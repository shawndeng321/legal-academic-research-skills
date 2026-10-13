# Obsidian 解析规则与幽灵文件（细则）

> 由审计技能 SKILL.md 4.4 节迁出（WIKI-12 瘦身）；报告口径保留在 SKILL.md。

**Obsidian 真实解析规则**（详见 `legal-research-wiki` 的 `references/linking-and-cross-references.md`）：

- 别名分隔先按 `\|` 再按 `|` 拆：`re.split(r'\\\||(?<!\\)\|', raw)[0]`；
- `&#124;` 不是分隔符，出现处按死链计并列为 P1；
- 反引号内的示例链接也会被图谱解析；维护文档中的示例一律写纯文本，包括自己新追加的日志条目；
- Graph View 空白节点排查 = 全库未解析链接扫描，文件列表干净不等于图谱干净；
- **畸形链接**：缺右括号的 `[[目标]`（用宽容正则 `\[\[([^\]\n]{2,200})\]` 并检查其后字符不是 `]`）、吞掉下一行标题的 `[[目标## …`、嵌套 `[[[[`/`]]]]`；
- **幽灵文件复活**：删除 `…&.md` 等 0 字节幽灵文件后，`.obsidian/workspace.json` 的 `lastOpenFiles` 仍会在下次启动时重建它们。清理时：①从 workspace.json 剥离相关路径并复查（首轮可能漏）；②在 `app.json` 的 `userIgnoreFilters` 中加入 `.maintenance`、`ghosts`；③请用户完全退出 Obsidian 再打开；
- 检查文件存在时带 `.md` 后缀，裸名永远不存在；
- 案号匹配用完整案号并同时处理全角、半角括号。
