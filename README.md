# wechat-search-skill

微信公众号文章检索 CLI 工具 | WeChat Official Account Article Search & Scrape CLI

---

**中文** | [English](#english)

## 简介

`wechat-search-skill` 是一个自包含的微信公众号文章检索命令行工具。通过微信公众平台 API，支持公众号搜索、文章列表获取、正文内容提取（Markdown 格式），并可集成到 Claude Code / OpenClaw 作为 Skill 使用。

### 功能特性

- 扫码登录，凭证自动缓存（约 4 天有效）
- 按名称搜索公众号
- 单个 / 批量爬取公众号文章
- 正文提取为 Markdown，支持图片、视频等多种文章类型
- JSON 结构化输出，便于工具集成
- 一键部署为 Claude Code / OpenClaw Skill

## 安装

```bash
# 从 GitHub 安装
pip install git+https://github.com/qbu11/wechat-search-skill.git

# 或克隆后本地安装
git clone https://github.com/qbu11/wechat-search-skill.git
pip install ./wechat-search-skill
```

### 环境要求

- Python >= 3.8
- Chrome 浏览器（登录时需要）

### 部署为 Claude Code Skill（可选）

```bash
wechat-search install-skill
```

自动将 SKILL.md 部署到 `~/.claude/skills/wechat-search/`，之后在 Claude Code 中可通过 `/wechat-search` 触发。

## 快速开始

```bash
# 1. 登录（首次使用，需微信扫码）
wechat-search login

# 2. 检查登录状态
wechat-search status

# 3. 搜索公众号
wechat-search search "人民日报"

# 4. 爬取文章（标题 + 链接）
wechat-search scrape "人民日报" --pages 5 --days 30

# 5. 爬取文章（含正文）
wechat-search scrape "人民日报" --pages 5 --days 30 --content

# 6. 保存到 CSV
wechat-search scrape "人民日报" --pages 5 --days 30 --content --output result.csv

# 7. 批量爬取
wechat-search batch "人民日报,新华社,CCTV" --pages 3 --days 7 --content
```

## 命令参考

| 命令 | 说明 |
|------|------|
| `status` | 检查登录状态 |
| `login` | 扫码登录微信公众平台 |
| `search <query>` | 搜索公众号 |
| `scrape <account>` | 爬取单个公众号文章 |
| `batch <accounts>` | 批量爬取（逗号分隔） |
| `install-skill` | 部署 Skill 到 Claude Code / OpenClaw |

### scrape 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--pages` | 最大页数（每页 5 篇） | 5 |
| `--days` | 时间范围（最近 N 天） | 30 |
| `--content` | 获取文章正文 | False |
| `--interval` | 请求间隔（秒） | 5 |
| `--output` | 输出 CSV 文件路径 | - |

### batch 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--pages` | 每号最大页数 | 3 |
| `--days` | 时间范围 | 30 |
| `--content` | 获取正文 | False |
| `--interval` | 请求间隔（秒） | 10 |
| `--output-dir` | 输出目录 | ~/WeChatSpider |

## 输出格式

所有命令输出 JSON：

```json
{
  "success": true,
  "data": {
    "account": "人民日报",
    "total": 10,
    "articles": [
      {
        "title": "文章标题",
        "publish_time": "2026-03-01 10:00:00",
        "link": "https://mp.weixin.qq.com/s/...",
        "content": "正文内容（Markdown，仅 --content 时）"
      }
    ]
  }
}
```

## 作为 Python 库使用

```python
from wechat_search.spider.wechat.login import WeChatSpiderLogin
from wechat_search.spider.wechat.scraper import WeChatScraper

login = WeChatSpiderLogin()
if login.login():
    scraper = WeChatScraper(login.get_token(), login.get_headers())
    accounts = scraper.search_account("人民日报")
    articles = scraper.get_account_articles("人民日报", accounts[0]["wpub_fakid"], max_pages=5)
```

## 注意事项

1. 登录凭证有效期约 4-7 天，过期需重新扫码
2. 请求间隔建议 >= 3 秒，避免被微信限制
3. `--content` 会显著增加耗时，按需使用
4. 日志输出到 stderr，JSON 结果输出到 stdout
5. 仅用于学习和研究目的

---

<a name="english"></a>

**[中文](#简介)** | English

## Introduction

`wechat-search-skill` is a self-contained CLI tool for searching and scraping articles from WeChat Official Accounts (微信公众号). It interacts with the WeChat Official Account Platform API to search accounts, fetch article lists, and extract full article content in Markdown format. It also integrates as a Skill for Claude Code / OpenClaw.

### Features

- QR code login with automatic credential caching (~4 days)
- Search official accounts by name
- Single / batch article scraping
- Full content extraction to Markdown (images, videos, etc.)
- Structured JSON output for tool integration
- One-command deployment as Claude Code / OpenClaw Skill

## Installation

```bash
# From GitHub
pip install git+https://github.com/qbu11/wechat-search-skill.git

# Or clone and install locally
git clone https://github.com/qbu11/wechat-search-skill.git
pip install ./wechat-search-skill
```

### Requirements

- Python >= 3.8
- Chrome browser (required for login)

### Deploy as Claude Code Skill (optional)

```bash
wechat-search install-skill
```

This deploys SKILL.md to `~/.claude/skills/wechat-search/`. After that, trigger it in Claude Code via `/wechat-search`.

## Quick Start

```bash
# 1. Login (first time, requires WeChat QR scan)
wechat-search login

# 2. Check login status
wechat-search status

# 3. Search for an account
wechat-search search "人民日报"

# 4. Scrape articles (titles + links only)
wechat-search scrape "人民日报" --pages 5 --days 30

# 5. Scrape with full content
wechat-search scrape "人民日报" --pages 5 --days 30 --content

# 6. Save to CSV
wechat-search scrape "人民日报" --pages 5 --days 30 --content --output result.csv

# 7. Batch scrape multiple accounts
wechat-search batch "人民日报,新华社,CCTV" --pages 3 --days 7 --content
```

## Command Reference

| Command | Description |
|---------|-------------|
| `status` | Check login status |
| `login` | Login via WeChat QR code |
| `search <query>` | Search official accounts |
| `scrape <account>` | Scrape a single account |
| `batch <accounts>` | Batch scrape (comma-separated) |
| `install-skill` | Deploy Skill to Claude Code / OpenClaw |

### scrape options

| Option | Description | Default |
|--------|-------------|---------|
| `--pages` | Max pages (5 articles/page) | 5 |
| `--days` | Time range (last N days) | 30 |
| `--content` | Fetch article body | False |
| `--interval` | Request interval (seconds) | 5 |
| `--output` | Output CSV file path | - |

### batch options

| Option | Description | Default |
|--------|-------------|---------|
| `--pages` | Max pages per account | 3 |
| `--days` | Time range | 30 |
| `--content` | Fetch article body | False |
| `--interval` | Request interval (seconds) | 10 |
| `--output-dir` | Output directory | ~/WeChatSpider |

## Output Format

All commands output JSON:

```json
{
  "success": true,
  "data": {
    "account": "人民日报",
    "total": 10,
    "articles": [
      {
        "title": "Article Title",
        "publish_time": "2026-03-01 10:00:00",
        "link": "https://mp.weixin.qq.com/s/...",
        "content": "Article body in Markdown (only with --content)"
      }
    ]
  }
}
```

## Use as Python Library

```python
from wechat_search.spider.wechat.login import WeChatSpiderLogin
from wechat_search.spider.wechat.scraper import WeChatScraper

login = WeChatSpiderLogin()
if login.login():
    scraper = WeChatScraper(login.get_token(), login.get_headers())
    accounts = scraper.search_account("人民日报")
    articles = scraper.get_account_articles("人民日报", accounts[0]["wpub_fakid"], max_pages=5)
```

## Notes

1. Login credentials expire in ~4-7 days; re-scan when expired
2. Keep request interval >= 3 seconds to avoid rate limiting
3. `--content` significantly increases scrape time; use only when needed
4. Logs go to stderr, JSON results go to stdout
5. For educational and research purposes only

## Acknowledgments / 致谢

This project is based on [WeMediaSpider](https://github.com/nicekate/WeMediaSpider), refactored into a self-contained pip-installable CLI tool. Thanks to the original contributors.

本项目基于 [WeMediaSpider](https://github.com/nicekate/WeMediaSpider) 重构为自包含的 pip 可安装 CLI 工具，感谢原项目贡献者。

## License

MIT (see [LICENSE](LICENSE)) — includes original WeMediaSpider copyright.
