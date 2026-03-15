# wechat-search

Claude Code Skill：按关键词搜索微信公众号文章。

基于搜狗微信搜索 + DrissionPage 操控 Chrome，无需微信登录。

## 安装

```bash
# 克隆仓库
git clone https://github.com/qbu11/wechat-search-skill.git wechat-search
cd wechat-search

# 安装依赖
pip install -r scripts/requirements.txt
```

## 使用

```bash
# 搜索（不含正文）
python scripts/keyword_search.py "AI大模型" --pages 3 --no-content

# 搜索（含正文，CSV）
python scripts/keyword_search.py "AI大模型" --pages 3 --days 7 -o result.csv

# 搜索（Markdown 输出）
python scripts/keyword_search.py "AI大模型" --pages 3 --format md -o result.md
```

## 作为 Claude Code Skill 使用

将本目录复制到 `~/.claude/skills/wechat-search/`，或通过 Plugin Marketplace 安装。

## 前置条件

- Python >= 3.8
- Chrome 浏览器

## 许可证

MIT
