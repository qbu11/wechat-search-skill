# wechat-search-skill

Claude Code Skill：微信公众号文章搜索 + URL 直读。

基于搜狗微信搜索 + DrissionPage，无需微信登录。支持两种场景：
1. **关键词搜索** — 按关键词批量搜索微信文章
2. **URL 直读** — 直接读取 `mp.weixin.qq.com` 文章全文

## 安装

```bash
git clone https://github.com/qbu11/wechat-search-skill.git ~/.claude/skills/wechat-search
cd ~/.claude/skills/wechat-search
pip install -r scripts/requirements.txt
```

新开 Claude Code 会话后，发送微信链接或输入"微信文章搜索"即可自动触发。

## 功能一：关键词搜索

```bash
python scripts/keyword_search.py "AI大模型" --pages 3 -o result.csv
python scripts/keyword_search.py "AI大模型" --pages 3 --days 7 --format md -o result.md
python scripts/keyword_search.py "AI大模型" --no-headless  # 显示浏览器（验证码）
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `keyword` | (必填) | 搜索关键词 |
| `--pages N` | 3 | 搜索页数（每页约10篇） |
| `--days N` | 不限 | 时间范围 |
| `--no-content` | 获取正文 | 不获取正文 |
| `--format csv\|md` | csv | 输出格式 |
| `--output FILE` | 自动 | 输出文件 |
| `--strategy auto\|requests\|browser` | auto | 正文获取策略 |

## 功能二：直接读取微信文章 URL

当用户发送 `mp.weixin.qq.com` 链接时，Claude 自动调用 `ArticleContentFetcher` 读取全文：

```python
import sys
sys.path.insert(0, r'~/.claude/skills/wechat-search/scripts')
from content_fetcher import ArticleContentFetcher

fetcher = ArticleContentFetcher(strategy="auto")
result = fetcher.fetch("https://mp.weixin.qq.com/s/xxxxx")
# result: {title, content_md, images, author, publish_time}
```

| 策略 | 说明 |
|------|------|
| `auto`（默认） | 先 requests，失败则 browser |
| `requests` | 纯 HTTP，最快 |
| `browser` | DrissionPage 渲染 |

## 自动化配置（Hook + Rule）

WebFetch 访问微信文章会被验证码拦截。通过以下配置让 Claude 自动使用本 skill：

### 1. 安装 Hook — 拦截 WebFetch

```bash
cp hooks/block-webfetch-wechat.js ~/.claude/hooks/
```

在 `~/.claude/settings.json` 添加：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "WebFetch",
        "hooks": [
          {
            "type": "command",
            "command": "node ~/.claude/hooks/block-webfetch-wechat.js",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

### 2. 安装 Rule — 设置默认读取方式

```bash
cp docs/wechat-reading.md ~/.claude/rules/
```

### 一键安装

```bash
git clone https://github.com/qbu11/wechat-search-skill.git ~/.claude/skills/wechat-search
cd ~/.claude/skills/wechat-search
pip install -r scripts/requirements.txt
cp hooks/block-webfetch-wechat.js ~/.claude/hooks/
cp docs/wechat-reading.md ~/.claude/rules/
# 手动将 hook JSON 配置加入 ~/.claude/settings.json
```

## 项目结构

```
wechat-search-skill/
├── SKILL.md                           # Claude Code Skill 定义
├── README.md
├── LICENSE.txt
├── hooks/
│   └── block-webfetch-wechat.js       # PreToolUse Hook
├── docs/
│   └── wechat-reading.md             # 全局 Rule 模板
└── scripts/
    ├── requirements.txt
    ├── keyword_search.py              # CLI 主入口
    ├── sogou_search.py                # 搜狗搜索
    ├── url_resolver.py                # 链接转换
    ├── content_fetcher.py             # 多策略正文获取
    ├── article_utils.py               # HTML→Markdown
    └── formatters.py                  # CSV/MD 输出
```

## 触发词

- `微信文章搜索` / `微信关键词搜索` / `搜索公众号文章`
- `读取微信文章`
- 直接发送 `mp.weixin.qq.com` 链接
- `wechat article search` / `keyword-search`

## 注意事项

- 搜狗验证码时加 `--no-headless`
- 请求间隔 >=3 秒
- 仅用于学习和研究目的

## License

MIT
