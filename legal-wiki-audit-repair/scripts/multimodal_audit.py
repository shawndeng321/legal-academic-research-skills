#!/usr/bin/env python3
"""法学研究 Wiki 深检脚本（七项结构检查）。

用法：
    python3 -X utf8 multimodal_audit.py <WIKI_PATH> [--json] [--strict] [--privacy]

    WIKI_PATH 也可通过环境变量 WIKI_PATH 提供。`--json` 输出机器可读结果
    （字段名为英文，内容为中文）；`--strict` 下「提示」级发现也计入失败；
    `--privacy` 启用可选的个人信息格式检查（默认关闭，命中值打码显示）。

退出码：
    0 = 通过；1 = 存在阻断项（--strict 下提示项也计入）；
    2 = 执行失败或扫描不完整（参数、配置、依赖错误，或未扫描到任何对象）。

七项检查与规则编号：
    1 索引一致性  IDX-00 缺少 index.md（未检查）/IDX-01 计数不符/
                  IDX-02 缺索引条目/IDX-03 幽灵条目/IDX-04 游离文件
    2 未摄入原始材料 RAW-01 原件缺提取/RAW-02 提取命名不一致/
                  RAW-03 占位片段/RAW-04 未登记日志/
                  RAW-05 提取文件缺 frontmatter 或无法解析/RAW-06 占位 sha256
    3 frontmatter 质量 FM-01 解析失败/FM-02 缺必填字段或字段为空/
                  FM-03 类型非法/FM-04 标签问题/FM-05 重复键/FM-06 来源路径不存在
    4 链接完整性  LINK-01 死链/LINK-02 空目标（0 字节）/LINK-03 同名歧义/
                  LINK-04 畸形写法/LINK-05 路径前缀不符/LINK-06 锚点不存在/
                  LINK-07 孤立页/LINK-08 出站不足
    5 文件卫生    HYG-01 素材图未引用/HYG-02 提取正文过短或缺提取
    6 日志格式    LOG-01 日志超阈值
    7 法学专项    NORM-01 法规范页缺 效力状态/核验日期，NORM-02 核验日期超期限
                  （默认 365 天，可配置），NORM-03 失效规范被概念或比较页引用，
                  DUP-01 同一案号（全半角与空格规范化后）疑似重复页面，
                  PRIV-01 疑似个人信息格式（可选，`--privacy` 启用，打码报告），
                  NORM-9、PRIV-9 通过标记

约定配置：页面目录、原始目录、排除目录、必填字段默认见下方 DEFAULT_*；
vault 根目录存在 `wiki-audit.config.json` 时按键覆盖（page_dirs、raw_dir、
exclude_dirs、meta_files、required_fields、norm_verify_max_age_days、
privacy{enabled, extra_patterns}）。法规范时效：`核验日期` 超过
norm_verify_max_age_days 天提示复核；隐私检查的 extra_patterns 用于放入
设计书约定的脱敏模式（未配置时只做格式检查并说明）。

边界：本脚本只做**结构与来源一致性**检查，不构成学术内容审查；结构检查
通过不等于学术可用性通过。标题/块锚点按文本近似核对（块锚点与图谱细节
未在真实 Obsidian 全版本实测，标「待核」）。
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

# Emoji（🔴🟡✅）在部分 zh-CN 控制台会崩溃；强制 UTF-8 输出。
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover - 平台相关
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wiki_links  # noqa: E402   （共享解析模块，两个技能各持一份、字节相同）
from wiki_links import (  # noqa: E402
    DEFAULT_SKIP_DIR_NAMES,
    VaultIndex,
    as_posix,
    malformed_problems,
    parse_links_in_line,
)

try:
    import yaml
except ImportError:  # pragma: no cover - 依赖缺失路径
    yaml = None

# --- 约定配置（可用 vault 根目录的 wiki-audit.config.json 覆盖） ---
DEFAULT_PAGE_DIRS = (
    "entities", "concepts", "comparisons", "queries", "methodology", "research-design",
)
DEFAULT_RAW_DIR = "raw"
DEFAULT_EXCLUDE_DIRS = tuple(sorted(DEFAULT_SKIP_DIR_NAMES)) + (
    ".obsidian", ".git", ".maintenance", "drafts",
)
DEFAULT_META_FILES = ("SCHEMA.md", "index.md", "log.md")
DEFAULT_REQUIRED_FIELDS = ("title", "created", "updated", "type", "tags", "sources")
CONFIG_FILE_NAME = "wiki-audit.config.json"
# 与脚本同名的维护台账文件：不属于正式页面也不属于原始材料，不报游离。
ROOT_ALLOWED_FILES = ("知识库排查修复流程与整改台账.md",)
VALID_TYPES = {
    "case", "paper", "norm", "concept", "comparison", "query", "moc", "handoff",
    "research-design", "methodology", "draft", "model-article", "entity", "summary",
    "范文", "底稿", "法规范", "案例", "论文", "概念", "比较",
}
BINARY_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".wav", ".mp3", ".gif", ".webp", ".docx", ".doc"}
SIBLING_REQUIRED_RAW_DIRS = ("transcripts", "screenshots")
STUB_KEYWORDS = ("Content extracted", "full text available", "source URL")
PLACEHOLDER_HASHES = ("<placeholder>", "PLACEHOLDER")
LOG_WARN_THRESHOLD = 500


class Finding:
    __slots__ = ("rule", "severity", "scope", "path", "location", "message")

    def __init__(self, rule, severity, scope, path, location, message):
        self.rule = rule
        self.severity = severity      # broken / warning / pass
        self.scope = scope            # 结构 / 来源 / 内容 / 链接 / 卫生 / 日志
        self.path = path
        self.location = location
        self.message = message

    def to_dict(self):
        return {
            "rule": self.rule, "severity": self.severity, "scope": self.scope,
            "path": self.path, "location": self.location, "message": self.message,
        }


class Audit:
    def __init__(self, wiki, config):
        self.wiki = wiki
        self.page_dirs = list(config["page_dirs"])
        self.raw_dir = config["raw_dir"]
        self.exclude_dirs = set(config["exclude_dirs"])
        self.meta_files = list(config["meta_files"])
        self.required_fields = list(config["required_fields"])
        self.norm_verify_max_age_days = config["norm_verify_max_age_days"]
        self.privacy = dict(config["privacy"])
        self._extra_privacy_patterns = [
            ("自定义模式", re.compile(pattern))
            for pattern in self.privacy.get("extra_patterns", [])
        ]
        self.findings = []
        self.unreadable = []
        self.raw_unreadable = []
        self.duplicate_keys = []
        self.check_notes = {}
        self.check_stats = {}
        self.index = VaultIndex.build(wiki, exclude_dir_names=set(DEFAULT_SKIP_DIR_NAMES))
        self.pages = {}
        self.raw_files = {}

    # ---------- 基础 ----------
    def add(self, rule, severity, scope, path, location, message):
        self.findings.append(Finding(rule, severity, scope, path, location, message))

    def _skipped(self, rel_parts):
        return any(
            part.startswith(".") or part in self.exclude_dirs for part in rel_parts
        )

    def _walk(self, root_rel):
        root = self.wiki / root_rel
        if not root.is_dir():
            return
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = as_posix(str(path.relative_to(self.wiki)))
            parts = rel.split("/")
            if self._skipped(parts[:-1]):
                continue
            yield rel, path

    def _split_frontmatter(self, text):
        """返回 (fm_text 或 None, body)。"""
        if not text or not text.startswith("---"):
            return None, text or ""
        parts = text.split("---", 2)
        if len(parts) < 3:
            return None, text
        return parts[1], parts[2]

    def _parse_frontmatter(self, text, rel):
        """页面 frontmatter：YAML 错误与重复键在这里单列。返回 (fm, ok)。"""
        fm_text, _ = self._split_frontmatter(text)
        if fm_text is None:
            return {}, True
        try:
            data = yaml.load(fm_text, Loader=_strict_loader())
        except DuplicateKeyError as exc:
            self.duplicate_keys.append((rel, str(exc)))
            self.add("FM-05", "warning", "内容", rel, "frontmatter",
                     f"重复键：{exc}（后值会覆盖前值，请合并）")
            try:
                data = yaml.load(fm_text, Loader=yaml.SafeLoader)
            except yaml.YAMLError:
                data = {}
            return (data if isinstance(data, dict) else {}), True
        except yaml.YAMLError as exc:
            mark = getattr(exc, "problem_mark", None)
            where = f"第 {mark.line + 1} 行" if mark is not None else "frontmatter"
            self.add("FM-01", "broken", "内容", rel, where,
                     f"frontmatter 解析失败：{getattr(exc, 'problem', exc)}（该页其余检查未执行）")
            self.unreadable.append(rel)
            return None, False
        if data is None:
            return {}, True
        if not isinstance(data, dict):
            self.add("FM-01", "broken", "内容", rel, "frontmatter",
                     "frontmatter 不是键值映射（该页其余检查未执行）")
            self.unreadable.append(rel)
            return None, False
        return data, True

    # ---------- 采集 ----------
    def collect(self):
        for dir_name in self.page_dirs:
            for rel, path in self._walk(dir_name):
                if not rel.endswith(".md"):
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError) as exc:
                    self.add("FM-01", "broken", "内容", rel, "文件", f"无法读取：{exc}")
                    self.unreadable.append(rel)
                    continue
                fm, ok = self._parse_frontmatter(text, rel)
                self.pages[rel] = {
                    "path": path, "text": text, "fm": fm or {}, "ok": ok,
                }
        for rel, path in self._walk(self.raw_dir):
            ext = os.path.splitext(rel)[1].lower()
            self.raw_files[rel] = {"path": path, "ext": ext, "is_binary": ext in BINARY_EXTS}

    # ---------- 检查 1：索引一致性 ----------
    def check_index(self):
        stats = {"pages": len(self.pages), "declared": None, "entries": None}
        index_path = self.wiki / "index.md"
        if index_path.is_file():
            text = index_path.read_text(encoding="utf-8")
            declared = None
            entries = {}
            for line in text.splitlines():
                m = re.search(r"(?:总页数|页面总数|当前纳入导航的页面|Total pages)\**\s*[：:]\s*(\d+)", line)
                if m:
                    declared = int(m.group(1))
                for link in parse_links_in_line(line):
                    if not link.file_part or link.file_part.startswith(("http", "#")):
                        continue
                    resolution = self.index.resolve(link.file_part)
                    if resolution.resolvable and resolution.target:
                        entries[resolution.target] = link.raw
                    else:
                        entries.setdefault("__ghost__:" + link.file_part, link.raw)
            stats["declared"] = declared
            stats["entries"] = len(entries)
            page_set = set(self.pages)
            if declared is not None and declared != len(page_set):
                self.add("IDX-01", "broken", "结构", "index.md", "计数行",
                         f"索引声明 {declared} 页，磁盘实际 {len(page_set)} 页")
            resolved = {k for k in entries if not k.startswith("__ghost__")}
            missing = sorted(page_set - resolved)
            if missing:
                self.add("IDX-02", "broken", "结构", "index.md", "条目",
                         f"磁盘页面不在索引中（{len(missing)}）：{'、'.join(missing[:8])}"
                         + ("……" if len(missing) > 8 else ""))
            ghosts = []
            for k, v in entries.items():
                if k.startswith("__ghost__"):
                    ghosts.append(f"[[{v}]]（无法解析）")
            for k in sorted(resolved - page_set):
                ghosts.append(f"[[{entries[k]}]]（指向 {k}，非正式页面）")
            if ghosts:
                self.add("IDX-03", "broken", "结构", "index.md", "条目",
                         f"幽灵条目（{len(ghosts)}）：{'、'.join(ghosts[:8])}"
                         + ("……" if len(ghosts) > 8 else ""))
            if not missing and not ghosts and (declared is None or declared == len(page_set)):
                self.add("IDX-9", "pass", "结构", "index.md", "文件",
                         f"计数与条目一致（{len(page_set)} 页）")
        else:
            self.check_notes[1] = "未找到 index.md——索引一致性未检查（不视为通过）"
            self.add("IDX-00", "warning", "结构", "index.md", "文件",
                     "缺少 index.md，索引一致性未检查（不视为通过）")
        # 游离 .md：不在页面目录、不在 raw、不是元文件
        stray = []
        for rel, _path in self._walk("."):
            if not rel.endswith(".md"):
                continue
            first = rel.split("/", 1)[0]
            if first in self.page_dirs or first == self.raw_dir:
                continue
            if rel in self.meta_files or rel in ROOT_ALLOWED_FILES:
                continue
            stray.append(rel)
        if stray:
            self.add("IDX-04", "warning", "结构", "（库根）", "文件",
                     f"游离的 .md 文件（{len(stray)}）：{'、'.join(sorted(stray))}")
        broken = any(f.rule.startswith("IDX") and f.severity == "broken" for f in self.findings)
        warning = any(f.rule.startswith("IDX") and f.severity == "warning" for f in self.findings)
        if broken:
            stats["status"] = "fail"
        elif warning:
            stats["status"] = "warn"
        elif not self.pages:
            stats["status"] = "not_checked"
            self.check_notes[1] = "未发现正式页面——索引一致性未检查（不视为通过）"
        else:
            stats["status"] = "pass"
        self.check_stats[1] = stats

    # ---------- 检查 2：未摄入原始材料 ----------
    def check_raw(self):
        stats = {"raw_total": len(self.raw_files), "binaries": 0, "pair_checked": 0}
        if not self.raw_files:
            self.check_notes[2] = f"未发现 {self.raw_dir}/ 下的任何原始文件——该检查未执行（不视为通过）"
            stats["status"] = "not_checked"
            self.check_stats[2] = stats
            return
        raw_md = {r for r in self.raw_files if r.endswith(".md")}
        binaries = {
            r: v for r, v in self.raw_files.items()
            if v["is_binary"] and not r.startswith(self.raw_dir + "/assets/")
        }
        stats["binaries"] = len(binaries)
        missing_extract, renamed = [], []
        for rel in sorted(binaries):
            subdir = rel[len(self.raw_dir) + 1:].split("/", 1)[0] if "/" in rel[len(self.raw_dir) + 1:] else ""
            sibling = os.path.splitext(rel)[0] + ".md"
            if sibling in self.raw_files:
                continue
            same_dir = os.path.dirname(rel)
            stem = os.path.splitext(os.path.basename(rel))[0]
            alt = next(
                (r for r in sorted(raw_md)
                 if os.path.dirname(r) == same_dir and stem in os.path.basename(r)),
                None,
            )
            if alt:
                renamed.append((rel, alt))
            elif subdir in SIBLING_REQUIRED_RAW_DIRS:
                missing_extract.append(rel)
        stats["pair_checked"] = len(binaries) if binaries else 0
        for rel in missing_extract:
            self.add("RAW-01", "broken", "来源", rel, "文件", "原件缺少同名提取 .md")
        for rel, alt in renamed:
            self.add("RAW-02", "warning", "来源", rel, "文件", f"提取文件命名不一致：{alt}")
        if binaries and not missing_extract and not renamed:
            self.add("RAW-9", "pass", "来源", f"{self.raw_dir}/", "目录",
                     f"原件均有对应提取（transcripts/screenshots，共 {len(binaries)} 个）")
        # 占位片段
        stubs = []
        for rel in sorted(raw_md):
            text = self.index.read_text(rel)
            if text is None:
                continue
            _fm, body = self._split_frontmatter(text)
            body_lines = [l for l in body.split("\n") if l.strip() and not l.strip().startswith(">")]
            if len(body_lines) <= 5 and any(kw in body for kw in STUB_KEYWORDS):
                stubs.append(rel)
        for rel in stubs:
            self.add("RAW-03", "warning", "来源", rel, "文件",
                     "占位片段（仅有提取线索，未完成摄入）")
        if raw_md and not stubs:
            self.add("RAW-9", "pass", "来源", f"{self.raw_dir}/", "目录", "无占位片段")
        # 日志登记
        log_refs = self._log_raw_refs(self._read_log())
        missing_log = sorted(raw_md - log_refs)
        for rel in missing_log:
            self.add("RAW-04", "warning", "来源", rel, "文件", "raw 的 .md 未登记到 log.md")
        if raw_md and not missing_log:
            self.add("RAW-9", "pass", "来源", "log.md", "文件", "raw 的 .md 均已登记到 log.md")
        # 提取物 frontmatter 与占位哈希（原「检查 3」对 raw 的口径，保留）
        for rel in sorted(raw_md):
            text = self.index.read_text(rel)
            if text is None:
                self.add("RAW-05", "broken", "来源", rel, "文件", "无法读取")
                self.raw_unreadable.append(rel)
                continue
            fm_text, _body = self._split_frontmatter(text)
            if fm_text is None:
                self.add("RAW-05", "broken", "来源", rel, "文件", "缺 frontmatter")
                continue
            try:
                data = yaml.load(fm_text, Loader=_strict_loader())
            except DuplicateKeyError as exc:
                self.add("RAW-05", "warning", "来源", rel, "文件", f"frontmatter 重复键：{exc}")
                try:
                    data = yaml.load(fm_text, Loader=yaml.SafeLoader)
                except yaml.YAMLError:
                    data = None
            except yaml.YAMLError as exc:
                self.add("RAW-05", "broken", "来源", rel, "文件",
                         f"frontmatter 解析失败：{getattr(exc, 'problem', exc)}")
                continue
            if isinstance(data, dict) and data.get("sha256") in PLACEHOLDER_HASHES:
                self.add("RAW-06", "broken", "来源", rel, "frontmatter", "占位 sha256")
        broken = any(f.severity == "broken" for f in self.findings if f.scope == "来源")
        warning = any(f.severity == "warning" for f in self.findings if f.scope == "来源")
        if broken:
            stats["status"] = "fail"
        elif warning:
            stats["status"] = "warn"
        else:
            stats["status"] = "pass"
        self.check_stats[2] = stats

    def _read_log(self):
        log_path = self.wiki / "log.md"
        return log_path.read_text(encoding="utf-8") if log_path.is_file() else ""

    def _log_raw_refs(self, log_text):
        refs = set()
        pattern = re.compile(
            "(?:" + re.escape(self.raw_dir) + r"/[^\n]+?\.(?:md|pdf|png|jpg|jpeg|wav|mp3|txt|docx|doc))"
        )
        for m in pattern.finditer(log_text or ""):
            refs.add(as_posix(m.group(0).strip()))
        return refs

    # ---------- 检查 3：frontmatter ----------
    def check_frontmatter(self):
        stats = {"checked": len(self.pages)}
        taxonomy = self._load_taxonomy()
        tag_usage = Counter()
        for page in self.pages.values():
            for t in self._tag_list(page["fm"]):
                tag_usage[t] += 1
        for rel, page in sorted(self.pages.items()):
            if not page["ok"]:
                continue
            fm = page["fm"]
            missing = [f for f in self.required_fields if f not in fm]
            if missing:
                self.add("FM-02", "broken", "内容", rel, "frontmatter",
                         f"缺少必填字段：{'、'.join(missing)}")
                continue
            for key in ("title", "created", "updated", "type"):
                value = fm.get(key)
                if value is None or (isinstance(value, str) and not value.strip()):
                    self.add("FM-02", "broken", "内容", rel, "frontmatter", f"字段为空：{key}")
            page_type = fm.get("type")
            if page_type is not None and not isinstance(page_type, (list, dict)) \
                    and str(page_type).strip() and str(page_type) not in VALID_TYPES:
                self.add("FM-03", "warning", "内容", rel, "frontmatter",
                         f"type 不在约定清单：{page_type}")
            tags = self._tag_list(fm)
            if not tags:
                self.add("FM-04", "warning", "内容", rel, "frontmatter", "tags 为空")
            bad = [t for t in tags if t not in taxonomy and tag_usage.get(t, 0) == 1]
            if bad:
                self.add("FM-04", "warning", "内容", rel, "frontmatter",
                         f"非词表且仅用一次的标签：{'、'.join(bad)}")
            sources = fm.get("sources") or []
            if isinstance(sources, str):
                sources = [s.strip() for s in sources.split(",")]
            for src in sources:
                src = str(src).strip()
                if not src or src.startswith(("http", "《")):
                    continue
                if not re.search(r"/|\.(?:md|pdf|docx|doc|txt|png|jpg|jpeg|csv)$", src, re.I):
                    continue
                if not self.index.resolve(src).resolvable:
                    self.add("FM-06", "warning", "来源", rel, "frontmatter",
                             f"来源路径不存在：{src}")
        broken = any(f.severity == "broken" for f in self.findings if f.scope == "内容")
        warning = any(f.severity == "warning" for f in self.findings if f.scope == "内容")
        stats["status"] = "fail" if broken else ("warn" if warning else "pass")
        if not self.pages:
            stats["status"] = "not_checked"
        self.check_stats[3] = stats

    @staticmethod
    def _tag_list(fm):
        tags = fm.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in re.split(r"[,，]", tags)]
        if not isinstance(tags, list):
            return []
        return [str(t).strip() for t in tags if str(t).strip()]

    def _load_taxonomy(self):
        schema_path = self.wiki / "SCHEMA.md"
        taxonomy = set()
        if not schema_path.is_file():
            return taxonomy
        schema = schema_path.read_text(encoding="utf-8")
        m = re.search(r"^##\s*Tag Taxonomy\s*$(.*?)(?=^##\s|\Z)", schema, re.MULTILINE | re.DOTALL)
        if m:
            section = m.group(1)
        else:
            parts = re.findall(r"^###\s*[A-E]\.\s*[^\n]*\n([^\n#]+)", schema, re.MULTILINE)
            parts += re.findall(r"`([^`]+)`", schema)
            section = "\n".join(parts)
        for line in section.split("\n"):
            for t in re.split(r"[、，,]+", line):
                t = t.strip().lstrip("- ").strip()
                if t and ":" not in t:
                    taxonomy.add(t)
        return taxonomy

    # ---------- 检查 4：链接完整性 ----------
    def check_links(self):
        stats = {"pages_scanned": len(self.pages), "broken": 0, "attachment_missing": 0,
                 "empty_target": 0, "path_mismatch": 0, "anchor_missing": 0,
                 "ambiguous": 0, "malformed": 0}
        outbound = defaultdict(set)
        inbound = defaultdict(set)
        for rel, page in sorted(self.pages.items()):
            for number, line in enumerate((page["text"] or "").splitlines(), 1):
                for problem in malformed_problems(line):
                    stats["malformed"] += 1
                    self.add("LINK-04", "warning", "链接", rel, f"L{number}",
                             f"{problem}｜{line.strip()[:60]}")
                for link in parse_links_in_line(line):
                    if link.file_part.startswith("http"):
                        continue
                    if link.file_part == "":
                        if link.anchor and self.index.check_heading_anchor(rel, link.anchor) == "missing":
                            stats["anchor_missing"] += 1
                            self.add("LINK-06", "warning", "链接", rel, f"L{number}",
                                     f"本页锚点不存在：#{link.anchor}")
                        continue
                    resolution = self.index.resolve(link.file_part, link.anchor)
                    if resolution.status == "ok" and resolution.target:
                        outbound[rel].add(resolution.target)
                        inbound[resolution.target].add(rel)
                    elif resolution.status == "missing":
                        if link.embed:
                            stats["attachment_missing"] += 1
                        else:
                            stats["broken"] += 1
                        kind = "附件" if link.embed else "笔记"
                        self.add("LINK-01", "broken", "链接", rel, f"L{number}",
                                 f"死链（{kind}）：[[{link.raw}]]")
                    elif resolution.status == "empty_target":
                        stats["empty_target"] += 1
                        self.add("LINK-02", "broken", "链接", rel, f"L{number}",
                                 f"空目标（0 字节页面）：[[{link.raw}]] → {resolution.target}")
                    elif resolution.status == "path_mismatch":
                        stats["path_mismatch"] += 1
                        outbound[rel].add(resolution.target)
                        inbound[resolution.target].add(rel)
                        self.add("LINK-05", "warning", "链接", rel, f"L{number}",
                                 f"路径前缀不符：[[{link.raw}]] → 实际 {resolution.target}")
                    elif resolution.status == "ambiguous":
                        stats["ambiguous"] += 1
                        outbound[rel].add(resolution.target)
                        inbound[resolution.target].add(rel)
                        self.add("LINK-03", "warning", "链接", rel, f"L{number}",
                                 f"同名歧义：[[{link.raw}]] → {resolution.target}"
                                 f"（另有 {len(resolution.candidates) - 1} 个同名文件）")
                    elif resolution.status == "anchor_missing":
                        stats["anchor_missing"] += 1
                        outbound[rel].add(resolution.target)
                        inbound[resolution.target].add(rel)
                        self.add("LINK-06", "warning", "链接", rel, f"L{number}",
                                 f"锚点不存在：[[{link.raw}]] → {resolution.target}")
        for stem, paths in sorted(self.index.duplicate_stems().items()):
            self.add("LINK-03", "warning", "链接", "（全库）", "同名文件",
                     f"同名页面「{stem}」：{'、'.join(paths)}（链接将按最短路径解析，建议消歧）")
        if not stats["broken"] and not stats["attachment_missing"]:
            self.add("LINK-9", "pass", "链接", "（全库）", "全库", "未发现死链")
        orphans = sorted(rel for rel in self.pages if not inbound.get(rel))
        for rel in orphans:
            self.add("LINK-07", "warning", "链接", rel, "文件", "孤立页（0 入链）")
        if self.pages and not orphans:
            self.add("LINK-9", "pass", "链接", "（全库）", "全库", "无孤立页（0 入链）")
        under = [(rel, len(outbound.get(rel, ()))) for rel in sorted(self.pages)]
        under = [(rel, n) for rel, n in under if n < 2]
        for rel, n in under:
            self.add("LINK-08", "warning", "链接", rel, "文件", f"出站链接不足（{n} < 2）")
        if self.pages and not under:
            self.add("LINK-9", "pass", "链接", "（全库）", "全库", "所有页面出站链接均 ≥2")
        broken = any(f.severity == "broken" for f in self.findings if f.scope == "链接")
        warning = any(f.severity == "warning" for f in self.findings if f.scope == "链接")
        stats["status"] = "fail" if broken else ("warn" if warning else "pass")
        if not self.pages:
            stats["status"] = "not_checked"
        self.check_stats[4] = stats

    # ---------- 检查 5：文件卫生 ----------
    def check_hygiene(self):
        stats = {"checked": 0}
        assets = [r for r, info in self.raw_files.items()
                  if info["ext"] in {".png", ".jpg", ".jpeg"}
                  and r.startswith(self.raw_dir + "/assets/")]
        screenshots = [r for r, info in self.raw_files.items()
                       if info["ext"] in {".png", ".jpg", ".jpeg"}
                       and r.startswith(self.raw_dir + "/screenshots/")]
        stats["checked"] = len(assets) + len(screenshots)
        for rel in sorted(assets):
            basename = os.path.basename(rel)
            refs = sum(1 for page in self.pages.values() if basename in (page["text"] or ""))
            if refs == 0:
                self.add("HYG-01", "warning", "卫生", rel, "文件", "素材图未被任何页面引用")
            else:
                self.add("HYG-9", "pass", "卫生", rel, "文件", f"已被 {refs} 个页面引用")
        for rel in sorted(screenshots):
            sibling = os.path.splitext(rel)[0] + ".md"
            if sibling not in self.raw_files:
                self.add("HYG-02", "broken", "卫生", rel, "文件", "缺少同名提取 .md")
                continue
            text = self.index.read_text(sibling) or ""
            _fm, body = self._split_frontmatter(text)
            lines = [l for l in body.strip().split("\n") if l.strip()]
            if len(lines) <= 2:
                self.add("HYG-02", "warning", "卫生", sibling, "文件",
                         f"提取正文过短（{len(lines)} 行）")
            else:
                self.add("HYG-9", "pass", "卫生", sibling, "文件",
                         f"提取正文 {len(lines)} 行")
        broken = any(f.severity == "broken" for f in self.findings if f.scope == "卫生")
        warning = any(f.severity == "warning" for f in self.findings if f.scope == "卫生")
        if broken:
            stats["status"] = "fail"
        elif warning:
            stats["status"] = "warn"
        elif not stats["checked"]:
            stats["status"] = "not_checked"
            self.check_notes[5] = (f"未发现 {self.raw_dir}/assets 与 {self.raw_dir}/screenshots 素材"
                                   "——该检查未执行（不视为通过）")
        else:
            stats["status"] = "pass"
        self.check_stats[5] = stats

    # ---------- 检查 6：日志格式 ----------
    def check_log(self):
        stats = {"entries": 0}
        log_text = self._read_log()
        if not log_text:
            self.check_notes[6] = "未找到 log.md——日志检查未执行（不视为通过）"
            stats["status"] = "not_checked"
            self.check_stats[6] = stats
            return
        entries = re.findall(r"^## \[(\d{4}-\d{2}-\d{2})\]", log_text, re.MULTILINE)
        stats["entries"] = len(entries)
        if len(entries) > LOG_WARN_THRESHOLD:
            self.add("LOG-01", "warning", "日志", "log.md", "文件",
                     f"日志条目 {len(entries)} 条，超过 {LOG_WARN_THRESHOLD}，建议轮转")
            stats["status"] = "warn"
        else:
            self.add("LOG-9", "pass", "日志", "log.md", "文件",
                     f"日志条目 {len(entries)} 条（阈值 {LOG_WARN_THRESHOLD}）")
            stats["status"] = "pass"
        self.check_stats[6] = stats

    # ---------- 检查 7：法学专项（法规范时效、案件去重、隐私格式） ----------
    PRIVACY_PATTERNS = (
        ("身份证号", re.compile(
            r"(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)")),
        ("身份证号", re.compile(
            r"(?<!\d)[1-9]\d{5}\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}(?!\d)")),
        ("银行卡号", re.compile(r"(?<!\d)[1-9]\d{15,18}(?!\d)")),
        ("手机号", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    )
    STALE_NORM_STATUSES = ("已废止", "已修订")

    @staticmethod
    def _mask(value):
        if len(value) <= 5:
            return "*" * len(value)
        return value[:3] + "*" * (len(value) - 5) + value[-2:]

    @staticmethod
    def _as_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            match = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", value.strip())
            if match:
                try:
                    return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                except ValueError:
                    return None
        return None

    @staticmethod
    def _normalize_docket(value):
        if value is None:
            return None
        text = str(value).strip()
        if not text or text in ("原文未载明", "未载明", "无", "不详", "年份不详"):
            return None
        text = text.translate(str.maketrans({
            "（": "(", "）": ")", "〔": "(", "〕": ")", "【": "(", "】": ")",
            "［": "(", "］": ")", "\u3000": " ",
        }))
        text = re.sub(r"\s+", "", text)
        return text or None

    def _privacy_hits(self, text):
        """返回 [(行号, 类别, 打码值)]；重叠命中只取其一（身份证 > 银行卡 > 手机）。"""
        matches = []
        for line_no, line in enumerate(text.split("\n"), 1):
            found = []
            for index, (category, pattern) in enumerate(self.PRIVACY_PATTERNS):
                for match in pattern.finditer(line):
                    found.append((match.start(), match.end(), index, category, match.group(0)))
            for index, (category, pattern) in enumerate(self._extra_privacy_patterns):
                for match in pattern.finditer(line):
                    found.append((match.start(), match.end(),
                                  len(self.PRIVACY_PATTERNS) + index, category, match.group(0)))
            found.sort(key=lambda item: (item[0], -(item[1] - item[0]), item[2]))
            accepted_end = -1
            for start, end, _priority, category, value in found:
                if start >= accepted_end:
                    accepted_end = end
                    matches.append((line_no, category, self._mask(value)))
        return matches

    def check_special(self):
        stats = {"norms": 0, "cases": 0, "privacy_scanned": 0, "privacy_hits": 0}
        notes = []

        # --- 法规范时效 ---
        norms = {rel: page for rel, page in self.pages.items()
                 if isinstance(page["fm"], dict) and page["fm"].get("type") == "norm"}
        stats["norms"] = len(norms)
        if not norms:
            notes.append("未发现 type: norm 页面——法规范时效检查未执行（不视为通过）")
        stale_status = {}
        for rel in sorted(norms):
            fm_data = norms[rel]["fm"]
            status = fm_data.get("效力状态")
            verified = fm_data.get("核验日期")
            missing = [name for name, value in (("效力状态", status), ("核验日期", verified))
                       if value is None or (isinstance(value, str) and not value.strip())]
            if missing:
                self.add("NORM-01", "warning", "专项", rel, "frontmatter",
                         "法规范页缺少字段：" + "、".join(missing)
                         + "（建库要求填写 效力状态 与 核验日期）")
            verified_date = self._as_date(verified)
            if verified_date is not None:
                age = (date.today() - verified_date).days
                if age > self.norm_verify_max_age_days:
                    self.add("NORM-02", "warning", "专项", rel, "frontmatter",
                             "核验日期 {} 距今 {} 天（上限 {} 天），请复核效力状态".format(
                                 verified_date.isoformat(), age, self.norm_verify_max_age_days))
            if isinstance(status, str) and status.strip() in self.STALE_NORM_STATUSES:
                stale_status[rel] = status.strip()
        if stale_status:
            referenced = {rel: [] for rel in stale_status}
            for rel in sorted(self.pages):
                page = self.pages[rel]
                fm_data = page["fm"] if isinstance(page["fm"], dict) else {}
                if fm_data.get("type") not in ("concept", "comparison"):
                    continue
                for line in page["text"].split("\n"):
                    for link in parse_links_in_line(line):
                        if not link.file_part or link.file_part.startswith(("http", "#")):
                            continue
                        resolution = self.index.resolve(link.file_part)
                        if resolution.resolvable and resolution.target in referenced:
                            if rel not in referenced[resolution.target]:
                                referenced[resolution.target].append(rel)
            for rel in sorted(referenced):
                sources = referenced[rel]
                if not sources:
                    continue
                shown = "、".join(sources[:6]) + ("……" if len(sources) > 6 else "")
                self.add("NORM-03", "warning", "专项", rel, "frontmatter",
                         "效力状态为「{}」，但被概念/比较页作为现行依据引用（{} 处）：{}"
                         "——核对是历史适用，还是误引失效规范".format(
                             stale_status[rel], len(sources), shown))

        # --- 案件去重 ---
        cases = {rel: page for rel, page in self.pages.items()
                 if isinstance(page["fm"], dict) and page["fm"].get("type") == "case"}
        stats["cases"] = len(cases)
        if not cases:
            notes.append("未发现 type: case 页面——案件去重检查未执行（不视为通过）")
        groups = defaultdict(list)
        for rel in sorted(cases):
            docket = self._normalize_docket(cases[rel]["fm"].get("docket"))
            if docket:
                groups[docket].append(rel)
        for docket in sorted(groups):
            group = groups[docket]
            if len(group) < 2:
                continue
            details = []
            for rel in group:
                fm_data = cases[rel]["fm"]
                court = fm_data.get("court") or "法院未载"
                decided = self._as_date(fm_data.get("decision_date"))
                decided_text = decided.isoformat() if decided else (
                    str(fm_data.get("decision_date")) if fm_data.get("decision_date") else "日期未载")
                details.append("{}（{}；{}）".format(rel, court, decided_text))
            common = os.path.commonpath(group)
            self.add("DUP-01", "warning", "专项", common or "（库根）", "案号",
                     "疑似同一案件（案号规范化后相同）：「{}」——{}；只报告，不自动合并".format(
                         docket, "；".join(details)))

        # --- 隐私格式（可选） ---
        if self.privacy.get("enabled"):
            scanned = [(rel, self.pages[rel]["text"]) for rel in sorted(self.pages)]
            for rel in sorted(self.raw_files):
                if rel.endswith(".md"):
                    text = self.index.read_text(rel)
                    if text is not None:
                        scanned.append((rel, text))
            stats["privacy_scanned"] = len(scanned)
            hit_total = 0
            for rel, text in scanned:
                in_raw = rel.startswith(self.raw_dir + "/")
                for line_no, category, masked in self._privacy_hits(text):
                    hit_total += 1
                    suffix = "（原始材料只读：只报告，不修改）" if in_raw else "——核对是否应脱敏为「某某」写法"
                    self.add("PRIV-01", "warning", "专项", rel, "L{}".format(line_no),
                             "疑似{}（已打码：{}）{}".format(category, masked, suffix))
            stats["privacy_hits"] = hit_total
            if not hit_total:
                self.add("PRIV-9", "pass", "专项", "（全库）", "扫描", "未发现疑似个人信息格式")
            if not self.privacy.get("extra_patterns"):
                notes.append("未配置设计书脱敏规则（privacy.extra_patterns）——当前仅做格式检查")
        else:
            notes.append("隐私格式检查未启用（可选）——加 --privacy 或在 wiki-audit.config.json 中设 privacy.enabled=true")

        check7_rules = ("NORM-01", "NORM-02", "NORM-03", "DUP-01")
        has_warning = any(f.rule in check7_rules and f.severity == "warning" for f in self.findings)
        if (norms or cases) and not has_warning:
            self.add("NORM-9", "pass", "专项", "（全库）", "扫描",
                     "法规范 {} 页、案例 {} 页：时效与案号去重检查通过".format(len(norms), len(cases)))
        if has_warning:
            stats["status"] = "warn"
        elif not norms and not cases and not self.privacy.get("enabled"):
            stats["status"] = "not_checked"
        else:
            stats["status"] = "pass"
        self.check_stats[7] = stats
        if notes:
            self.check_notes[7] = "；".join(notes)

    # ---------- 汇总 ----------
    def run(self):
        self.collect()
        self.check_index()
        self.check_raw()
        self.check_frontmatter()
        self.check_links()
        self.check_hygiene()
        self.check_log()
        self.check_special()


# --- YAML 严格加载（重复键单列） ---
class DuplicateKeyError(Exception):
    pass


def _strict_loader():
    class _Loader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        mapping = {}
        seen = set()
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if isinstance(key, (dict, list)):
                key = str(key)
            if key in seen:
                raise DuplicateKeyError("「{}」出现两次".format(key))
            seen.add(key)
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    _Loader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
    )
    return _Loader


def load_config(wiki):
    config = {
        "page_dirs": list(DEFAULT_PAGE_DIRS),
        "raw_dir": DEFAULT_RAW_DIR,
        "exclude_dirs": list(DEFAULT_EXCLUDE_DIRS),
        "meta_files": list(DEFAULT_META_FILES),
        "required_fields": list(DEFAULT_REQUIRED_FIELDS),
        "norm_verify_max_age_days": 365,
        "privacy": {"enabled": False, "extra_patterns": []},
    }
    config_path = wiki / CONFIG_FILE_NAME
    if not config_path.is_file():
        return config
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{CONFIG_FILE_NAME} 读取失败：{exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{CONFIG_FILE_NAME} 必须是 JSON 对象")
    for key in ("page_dirs", "exclude_dirs", "meta_files", "required_fields"):
        if key in data:
            if not isinstance(data[key], list) or not all(isinstance(v, str) for v in data[key]):
                raise RuntimeError(f"{CONFIG_FILE_NAME} 的 {key} 必须是字符串数组")
            config[key] = data[key]
    if "raw_dir" in data:
        if not isinstance(data["raw_dir"], str):
            raise RuntimeError(f"{CONFIG_FILE_NAME} 的 raw_dir 必须是字符串")
        config["raw_dir"] = data["raw_dir"]
    if "norm_verify_max_age_days" in data:
        value = data["norm_verify_max_age_days"]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise RuntimeError(f"{CONFIG_FILE_NAME} 的 norm_verify_max_age_days 必须是非负整数")
        config["norm_verify_max_age_days"] = value
    if "privacy" in data:
        value = data["privacy"]
        if not isinstance(value, dict):
            raise RuntimeError(f"{CONFIG_FILE_NAME} 的 privacy 必须是对象")
        enabled = value.get("enabled", False)
        patterns = value.get("extra_patterns", [])
        if not isinstance(enabled, bool):
            raise RuntimeError(f"{CONFIG_FILE_NAME} 的 privacy.enabled 必须是布尔值")
        if not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
            raise RuntimeError(f"{CONFIG_FILE_NAME} 的 privacy.extra_patterns 必须是字符串数组")
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise RuntimeError(
                    f"{CONFIG_FILE_NAME} 的 privacy.extra_patterns 含非法正则：{pattern}（{exc}）") from exc
        config["privacy"] = {"enabled": enabled, "extra_patterns": patterns}
    return config


CHECK_TITLES = {
    1: "索引一致性", 2: "未摄入原始材料", 3: "frontmatter 质量",
    4: "链接完整性", 5: "文件卫生与惯例", 6: "日志格式",
    7: "法学专项（法规范时效、案件去重、隐私格式）",
}
SEVERITY_LABEL = {"broken": "🔴 阻断", "warning": "🟡 提示"}
STATUS_LABEL = {"pass": "✅ 通过", "warn": "🟡 有提示", "fail": "🔴 有阻断", "not_checked": "⚪ 未检查"}


def _rule_check(rule):
    prefix = rule.split("-", 1)[0]
    return {"IDX": 1, "RAW": 2, "FM": 3, "LINK": 4, "HYG": 5, "LOG": 6,
            "NORM": 7, "DUP": 7, "PRIV": 7}.get(prefix, 0)


def print_report(audit):
    print("=" * 72)
    print("法学研究 Wiki 深检报告（结构与来源一致性）")
    print("Wiki：{}".format(audit.wiki))
    print("页面 {} 个｜原始文件 {} 个".format(len(audit.pages), len(audit.raw_files)))
    print("=" * 72)
    for check_no in range(1, 8):
        stats = audit.check_stats.get(check_no, {})
        label = STATUS_LABEL.get(stats.get("status"), "⚪ 未检查")
        print("\n【检查 {}｜{}】{}".format(check_no, CHECK_TITLES[check_no], label))
        note = audit.check_notes.get(check_no)
        if note:
            print("  ⚪ " + note)
        for finding in audit.findings:
            if _rule_check(finding.rule) != check_no:
                continue
            if finding.severity == "pass":
                print("  ✅ " + finding.message)
            else:
                print("  {} [{}] {}｜{} — {}".format(
                    SEVERITY_LABEL[finding.severity], finding.rule,
                    finding.path, finding.location, finding.message))
    broken = [f for f in audit.findings if f.severity == "broken"]
    warnings = [f for f in audit.findings if f.severity == "warning"]
    print("\n" + "=" * 72)
    print("汇总")
    print("=" * 72)
    print("  🔴 阻断项：{}｜🟡 提示项：{}".format(len(broken), len(warnings)))
    if audit.unreadable:
        print("  ⚪ 解析失败、其余检查未执行的页面（{}）：{}".format(
            len(audit.unreadable), "、".join(audit.unreadable[:8])))
    if audit.raw_unreadable:
        print("  ⚪ 无法读取的提取文件（{}）：{}".format(
            len(audit.raw_unreadable), "、".join(audit.raw_unreadable[:8])))
    print("  说明：本报告仅覆盖结构与来源一致性；不构成学术内容审查，")
    print("        学术可用性（要旨、论证、统计口径等）需另行人工抽查。")
    print("        标题/块锚点按文本近似核对（块锚点待核）。")


def build_result(audit, strict, exit_code):
    broken = [f for f in audit.findings if f.severity == "broken"]
    warnings = [f for f in audit.findings if f.severity == "warning"]
    return {
        "schema_version": 1,
        "tool": "multimodal_audit",
        "wiki": str(audit.wiki),
        "strict": strict,
        "counts": {"pages": len(audit.pages), "raw_files": len(audit.raw_files)},
        "unreadable_pages": list(audit.unreadable),
        "unreadable_raw": list(audit.raw_unreadable),
        "duplicate_keys": [{"path": p, "detail": d} for p, d in audit.duplicate_keys],
        "notes": {str(k): v for k, v in sorted(audit.check_notes.items())},
        "checks": [
            {"check": n, "title": CHECK_TITLES[n], "note": audit.check_notes.get(n),
             **audit.check_stats.get(n, {"status": "not_checked"})}
            for n in range(1, 8)
        ],
        "findings": [f.to_dict() for f in audit.findings if f.severity != "pass"],
        "summary": {"broken": len(broken), "warning": len(warnings), "exit_code": exit_code},
    }


def main(argv):
    json_mode = "--json" in argv
    strict = "--strict" in argv
    privacy = "--privacy" in argv
    rest = [a for a in argv if a not in ("--json", "--strict", "--privacy")]
    if "--help" in rest or "-h" in rest:
        print(__doc__)
        return 0
    unknown = [a for a in rest if a.startswith("-")]
    if unknown:
        print("错误：未知参数 {}。用法：python3 multimodal_audit.py <WIKI_PATH> [--json] [--strict] [--privacy]".format(unknown),
              file=sys.stderr)
        return 2
    wiki_input = rest[0] if rest else os.environ.get("WIKI_PATH")
    if not wiki_input:
        print(
            "错误：未提供 Wiki 根目录。用法：python3 multimodal_audit.py <WIKI_PATH> [--json] [--strict] [--privacy]；"
            "也可设置环境变量 WIKI_PATH。(error: pass the Wiki root as an argument or set WIKI_PATH)",
            file=sys.stderr,
        )
        return 2
    wiki = Path(os.path.abspath(os.path.expanduser(wiki_input)))
    if not wiki.is_dir():
        print("错误：Wiki 根目录不存在或不是目录：{}".format(wiki), file=sys.stderr)
        return 2
    if yaml is None:
        print("错误：深检需要 PyYAML。请先安装：python3 -m pip install PyYAML"
              "（或 python3 -m pip install -r requirements-dev.txt）", file=sys.stderr)
        return 2
    try:
        config = load_config(wiki)
    except RuntimeError as exc:
        print("错误：{}".format(exc), file=sys.stderr)
        return 2
    if privacy:
        config["privacy"]["enabled"] = True
    audit = Audit(wiki, config)
    audit.run()
    empty_scan = not audit.pages and not audit.raw_files
    if empty_scan:
        exit_code = 2
        audit.check_notes[0] = "未扫描到任何页面或原始文件——请确认路径；不视为通过"
    else:
        broken = any(f.severity == "broken" for f in audit.findings)
        warning = any(f.severity == "warning" for f in audit.findings)
        exit_code = 1 if (broken or (strict and warning)) else 0
    if json_mode:
        print(json.dumps(build_result(audit, strict, exit_code), ensure_ascii=False, indent=2))
    else:
        print_report(audit)
        if empty_scan:
            print("  ⚪ 未扫描到任何页面或原始文件——请确认路径；不视为通过")
        if exit_code == 1:
            reason = "存在阻断项" + ("；--strict 下提示项也计入" if strict else "")
        elif exit_code == 0:
            reason = "通过"
        else:
            reason = "执行失败或扫描不完整"
        print("\n退出码：{}（{}）".format(exit_code, reason))
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
