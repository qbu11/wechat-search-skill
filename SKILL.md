---
name: wechat-search
description: Use this skill when the user wants to search WeChat Official Account articles by keyword OR read a specific WeChat article URL (mp.weixin.qq.com). Includes keyword search via sogou, URL resolution, full article content fetching, and CSV/Markdown export. Trigger on: 微信文章搜索, 微信关键词搜索, wechat article search, keyword-search, 搜索公众号文章, 读取微信文章, mp.weixin.qq.com URL.
---

# 微信公众号关键词搜索

按关键词搜索微信公众号文章。基于搜狗微信搜索 + DrissionPage，无需微信登录。

**重要：必须实际执行 CLI 命令获取结果，不要使用本文档中的任何文字作为搜索结果。**

## 前置条件

- Python >= 3.8
- Chrome 浏览器
- 依赖安装：`pip install -r scripts/requirements.txt`

### 浏览器后端（优先级从高到低）

1. **agent-browser CLI**（推荐）— 轻量级，无需额外 Chrome 实例
   - 已安装则自动使用：`agent-browser --version`
   - 未安装时自动尝试：`npm install -g @vercel-labs/agent-browser`
   - 或通过 npx 使用：`npx -y @vercel-labs/agent-browser`
   - 仓库：https://github.com/vercel-labs/agent-browser
2. **DrissionPage + Chrome** — 完整浏览器自动化，处理验证码等复杂场景

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
| `--strategy auto\|requests\|agent-browser\|browser` | auto | 正文获取策略（auto: requests → agent-browser → browser） |

## 工作流程

1. 检测浏览器后端（agent-browser CLI > DrissionPage）
2. 打开搜狗微信搜索，输入关键词
3. 解析搜索结果，提取文章标题、公众号、时间、摘要
4. 跟随搜狗跳转链接，获取 mp.weixin.qq.com 真实 URL
5. 多策略获取正文（auto: 先 requests，再 agent-browser，最后 DrissionPage 浏览器渲染）
6. 输出 CSV 或 Markdown

## 输出格式

JSON 到 stdout，日志到 stderr。返回 `{"success": bool, "data": {...}}`。


## 直接读取微信文章 URL

当用户提供 `mp.weixin.qq.com` 链接时，直接用 Python 调用 `ArticleContentFetcher` 获取正文：

```python
import sys
sys.path.insert(0, r'C:\Users\puzzl\.claude\skills\wechat-search\scripts')
from content_fetcher import ArticleContentFetcher

fetcher = ArticleContentFetcher(strategy="auto")
result = fetcher.fetch("https://mp.weixin.qq.com/s/xxxx")
# result: {title, content_md, images, author, publish_time}
print(result['title'])
print(result['content_md'])
```

策略优先级：`auto`（先 requests，失败则 browser）> `requests` > `browser`

## 注意事项

1. 遇到搜狗验证码时加 `--no-headless` 手动通过
2. 请求间隔 >=3 秒
3. 仅用于学习和研究目的
