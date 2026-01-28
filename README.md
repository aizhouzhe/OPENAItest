# 每日未读/未回复邮件整理工具

这是一个基于 IMAP 的自动化脚本，用来每天整理「未读」或「未回复」邮件，并输出可追踪的日报告（Markdown）。

## 功能

- 自动检索 **未读 (UNSEEN)** 或 **未回复 (UNANSWERED)** 邮件
- 生成 Markdown 报告，便于留档
- 可选：把待处理邮件移动到指定文件夹（例如 `Triage`）
- 支持 `cron` 或任务调度器每日执行

## 安装与准备

1. 准备 IMAP 账号/应用密码（例如 Gmail 的 App Password）。
2. 复制配置文件并填写：

```bash
cp config.example.json config.json
```

3. 编辑 `config.json`：

```json
{
  "imap_host": "imap.example.com",
  "imap_port": 993,
  "username": "you@example.com",
  "password": "app_password_or_token",
  "mailbox": "INBOX",
  "criteria": "OR UNSEEN UNANSWERED",
  "max_items": 50,
  "report_path": "reports/daily-email-triage.md",
  "move_to_folder": "Triage"
}
```

> 小提示：
> - `criteria` 使用 IMAP 搜索语法，默认会匹配「未读或未回复」。
> - `move_to_folder` 为空则不移动邮件。

## 使用方法

```bash
python3 email_triage.py --config config.json
```

运行后会输出报告，并按 `report_path` 保存。

## 每日自动化（示例）

使用 `cron`：

```bash
crontab -e
```

加入：

```bash
0 9 * * * /usr/bin/python3 /path/to/email_triage.py --config /path/to/config.json >> /path/to/triage.log 2>&1
```

## 注意事项

- 请确保 IMAP 账号安全，建议使用应用专用密码。
- 部分邮箱服务需要在后台开启 IMAP。
- 若启用移动功能，脚本会创建指定文件夹并将邮件从原邮箱删除（实际为复制+删除）。

