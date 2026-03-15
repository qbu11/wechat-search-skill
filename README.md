# wechat-search

Claude Code Skill：按关键词搜索微信公众号文章。

基于搜狗微信搜索 + DrissionPage 操控 Chrome，无需微信登录。

## 安装

### 作为 Claude Code Skill

```bash
# 克隆到 skills 目录（推荐）
git clone https://github.com/qbu11/wechat-search-skill.git ~/.claude/skills/wechat-search
cd ~/.claude/skills/wechat-search
pip install -r scripts/requirements.txt
```

新开 Claude Code 会话后，输入"微信文章搜索"或"keyword-search"即可自动触发。

### 独立使用

```bash
git clone https://github.com/qbu11/wechat-search-skill.git wechat-search
cd wechat-search
pip install -r scripts/requirements.txt
```

## 使用

```bash
# 搜索不含正文（最快）
python scripts/keyword_search.py "AI大模型" --pages 3 --no-content

# 搜索含正文，CSV 输出
python scripts/keyword_search.py "AI大模型" --pages 3 --days 7 -o result.csv

# Markdown 输出
python scripts/keyword_search.py "AI大模型" --pages 3 --format md -o result.md

# 显示浏览器窗口（调试/验证码）
python scripts/keyword_search.py "AI大模型" --no-headless
```

## 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `keyword` | (必填) | 搜索关键词 |
| `--pages N` | 3 | 搜狗搜索页数（每页约 10 篇） |
| `--days N` | 不限 | 时间范围（最近 N 天） |
| `--no-content` | 获取正文 | 不获取文章正文 |
| `--format csv\|md` | csv | 输出格式 |
| `--output FILE` / `-o` | 自动生成 | 输出文件路径 |
| `--no-headless` | 无头模式 | 显示浏览器窗口 |
| `--strategy auto\|requests\|browser` | auto | 正文获取策略 |

## 工作流程

```
搜狗微信搜索 → 解析文章列表 → 链接转换(sogou→mp.weixin) → 多策略正文获取 → CSV/Markdown
```

## 项目结构

```
wechat-search/
├── SKILL.md                  # Claude Code Skill 定义（YAML frontmatter）
├── LICENSE.txt
├── README.md
└── scripts/
    ├── requirements.txt      # Python 依赖
    ├── keyword_search.py     # 主入口（CLI argparse）
    ├── sogou_search.py       # 搜狗微信搜索
    ├── url_resolver.py       # 搜狗链接→mp.weixin 转换
    ├── content_fetcher.py    # 多策略正文获取
    ├── article_utils.py      # HTML→Markdown 工具
    └── formatters.py         # CSV/Markdown 输出
```

## 前置条件

- Python >= 3.8
- Chrome 浏览器

## 注意事项

- 遇到搜狗验证码时加 `--no-headless` 手动通过
- 请求间隔 >=3 秒，避免触发反爬
- 仅用于学习和研究目的

## 许可证

MIT
