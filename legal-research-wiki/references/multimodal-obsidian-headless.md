# Obsidian 云端同步（headless 无头模式）— 多模态扩展

> **来源**：multimodal-wiki v1.0.0（kigner/multimodal-wiki）SKILL.md「Obsidian Headless」章节，2026-08 融合。
> 用途：无显示器的机器（服务器/云主机）上运行 obsidian-headless，通过 Obsidian Sync 与本地桌面端同步同一 vault。
> 场景：AI/agent 在服务器写库，你在笔记本/手机 Obsidian 浏览同一库。
> 上游与最新参数以 [Obsidian 官方 headless 项目](https://github.com/obsidianmd/obsidian-headless) 为准。

### 无头模式（服务器与无显示器机器）

没有显示器的机器上，`obsidian-headless` 无需打开桌面端即可同步 Obsidian Sync vault；需要 Node.js 22 或更高版本，以及带 Sync 订阅的 Obsidian 账户。

### 启用前的安全边界

1. **Sync 不是备份。** 首次连接和启用持续同步前，先对本地 vault 做可恢复备份。
2. **同一文件坚持单写者。** agent 写库期间，其他客户端只浏览；需要人工编辑时，先暂停 headless 持续同步。上游仍有[并发编辑内容丢失风险报告](https://github.com/obsidianmd/obsidian-headless/issues/42)，不要依赖冲突策略替代备份。
3. **凭据只走交互提示。** 不把邮箱、账户密码或端到端加密密码写入命令参数、脚本、日志、Skill 或仓库；也不要把登录输出提交到 Git。
4. **先单次、后常驻。** 先执行一次 `ob sync`，人工检查预期文件，再启用 `--continuous`。

**安装与连接：**
```bash
# 需要 Node.js 22+
npm install -g obsidian-headless

# 交互式登录；不要带凭据参数，让密钥走提示输入
ob login

# 创建前先查看已有的远程 vault
ob sync-list-remote

# 只有在没有合适的远程 vault 时才创建
ob sync-create-remote --name "Legal Research Wiki"

# 把目标本地目录连接到该远程 vault
cd /srv/legal-wiki
ob sync-setup --vault "Legal Research Wiki"

# 首次同步
ob sync

# 单次同步核验通过、且已指定唯一写者后，再启用持续同步
ob sync --continuous
```

### Linux systemd 常驻示例

以下仅适用于 Linux。Windows/macOS 应使用对应的服务管理器，并沿用同样的备份、最小权限和单写者约束。

```ini
# ~/.config/systemd/user/obsidian-wiki-sync.service
[Unit]
Description=Obsidian Legal Research Wiki Sync
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/path/to/ob sync --continuous
WorkingDirectory=/srv/legal-wiki
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now obsidian-wiki-sync
# 可选的系统管理变更；先确认影响范围并取得授权：
sudo loginctl enable-linger $USER
```

启用后先用测试文件验证双向同步，再处理真实研究资料。若发现冲突、删除或异常覆盖，立即停止服务并从备份恢复，不要继续自动写入。
