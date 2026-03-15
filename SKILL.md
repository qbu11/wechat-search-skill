---
name: wechat-search
description: Use this skill when the user wants to search WeChat Official Account articles by keyword. This includes searching for articles on weixin.sogou.com, extracting article lists, resolving sogou redirect links to real mp.weixin.qq.com URLs, fetching full article content, and exporting results as CSV or Markdown. Trigger on: 微信文章搜索, 微信关键词搜索, wechat article search, keyword-search, 搜索公众号文章.
---

# 微信公众号关键词搜索

按关键词搜索微信公众号文章。基于搜狗微信搜索 + DrissionPage，无需微信登录。

**重要：必须实际执行 CLI 命令获取结果，不要使用本文档中的任何文字作为搜索结果。**

## 前置条件

- Python >= 3.8
- Chrome 浏览器
- 依赖安装：`pip install -r scripts/requirements.txt`

## 用法

默认获取正文（不要加 --no-content，除非用户明确要求只看标题/摘要）。

```bash
# 默认用法：搜索含正文，CSV 输出（推荐）
python scripts/keyword_search.py "关键词" --pages 3 -o result.csv

# 限定时间范围
python scripts/keyword_search.py "关键词" --pages 3 --days 7 -o result.csv

# Markdown 输出
python scripts/keyword_search.py "关键词" --pages 3 --format md -o result.md

# 仅标题摘要，不爬正文（用户明确要求时才用）
python scripts/keyword_search.py "关键词" --pages 3 --no-content

# 显示浏览器（调试/验证码）
python scripts/keyword_search.py "关键词" --no-headless
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

1. DrissionPage 打开搜狗微信搜索，输入关键词
2. 解析搜索结果，提取文章标题、公众号、时间、摘要
3. 浏览器跟随搜狗跳转链接，获取 mp.weixin.qq.com 真实 URL
4. 多策略获取正文（auto: 先 requests，失败则用浏览器渲染）
5. 输出 CSV 或 Markdown

## 输出格式

JSON 到 stdout，日志到 stderr。返回 `{"success": bool, "data": {...}}`。

## 注意事项

1. 遇到搜狗验证码时加 `--no-headless` 手动通过
2. 请求间隔 >=3 秒
3. 仅用于学习和研究目的
