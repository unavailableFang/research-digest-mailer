# 信息推送助手

每天上午 9 点把科研相关进展整理成一封适合电脑和手机阅读的 HTML 邮件。当前版本从 Crossref 检索已发表期刊论文，只保留配置中影响因子大于 10 的期刊，并按影响因子优先排序。

## 1. 调整关键词和期刊白名单

编辑 [config/topics.toml](/Users/fangyanbo/Documents/信息推送助手/config/topics.toml)。

关键词已按你的要求设置为：

```toml
keywords = [
  "smart window",
  "radiative cooling",
  "micro/nano manufacturing",
  "micro nano manufacturing",
  "micronano manufacturing",
  "3D printing",
  "additive manufacturing"
]
```

期刊白名单示例：

```toml
[[journals]]
name = "Advanced Materials"
impact_factor = 27.4
```

注意：影响因子每年更新，而且没有可靠免费官方 API。请按你手头的最新版 JCR、期刊官网或课题组认可的数据更新 `impact_factor`。程序只会推送 `impact_factor > minimum_impact_factor` 的期刊文章，默认阈值是 10。

常用设置：

- `days_back`：回看最近几天，默认 7 天。
- `max_items`：一封邮件最多显示多少篇。
- `minimum_impact_factor`：最低影响因子阈值，默认 10。
- `timezone`：默认 `Asia/Hong_Kong`。

## 2. 本地预览

```bash
python3 -m pip install -e .
PYTHONPATH=src python3 -m research_digest.cli --preview digest-preview.html
open digest-preview.html
```

只看纯文本结果，不发邮件：

```bash
PYTHONPATH=src python3 -m research_digest.cli --dry-run
```

## 3. 配置邮箱发送

建议使用邮箱的“应用专用密码”或“SMTP 授权码”，不要使用网页登录密码。

```bash
export SMTP_HOST=smtp.example.com
export SMTP_PORT=465
export SMTP_USER=your-email@example.com
export SMTP_PASSWORD=your-app-password
export SMTP_SSL=true
export MAIL_FROM=your-email@example.com
export MAIL_TO=your-email@example.com

PYTHONPATH=src python3 -m research_digest.cli
```

常见 SMTP：

- Gmail：`SMTP_HOST=smtp.gmail.com`，`SMTP_PORT=465`，需要应用专用密码。
- Outlook：`SMTP_HOST=smtp.office365.com`，`SMTP_PORT=587`，设置 `SMTP_SSL=false`。
- QQ 邮箱：`SMTP_HOST=smtp.qq.com`，`SMTP_PORT=465`，需要 SMTP 授权码。

可选：设置 `CROSSREF_MAILTO=你的邮箱`，方便 Crossref 联系高频 API 使用者。

## 4. 去重、图片和中文摘要

实际发信成功后，程序会把已发送论文的 DOI 记录到 `.digest-state/sent.json`。下一次发信会自动过滤这些 DOI，即使 `days_back` 与前一天重叠，也不会重复推送同一篇文章。

预览和 dry-run 不会写入发送历史，方便你反复检查内容：

```bash
PYTHONPATH=src python3 -m research_digest.cli --preview digest-preview.html
PYTHONPATH=src python3 -m research_digest.cli --dry-run
```

如果需要临时忽略发送历史重新发送，可加：

```bash
PYTHONPATH=src python3 -m research_digest.cli --include-sent
```

邮件会显示 Crossref 提供的完整英文 Abstract，不再截断。若配置了翻译 API，也会显示完整中文翻译。

邮件会尝试从每篇文章页面提取图片摘要或代表图。当前会依次检查 `citation_image`、`og:image`、`twitter:image` 等元数据、JSON-LD 里的 article image、`link rel=image_src/preload`，以及页面中的高相关图片候选。不是所有期刊页面都会提供可用于邮件显示的图片；若页面反爬、图片懒加载或只在搜索页展示，邮件可能仍然没有图片。

中文摘要使用 Google Cloud Translation API Basic v2。设置 `GOOGLE_TRANSLATE_API_KEY` 后会自动翻译：

```bash
export GOOGLE_TRANSLATE_API_KEY=你的 Google Translation API key
```

可选：默认从英文翻译到简体中文。如果需要调整语言，可设置：

```bash
export GOOGLE_TRANSLATE_SOURCE=en
export GOOGLE_TRANSLATE_TARGET=zh-CN
```

如果没有设置 `GOOGLE_TRANSLATE_API_KEY`，邮件仍会正常发送，只是中文摘要位置会显示“未配置翻译或翻译暂不可用”。

## 5. 每天上午 9 点自动推送

### 方案 A：GitHub Actions

把项目推到 GitHub 后，在仓库的 `Settings -> Secrets and variables -> Actions` 添加：

`SMTP_HOST`、`SMTP_PORT`、`SMTP_USER`、`SMTP_PASSWORD`、`SMTP_SSL`、`MAIL_FROM`、`MAIL_TO`

如果要生成中文摘要，再添加 `GOOGLE_TRANSLATE_API_KEY`。GitHub Actions 会缓存 `.digest-state`，用于跨天记录已推送 DOI。

[.github/workflows/daily-digest.yml](/Users/fangyanbo/Documents/信息推送助手/.github/workflows/daily-digest.yml) 已设置为每天 `18:00 UTC` 运行，也就是香港时间凌晨 2 点。

### 方案 B：macOS launchd

先把 [launchd/com.local.research-digest.plist](/Users/fangyanbo/Documents/信息推送助手/launchd/com.local.research-digest.plist) 里的 SMTP 信息替换成你的邮箱配置，然后执行：

```bash
cp launchd/com.local.research-digest.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.local.research-digest.plist
```

手动触发一次：

```bash
launchctl start com.local.research-digest
```

查看日志：

```bash
tail -n 100 /tmp/research-digest.out.log
tail -n 100 /tmp/research-digest.err.log
```

## 6. 运行测试

```bash
python3 -m pip install -e ".[dev]"
pytest
```
