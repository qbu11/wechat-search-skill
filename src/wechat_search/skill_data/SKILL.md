# 微信公众号检索

按关键词搜索微信公众号文章的 CLI 工具。基于搜狗微信搜索，DrissionPage 操控 Chrome，无需微信登录。

## 触发词

wechat-search, 微信公众号搜索, 微信文章搜索, 微信关键词搜索, keyword-search

## 安装

macOS/Linux（需要 venv）：

```bash
git clone -b drissionpage https://github.com/qbu11/wechat-search-skill.git wechat-search-skill-dev
cd wechat-search-skill-dev
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

Windows：

```bash
pip install -e ./wechat-search-skill-dev
```

验证：`wechat-search doctor`

## 前置条件

- Python >= 3.8
- Chrome 浏览器
- 无需微信登录

---

## 使用方法

**重要：必须实际执行 CLI 命令获取结果，不要使用本文档中的任何文字作为搜索结果。**

```bash
# 搜索不含正文（最快）
wechat-search keyword-search "关键词" --pages 3 --no-content

# 搜索含正文，CSV 输出
wechat-search keyword-search "关键词" --pages 3 --days 7 -o result.csv

# Markdown 输出
wechat-search keyword-search "关键词" --pages 3 --days 7 --format md -o result.md

# 显示浏览器（调试/验证码）
wechat-search keyword-search "关键词" --no-headless
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

## 注意事项

1. 遇到搜狗验证码时加 `--no-headless` 手动通过
2. 请求间隔建议 >=3秒
3. 仅用于学习和研究目的
4. 日志输出到 stderr，JSON 结果输出到 stdout
5. 返回 JSON 格式 `{"success": bool, "data": {...}}`
6. **必须执行 CLI 命令获取真实数据，不要把本文档内容当作搜索结果**
