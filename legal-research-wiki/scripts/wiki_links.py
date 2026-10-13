#!/usr/bin/env python3
"""共享的 Obsidian 链接解析与解析规则（法学研究 Wiki 技能包）。

本模块由 `legal-research-wiki` 与 `legal-wiki-audit-repair` 各持一份
（两份文件必须字节相同）；两个技能的检查脚本共用同一套解析规则，
保证对同一范围给出相同的结论。修改时必须同步两份副本。

解析规则（按 Obsidian 的常见行为实现；块锚点与图谱细节未在真实
Obsidian 全版本实测的条目按“待核”处理）：

- 链接：``[[目标]]``、``[[目标|别名]]``、``[[目标\\|别名]]``（表格转义）、
  ``[[目标#锚点]]``、``[[目标#^块标识]]``、``[[目标.md]]``、``[[子目录/目标]]``、
  附件嵌入 ``![[图片.png]]``；
- 别名分隔符：``|`` 与 ``\\|``；``&#124;`` 不是分隔符（属畸形写法）；
- 解析顺序：显式路径（相对 vault 根）→ 按文件名（笔记按 stem、附件按全名）；
- 同名文件不静默合并：由调用方通过同名索引报告“同名歧义”；
- 标题锚点按目标页标题文本近似核对；块锚点（``#^id``）按行尾 ``^id``
  近似核对（待核）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "WIKILINK_RE",
    "ATTACHMENT_EXTS",
    "ParsedLink",
    "Resolution",
    "VaultIndex",
    "malformed_problems",
    "normalize_heading",
    "split_alias",
    "strip_md_suffix",
]

# `[^\[\]\n]+?` 保证不吞掉嵌套的方括号；嵌套写法由 malformed_problems 单列。
WIKILINK_RE = re.compile(r"(!?)\[\[([^\[\]\n]+?)\]\]")
ALIAS_SPLIT_RE = re.compile(r"\\\||(?<!\\)\|")
SWALLOWED_HEADING_RE = re.compile(r"\[\[[^\]\n]*##")
NESTED_BRACKETS_RE = re.compile(r"\[\[[^\]\n]*\[\[")
EMPTY_TARGET_RE = re.compile(r"\[\[\s*(?:\|[^\]]*)?\]\]")
BLOCK_ID_RE_TEMPLATE = r"(?:^|\s)\^{}\s*$"

ATTACHMENT_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp",
    ".pdf", ".docx", ".doc", ".pptx", ".xlsx",
    ".wav", ".mp3", ".m4a", ".mp4", ".mov",
    ".txt", ".md",
}

# 两个检查器共用的“跳过目录”约定：隐藏目录（. 开头）另按前缀忽略；
# 备份/存档目录不得让已删除的页面看起来仍然存在（死链掩盖问题）。
DEFAULT_SKIP_DIR_NAMES = {
    "ghosts", "backup", "backups", "_scripts", "node_modules", "_archive",
}


def split_alias(raw: str) -> tuple[str, bool]:
    """按 Obsidian 规则剥离别名，返回（文件部分, 是否有别名）。"""
    parts = ALIAS_SPLIT_RE.split(raw, maxsplit=1)
    return parts[0].strip(), len(parts) > 1


def strip_md_suffix(target: str) -> str:
    return target[:-3] if target.lower().endswith(".md") else target


def as_posix(value: str) -> str:
    return value.replace("\\", "/")


def normalize_heading(text: str) -> str:
    """标题锚点比较用的规范化：去首尾空白、压缩内部空白、小写。"""
    return re.sub(r"\s+", " ", text.strip()).lower()


@dataclass(frozen=True)
class ParsedLink:
    """行内解析出的一个 wikilink。"""

    raw: str                 # 链接内文原文（未剥别名/锚点）
    embed: bool              # 是否为 ![[...]] 嵌入
    file_part: str           # 剥别名后的文件部分（保留路径与 .md 后缀）
    anchor: str | None       # 第一个 # 之后的内容；None 表示无锚点
    has_alias: bool


def parse_links_in_line(line: str) -> list[ParsedLink]:
    """解析一行中的全部 wikilink（``&#124;`` 写法由畸形检查单列，这里跳过）。"""
    links = []
    for bang, raw in WIKILINK_RE.findall(line):
        if "&#124;" in raw:
            continue
        file_part, has_alias = split_alias(raw)
        if "#" in file_part:
            file_part, _, anchor = file_part.partition("#")
            anchor = anchor.strip() or None
        else:
            anchor = None
        links.append(
            ParsedLink(
                raw=raw,
                embed=bang == "!",
                file_part=file_part.strip(),
                anchor=anchor,
                has_alias=has_alias,
            )
        )
    return links


def malformed_problems(line: str) -> list[str]:
    """行级畸形写法检查（两个检查器共用）。"""
    problems = []
    if "&#124;" in line and "[[" in line:
        problems.append("`&#124;` 不是别名分隔符（表格中请用 `\\|`）")
    if SWALLOWED_HEADING_RE.search(line):
        problems.append("链接吞掉了后面的标题（缺少 `]]`）")
    if NESTED_BRACKETS_RE.search(line):
        problems.append("嵌套方括号（链接中还有 `[[`）")
    if EMPTY_TARGET_RE.search(line):
        problems.append("空链接目标（`[[]]` 或 `[[|别名]]`）")
    if line.count("[[") > line.count("]]"):
        problems.append("`[[` 与 `]]` 数量不匹配（截断或缺右括号）")
    return problems


