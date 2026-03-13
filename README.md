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
- Chrome 浏览器（登录时需要，未安装时会给出平台对应的安装提示）

### 环境自检

```bash
wechat-search doctor
```

检查 Python 版本、DrissionPage、Chrome 路径、端口 9222 状态、登录缓存、网络连通性。JSON 输出到 stdout，人类可读格式输出到 stderr。

### 部署为 Claude Code Skill（可选）

```bash
wechat-search install-skill
```

自动将 SKILL.md 部署到 `~/.claude/skills/wechat-search/`，之后在 Claude Code 中可通过 `/wechat-search` 触发。

## 快速开始

### 两种搜索模式

本工具支持两种搜索模式：

1. **按公众号名称搜索**：用户知道具体公众号名，使用 CLI 工具直接爬取
2. **按文章关键词搜索**：用户想跨公众号搜索相关文章，需配合 Chrome DevTools MCP 使用搜狗微信搜索

**自动判断**：先运行 `wechat-search search "关键词"`，如果返回的公众号列表不相关，则切换到搜狗搜索模式。

### CLI 快速上手

```bash
# 0. 环境自检（推荐首次使用时运行）
wechat-search doctor

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

# 8. 导出登录凭证（用于无头服务器部署）
wechat-search export-login

# 9. 在无头服务器上导入凭证
wechat-search import-login "导出的凭证字符串"
```

### 无头服务器部署

如果需要在无浏览器的服务器上使用，可以先在本地机器上登录并导出凭证：

```bash
# 在本地机器（有浏览器）
wechat-search login
wechat-search export-login
# 复制输出的凭证字符串

# 在无头服务器上
wechat-search import-login "粘贴凭证字符串"
wechat-search status  # 验证登录成功
```

## 命令参考

| 命令 | 说明 |
|------|------|
| `doctor` | 环境自检（Chrome、端口、缓存、网络） |
| `status` | 检查登录状态 |
| `login` | 扫码登录微信公众平台 |
| `search <query>` | 搜索公众号 |
| `scrape <account>` | 爬取单个公众号文章 |
| `batch <accounts>` | 批量爬取（逗号分隔） |
| `install-skill` | 部署 Skill 到 Claude Code / OpenClaw |
| `export-login` | 导出登录凭证（用于无头服务器） |
| `import-login <data>` | 导入登录凭证 |

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
- Chrome browser (required for login; provides platform-specific install hints if missing)

### Environment Check

```bash
wechat-search doctor
```

Checks Python version, DrissionPage, Chrome path, port 9222 status, login cache, and network connectivity. JSON to stdout, human-readable to stderr.

### Deploy as Claude Code Skill (optional)

```bash
wechat-search install-skill
```

This deploys SKILL.md to `~/.claude/skills/wechat-search/`. After that, trigger it in Claude Code via `/wechat-search`.

## Quick Start

### Two Search Modes

This tool supports two search modes:

1. **Search by Account Name**: When you know the specific account name, use CLI directly
2. **Search by Article Keywords**: When you want to search articles across accounts, use Sogou WeChat Search with Chrome DevTools MCP

**Auto-detection**: Run `wechat-search search "keyword"` first. If returned accounts are irrelevant, switch to Sogou search mode.

### CLI Quick Start

```bash
# 0. Environment check (recommended on first use)
wechat-search doctor

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

# 8. Export credentials (for headless servers)
wechat-search export-login

# 9. Import credentials on headless server
wechat-search import-login "exported-credential-string"
```

### Headless Server Deployment

For servers without a browser, export credentials from a local machine first:

```bash
# On local machine (with browser)
wechat-search login
wechat-search export-login
# Copy the credential string

# On headless server
wechat-search import-login "paste-credential-string"
wechat-search status  # Verify login success
```

## Command Reference

| Command | Description |
|---------|-------------|
| `doctor` | Check environment (Chrome, port, cache, network) |
| `status` | Check login status |
| `login` | Login via WeChat QR code |
| `search <query>` | Search official accounts |
| `scrape <account>` | Scrape a single account |
| `batch <accounts>` | Batch scrape (comma-separated) |
| `install-skill` | Deploy Skill to Claude Code / OpenClaw |
| `export-login` | Export credentials (for headless servers) |
| `import-login <data>` | Import credentials |

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
