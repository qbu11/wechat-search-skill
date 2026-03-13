# wechat-search-skill

微信公众号文章搜索与爬取工具。pip 可安装，CLI 驱动，支持 Claude Code / OpenClaw Skill 集成。

## 项目结构

```
wechat-search-skill/
├── CLAUDE.md                          # 本文件（开发者指南）
├── pyproject.toml                     # 包定义，入口 wechat-search
├── VERSIONS.md                        # 多版本管理（DrissionPage / agent-browser / Selenium）
├── wechat-article-search-workflow.md  # 场景 B 搜狗搜索工作流参考文档
├── src/wechat_search/
│   ├── cli.py                         # CLI 入口，所有子命令定义（含 doctor）
│   ├── skill_data/SKILL.md            # Skill 文档（随 pip 包分发）
│   └── spider/
│       ├── log/utils.py               # loguru 日志（stderr 输出，自动初始化）
│       └── wechat/
│           ├── login.py               # QR 扫码登录 + 凭证缓存（DrissionPage）
│           ├── scraper.py             # 爬虫核心（WeChatScraper / BatchWeChatScraper）
│           ├── utils.py               # 微信公众平台 API 请求 + HTML→Markdown
│           ├── paths.py               # 跨平台路径管理（缓存目录、输出目录）
│           ├── cache_codec.py         # 凭证导入导出（zlib + CRC32 + Base64）
│           └── async_utils.py         # 异步批量爬取（aiohttp + Semaphore）
└── skill/                             # 旧版 skill 目录（已迁移到 skill_data）
```

## 工作链路

### 完整数据流

```
CLI (cli.py)
 │
 ├─ wechat-search doctor ──→ 环境自检（Python/DrissionPage/Chrome/端口/缓存/网络）
 │
 ├─ wechat-search login ───→ _ensure_login()
 │                              │
 │                              ├─ load_cache() → 读 ~/.../wechat_cache.json
 │                              ├─ validate_cache() → GET /cgi-bin/searchbiz 测试 token
 │                              │
 │                              └─ 缓存无效时：
 │                                  ├─ _connect_to_browser()
 │                                  │   ├─ 方案1: 接管已有 Chrome (端口 9222)
 │                                  │   └─ 方案2: 创建新 Chrome
 │                                  │       ├─ _find_chrome_path() → 跨平台检测
 │                                  │       ├─ _find_available_port() → 9222-9231
 │                                  │       ├─ _setup_chrome_options() → 临时目录 + atexit
 │                                  │       └─ 记录 PID → 定向清理
 │                                  ├─ 导航到 mp.weixin.qq.com
 │                                  ├─ 等待扫码 (5min timeout)
 │                                  ├─ 提取 token (URL regex) + cookies
 │                                  └─ save_cache()
 │
 ├─ wechat-search search ──→ WeChatScraper.search_account()
 │                              └─ utils.get_fakid() → GET /cgi-bin/searchbiz
 │                                  └─ 返回 [{wpub_name, wpub_fakid}, ...]
 │
 ├─ wechat-search scrape ──→ WeChatScraper
 │                              ├─ search_account() → 匹配公众号
 │                              ├─ get_account_articles() → 分页获取文章列表
 │                              │   └─ utils.get_articles_list()
 │                              │       └─ GET /cgi-bin/appmsg (每页5篇, 间隔1-2s)
 │                              ├─ filter_articles_by_date() → 日期过滤
 │                              ├─ get_article_content_by_url() → 逐篇获取正文
 │                              │   └─ utils.get_article_content()
 │                              │       ├─ GET 文章 URL (重试3次, 指数退避)
 │                              │       ├─ BeautifulSoup 解析 HTML
 │                              │       └─ markdownify 转 Markdown
 │                              └─ save_articles_to_csv()
 │
 └─ wechat-search batch ───→ BatchWeChatScraper.start_batch_scrape()
                                ├─ 顺序模式: 逐个公众号处理
                                └─ 多线程模式: ThreadPoolExecutor
```

### 模块依赖关系

```
cli.py ─────────┬─→ login.py (WeChatSpiderLogin)
                ├─→ scraper.py (WeChatScraper, BatchWeChatScraper)
                ├─→ cache_codec.py (encode/decode)
                └─→ paths.py (get_wechat_cache_file, get_default_output_dir)

scraper.py ─────┬─→ utils.py (get_fakid, get_articles_list, get_article_content)
                └─→ log/utils.py (logger)

login.py ───────┬─→ DrissionPage (ChromiumPage, ChromiumOptions)
                ├─→ paths.py (缓存路径)
                └─→ log/utils.py (logger)

utils.py ───────┬─→ requests (HTTP)
                ├─→ beautifulsoup4 + lxml (HTML 解析)
                └─→ markdownify (HTML → Markdown)

async_utils.py ─┬─→ aiohttp (异步 HTTP)
                ├─→ beautifulsoup4 (HTML 解析)
                └─→ markdownify (HTML → Markdown)
```

### 关键数据结构

