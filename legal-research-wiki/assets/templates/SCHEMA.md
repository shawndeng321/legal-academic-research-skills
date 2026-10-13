# Wiki Schema v1.0

> 本文件规定本研究库的页面类型、字段、标签与链接约定。修改规范时升版本号，并在此处写一行变更说明（日期、改了什么、是否经用户确认）。
> 模板说明：`〈…〉` 为待填内容；不适用的类型或字段可以删除，但删除前确认没有页面在用。

## Domain

〈一句话说明研究领域与目标，例如：通过对某类行政案件裁判文书的系统分析，发现裁判规律、分歧点与演变，形成期刊论文。〉

## Conventions

- 文件名：中文，不含 `\ / : * ? " < > |`、`#`、`^`、`[`、`]` 等特殊字符。
- 每个正式知识页和工作导航页以 YAML frontmatter 开头；SCHEMA、index、log、整改台账等根目录元文件例外。
- 正式实体页之间用 wikilink 互相链接（每页至少 2 个出站链接，且每条关系说得出理由）；导航、查询、交接页按用途验收，不机械套用链接数量。
- 表格内的别名链接写作 `[[目标\|别名]]`；不要用 `&#124;`。
- 更新页面时更新 `updated`；新页面加入 `index.md` 对应分类；每次操作追加到 `log.md`。
- 维护文档（本文件、log、台账）中的示例链接写成纯文本，不写双方括号。
- 出处标记：综合 3 个以上来源的页面，在段落末尾加 `^[raw/...]`。

## Frontmatter

```yaml
---
title: 页面标题
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: case | paper | draft | model-article | concept | comparison | norm | research-design | methodology | query | moc | handoff
tags: [标签]                    # 每页 3—5 个，见 Tag Taxonomy
sources: [raw/...]              # 只写原始材料文件路径
source_note: 说明文字            # 可选：非路径来源（口述、目录说明、库内导航等）
source_confidence: high | medium | low          # 原始材料提取与核验的置信度
analysis_status: verified | preliminary | hypothesis | in_progress  # 研究分析层的核验状态
contested: true                 # 可选：页面内存在未解决的学术分歧
contradictions: [其他页面]       # 可选：与之矛盾的页面
---
```

### type 语义

| type | 含义 | 位置 |
|---|---|---|
| case | 案例页 | entities/案例/ |
| paper | 学术论文页 | entities/引用文献/ |
| norm | 法规范页（含规范实体、版本、条款版本页） | entities/法规范/〈层级〉/ |
| model-article | 目标期刊范文页（只作行文风格参考，不作学术引用） | entities/范文/ |
| draft | 底稿页：用户自己的已完成作品，作为全库锚点 | entities/底稿/ |
| concept | 概念页（含学术史争议地图） | concepts/ |
| comparison | 跨案比较页 | comparisons/ |
| research-design | 研究设计页、论点—证据—引注矩阵、专项方案 | research-design/ |
| methodology | 跨项目方法论、期刊风格观察卡 | methodology/ |
| query | 研究工作页：查询结果、对照表、行文思路 | queries/ |
| moc | 主题或争点导航页（不等于概念页） | queries/ |
| handoff | 会话交接与工作状态页 | queries/ |

`drafts/` 中的用户初稿与思路文件是非正式页面：不加 type、不计入页数、不做链接扩展。

### 类型专属字段

- `case`：逐步补充 `case_id`、`decision_date`、`court`、`docket`、`outcome`、`issues`；按需 `usage`（详析 / 脚注 / 统计 / 不用）、`sample_role`。
- `norm`：必须有 `规范层级`；涉及现行法判断时补 `效力状态`、`生效日期`、`失效日期`、`核验日期`；做时序研究时按 `legal-research-wiki` 的 norm-versioning 参考文件增加版本字段。
- `paper`、`model-article`：作者、刊物、年份等书目信息写在正文“基本信息”，不塞进 `sources`。
- `query`、`moc`、`handoff`：`sources` 可以为空，必须用 `source_note` 说明是库内导航或工作记录。

### sources 规范

- `sources` 只保留原始文件路径（`raw/...`），一个字段一种语义。
- 非路径来源写入 `source_note`；作者名、出处等写入正文。

### 置信度规范

- `source_confidence`：对原始材料提取的置信度。逐项回读原文一般为 high。
- `analysis_status`：`verified` 已逐项回读原文核验；`preliminary` 初步分析；`hypothesis` 假说，未经数据验证；`in_progress` 研究设计、矩阵等进行中的工作页。

## Tag Taxonomy

> 新增标签须先补进下表对应分类再使用；每页 3—5 个；层级、页面标题、来源机构不做标签。

- **域标签**：〈本项目领域词，全库通用，不计入下列分类〉
- **A. 争点 / 事实类**：〈…〉
- **B. 程序与监督类**：〈…〉
- **C. 责任与待遇类（或本领域的实体法律关系类）**：〈…〉
- **D. 研究与方法类**：〈如 群案研究、对比分析、实证分析、统计口径、法律适用、规范演进〉
- **E. 工作页 / 工具类**：〈如 论文写作、行文思路、会话交接、导航、案例索引〉

同义标签的合并、删除决定记在这里，并注明日期。

## Page Thresholds

- 创建新页面：某实体或概念出现在 2 个以上来源中，或是某来源的核心议题。
- 追加到已有页面：来源涉及已有页面覆盖的内容。
- 不创建页面：只被顺便提及的次要内容。
- 拆分页面：超过约 200 行时考虑拆分（只作可读性提示）。

## Update Policy

新信息与已有内容矛盾时，先按类型处理，再谈取舍：
1. **规范新版本**：不覆盖旧版——新旧版本各自保留页面与适用时段；
2. **同一文书的更正**：以更正为准，记录更正依据与日期；
3. **学术观点分歧**：并列保留（`contested` / `contradictions`），不因较新而取代；
4. **资料错误**（转录、编译错误）：纠正并在 `log.md` 记录。

日期新旧本身不构成取代理由；确需合并时保留旧内容与原因，列入检修报告供审阅。

## 目录结构

- `entities/引用文献/`：学术论文（paper）
- `entities/范文/`：目标期刊范文（model-article）
- `entities/底稿/`：用户自己的作品（draft）
- `entities/案例/`：案例（case）。〈是否分子目录、按什么分（引用可用性 / 权威层级 / 争点），由用户确认后写在这里〉
- `entities/法规范/`：按效力层级分子目录，目录序号即引用时的权威顺序：〈列出本项目使用的层级〉
- 案例文件名：`案例N-YYYY-简要案名.md`（N 全局连续，与 YAML `case_id` 一致；年份不详写 `年份不详`）