@dataclass
class Resolution:
    """对一条链接的解析结论。两个检查器必须据此分类，不得各自重写。"""

    status: str                # ok/missing/empty_target/path_mismatch/ambiguous/anchor_missing
    target: str | None = None  # 命中的 vault 相对路径（missing 时为 None）
    candidates: tuple[str, ...] = ()   # 同名歧义时的全部候选
    detail: str = ""

    @property
    def resolvable(self) -> bool:
        return self.status != "missing"


@dataclass
class VaultIndex:
    """vault 文件索引：按 vault 相对路径为身份，附 stem / 文件名多值索引。"""

    wiki: Path
    files: dict[str, Path] = field(default_factory=dict)          # relpath -> 绝对路径
    notes_by_stem: dict[str, list[str]] = field(default_factory=dict)
    files_by_name: dict[str, list[str]] = field(default_factory=dict)
    empty_notes: set[str] = field(default_factory=set)
    _text_cache: dict[str, str | None] = field(default_factory=dict)

    @classmethod
    def build(cls, wiki: Path, exclude_dir_names: set[str] | None = None) -> "VaultIndex":
        index = cls(wiki=Path(wiki))
        excluded = exclude_dir_names or set()
        for path in sorted(index.wiki.rglob("*")):
            rel_parts = path.relative_to(index.wiki).parts
            if any(part.startswith(".") or part in excluded for part in rel_parts[:-1]):
                continue
            if not path.is_file():
                continue
            rel = as_posix(str(path.relative_to(index.wiki)))
            index.files[rel] = path
            name = path.name
            index.files_by_name.setdefault(name, []).append(rel)
            if path.suffix.lower() == ".md":
                index.notes_by_stem.setdefault(path.stem, []).append(rel)
                try:
                    if path.stat().st_size == 0:
                        index.empty_notes.add(rel)
                except OSError:
                    pass
        return index

    def read_text(self, rel: str) -> str | None:
        if rel not in self._text_cache:
            try:
                self._text_cache[rel] = self.files[rel].read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                self._text_cache[rel] = None
        return self._text_cache[rel]

    def duplicate_stems(self) -> dict[str, list[str]]:
        return {stem: sorted(paths) for stem, paths in self.notes_by_stem.items() if len(paths) > 1}

    def check_heading_anchor(self, rel: str, anchor: str) -> str:
        """返回 ok / missing。块锚点（^id）为文本近似核对（待核）。"""
        text = self.read_text(rel)
        if text is None:
            return "missing"
        if anchor.startswith("^"):
            pattern = re.compile(
                BLOCK_ID_RE_TEMPLATE.format(re.escape(anchor[1:])), re.MULTILINE
            )
            return "ok" if pattern.search(text) else "missing"
        wanted = normalize_heading(anchor)
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                if normalize_heading(stripped.lstrip("#").strip()) == wanted:
                    return "ok"
        return "missing"

    def resolve(self, file_part: str, anchor: str | None = None) -> Resolution:
        """解析链接的文件部分；anchor 提供时同时核对其存在性。

        显式路径（含 `/`）保留路径语义：路径不存在时若按文件名可命中，
        记为 path_mismatch（提示改正前缀）；完全找不到为 missing。
        """
        target = as_posix(file_part).strip()
        if "#" in target:
            target, _, inline_anchor = target.partition("#")
            anchor = anchor or (inline_anchor.strip() or None)
            target = target.strip()
        if not target:
            return Resolution(status="ok", detail="同页锚点（[#标题]），不跨页")

        candidates: tuple[str, ...] = ()
        if "/" in target:
            path_variants = [target]
            if not target.lower().endswith(".md"):
                path_variants.append(target + ".md")
            hit = next((v for v in path_variants if v in self.files), None)
            if hit:
                rel = hit
                status = "ok"
            else:
                name = target.rsplit("/", 1)[-1]
                fallback = self._by_name(name)
                if not fallback:
                    return Resolution(status="missing", detail="路径与文件名均不存在")
                rel = fallback[0]
                candidates = tuple(fallback)
                status = "path_mismatch"
                if len(fallback) > 1:
                    status = "ambiguous"
        else:
            # 裸名解析：同时查“文件名精确匹配”（附件如 图.png、目标.md）与
            # “stem 匹配”（笔记如 论文v2.0 这类含点但非扩展名的名字）。
            matches = set(self.files_by_name.get(target, []))
            matches.update(self.notes_by_stem.get(strip_md_suffix(target), []))
            matches = sorted(matches)
            if not matches:
                return Resolution(status="missing", detail="库内不存在同名文件")
            rel = matches[0]
            candidates = tuple(matches)
            if len(matches) > 1:
                status = "ambiguous"
            else:
                status = "ok"

        if rel in self.empty_notes:
            return Resolution(status="empty_target", target=rel, candidates=candidates, detail="目标是 0 字节页面")
        if anchor:
            verdict = self.check_heading_anchor(rel, anchor)
            if verdict == "missing":
                return Resolution(status="anchor_missing", target=rel, candidates=candidates, detail=f"锚点不存在：# {anchor}")
        if status == "ambiguous":
            return Resolution(status="ambiguous", target=rel, candidates=candidates, detail="同名多文件，已按最短路径解析")
        return Resolution(status=status, target=rel, candidates=candidates)

    def _by_name(self, name: str) -> list[str]:
        if name in self.files_by_name:
            return sorted(self.files_by_name[name])
        if not name.lower().endswith(".md"):
            return sorted(self.notes_by_stem.get(name, []))
        return []
