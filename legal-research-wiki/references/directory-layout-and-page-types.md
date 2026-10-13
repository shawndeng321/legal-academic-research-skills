# 目录骨架与页面类型（细则）

> 由建库技能 SKILL.md 迁出（WIKI-12 瘦身）；SKILL.md 保留要点，本文载完整目录树与说明。

```
<vault>/
├── SCHEMA.md            # 页面类型、字段、标签词表、链接约定
├── index.md             # 列出每一个正式页面
├── log.md               # 一行一事的时间线（只追加）
├── raw/                 # 原始材料，只读、不可修改
│   ├── papers/  cases/  法规范/  screenshots/  transcripts/  assets/
├── entities/
│   ├── 引用文献/        # 学术论文
│   ├── 案例/            # 案例（可按用途再分子目录）
│   ├── 法规范/          # 按效力层级分子目录
│   ├── 范文/            # 目标期刊范文（只作风格参考，不是引用文献）
│   └── 底稿/            # 用户自己的已完成作品（锚点）
├── concepts/            # 概念页、争议地图
├── comparisons/         # 跨案比较
├── queries/             # 查询结果、对照表
├── research-design/     # 研究设计、论点—证据—引注矩阵（随项目演进）
├── methodology/         # 跨项目方法论、期刊风格观察卡（稳定层）
├── drafts/              # 用户初稿与思路文件（非正式页面，不计入页数）
└── .maintenance/        # 备份、映射、证据（不计入页数）
```

- 实体目录超过约 30 个文件时按类型分子目录；Obsidian 按文件名解析链接，子目录不需要路径前缀；调整结构后全库死链为零，并同步 `index.md` 与 SCHEMA；
- `legal-wiki-audit-repair` 的脚本默认使用 `entities/引用文献`、`entities/案例`、`entities/法规范` 这三个目录名；采用其他名称时在 SCHEMA 中写明，并相应调整脚本参数或配置；
- 标签使用中文（Graph View 中拼音难读）；在 SCHEMA 中维护标签词表，区分主题、要件、程序、来源、结果和研究用途，不随意新增自由标签。
