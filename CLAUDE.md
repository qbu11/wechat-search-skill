# wechat-search-skill

微信公众号文章搜索与爬取工具。

## 项目结构

```
src/wechat_search/
├── cli.py                 # CLI 入口（wechat-search 命令）
├── __init__.py
├── skill_data/SKILL.md    # Skill 文档（pip install 后可部署）
└── spider/
    ├── log/utils.py       # 日志工具（loguru）
    └── wechat/
        ├── login.py       # 登录模块（QR 扫码 + 凭证缓存）
        ├── scraper.py     # 爬虫核心（单号/批量/异步）
        ├── utils.py       # API 请求工具函数
        ├── paths.py       # 路径管理
        ├── cache_codec.py # 凭证导入导出编解码
        └── async_utils.py # 异步爬取支持
```

## 开发约定

- Python >= 3.8，无 GUI 依赖
- 所有命令输出 JSON 到 stdout，日志输出到 stderr
- Windows 环境需处理 UTF-8 编码（cli.py 中 `_ensure_utf8_stdout()`）
- 不使用 `console.log` / `print` 输出非结构化内容
- 请求间隔 >= 3 秒，避免被微信限流

## CLI 命令

| 命令 | 说明 |
|------|------|
| `status` | 检查登录状态 |
| `login` | 扫码登录 |
| `search <query>` | 搜索公众号 |
| `scrape <account>` | 爬取单个公众号 |
| `batch <accounts>` | 批量爬取（逗号分隔） |
| `export-login` | 导出凭证（无头服务器用） |
| `import-login <data>` | 导入凭证 |
| `install-skill` | 部署 SKILL.md 到 ~/.claude/skills/ |

## 两种搜索模式

### 场景 A：按公众号名称（CLI）

直接使用 `wechat-search scrape/batch` 命令，依赖微信公众平台 API + 登录态。

### 场景 B：按文章关键词（Chrome DevTools MCP）

通过搜狗微信搜索 `weixin.sogou.com` 获取文章列表，再用浏览器逐个访问获取正文。

关键限制：
- 搜狗有反爬虫机制，`requests` / `WebFetch` 会被重定向到 `/antispider/`
- 必须使用 Chrome DevTools MCP 浏览器访问
- 逐个访问，每篇间隔 3-5 秒

## 测试

```bash
# 检查登录
wechat-search status

# 搜索
wechat-search search "人民日报"

# 爬取（标题+链接）
wechat-search scrape "人民日报" --pages 2 --days 7

# 爬取（含正文）
wechat-search scrape "人民日报" --pages 2 --days 7 --content
```

## 打包发布

```bash
pip install .
wechat-search install-skill
```