**缓存文件** (`~/.../WeChatSpider/wechat_cache.json`):
```json
{
  "token": "123456789",
  "cookies": { "slave_sid": "...", "slave_user": "...", ... },
  "timestamp": 1710000000.0
}
```

**文章对象** (scraper 内部):
```python
{
  "name": "公众号名称",
  "title": "文章标题",
  "link": "https://mp.weixin.qq.com/s/...",
  "publish_timestamp": 1710000000,
  "publish_time": "2026-03-10 10:00:00",
  "digest": "",
  "content": "Markdown 正文"
}
```

**凭证编码** (cache_codec): `JSON → UTF-8 → zlib(level=9) → CRC32 → Base64-URL → "WC01" 前缀`

## 可移植性设计

login.py 中的跨平台适配机制（v1.0.0+）：

| 机制 | 函数 | 说明 |
|------|------|------|
| 平台自适应 UA | `_get_platform_user_agent()` | 根据 OS 返回 Chrome 120 UA |
| Chrome 路径检测 | `_find_chrome_path()` | Win: PROGRAMFILES; Mac: /Applications; Linux: which |
| 动态端口检测 | `_find_available_port()` | 9222 被占用自动尝试 9223-9231 |
| PID 定向清理 | `_cleanup_chrome_processes()` | 仅杀本实例创建的 Chrome，不影响用户窗口 |
| 临时目录安全网 | `atexit.register()` | 异常退出时也能清理 tempdir |
| 友好错误提示 | `_connect_to_browser()` | 区分 Chrome 未安装 / 端口占用 / 其他错误 |
| 环境自检 | `wechat-search doctor` | 一键检查 6 项环境依赖 |

## 分支管理

| 分支 | 浏览器方案 | 状态 |
|------|-----------|------|
| `master` | DrissionPage（纯 Python，推荐） | 活跃 |
| `agent-browser-version` | agent-browser（Vercel，Node.js） | 备选 |
| 本地备份 `wechat-search-skill-selenium-backup/` | Selenium | 归档 |

## 开发约定

- Python >= 3.8，无 GUI 依赖
- 所有 CLI 命令输出 JSON 到 stdout，日志输出到 stderr（loguru）
- Windows 必须处理 UTF-8：`_ensure_utf8_stdout()` + `_print_json()`
- 请求间隔 >= 3 秒，避免微信限流
- 登录模块使用 DrissionPage 操控 Chrome（CDP 端口 9222，可自动切换）
- 凭证缓存在跨平台数据目录（Win: `LOCALAPPDATA/WeChatSpider`; Mac: `~/Library/Application Support/WeChatSpider`; Linux: `~/.local/share/WeChatSpider`），有效期约 4 天

## CLI 命令

```bash
wechat-search doctor                    # 环境自检（Chrome、端口、缓存、网络）
wechat-search status                    # 检查登录状态
wechat-search login                     # 扫码登录（弹出 Chrome）
wechat-search search "关键词"            # 搜索公众号
wechat-search scrape "公众号" --pages 5 --days 30 --content --output result.csv
wechat-search batch "号1,号2" --pages 3 --days 7 --content --output-dir ./out
wechat-search export-login              # 导出凭证字符串
wechat-search import-login "凭证字符串"  # 导入凭证
wechat-search install-skill             # 部署 SKILL.md 到 ~/.claude/skills/
```

## 两种搜索模式

### 场景 A：按公众号名称（CLI 工具）

`wechat-search search/scrape/batch`，依赖微信公众平台 API + 登录态。

### 场景 B：按文章关键词（Chrome DevTools MCP + 搜狗）

通过 `weixin.sogou.com` 搜索文章，用 Chrome DevTools MCP 提取列表和正文。

关键限制（已验证）：
- 搜狗有反爬虫机制，`requests` / `WebFetch` 会被重定向到 `/antispider/`
- **必须**使用 Chrome DevTools MCP 浏览器访问
- 逐个访问，每篇间隔 3-5 秒
- 当用户要求"全部内容"/"完整文章"/"正文"时，自动批量抓取，不要先保存摘要再询问

## 打包与部署

```bash
# 安装
pip install .
# 或从 GitHub
pip install git+https://github.com/qbu11/wechat-search-skill.git

# 验证环境
wechat-search doctor

# 部署 Skill
wechat-search install-skill
# → ~/.claude/skills/wechat-search/SKILL.md
# → ~/.openclaw/skills/wechat-search/SKILL.md
```

## 测试

```bash
wechat-search doctor                                          # 环境自检
wechat-search status                                          # 登录态
wechat-search search "人民日报"                                # 搜索
wechat-search scrape "人民日报" --pages 2 --days 7             # 爬取标题
wechat-search scrape "人民日报" --pages 2 --days 7 --content   # 爬取正文
wechat-search export-login                                     # 导出凭证
```

## 已知问题

- Windows 终端 GBK 编码导致 JSON 输出乱码 → 已通过 `_ensure_utf8_stdout()` 修复
- 搜狗链接 requests 跟随跳转被反爬虫拦截 → 只能用浏览器
- 单篇文章抓取失败会中断批量任务 → 已加 try/except 容错
