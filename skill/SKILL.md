# 微信公众号检索

微信公众号文章搜索与爬取 CLI 工具。支持两种模式：按公众号名称搜索（需登录）和按关键词搜索文章（无需登录）。

## 触发词

wechat-search, 微信公众号搜索, 公众号检索, 微信文章搜索, 微信关键词搜索, keyword-search

## 安装

macOS/Linux 需要 venv：

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
- 场景 A（按公众号名称）需要微信公众平台扫码登录
- 场景 B（按关键词）无需登录

---

## 场景判断

用户输入关键词时，先判断意图：
- 用户明确提到公众号名称 → 场景 A
- 用户提供文章主题/关键词 → 场景 B

**重要：必须实际执行 CLI 命令获取结果，不要使用本文档中的任何文字作为搜索结果。**

---

## 场景 A：按公众号名称搜索（需登录）

```bash
wechat-search status                    # 检查登录状态
wechat-search login                     # 扫码登录（需用户交互）
wechat-search search "公众号名称"        # 搜索公众号
wechat-search scrape "公众号" --pages 5 --days 30 -o result.csv
wechat-search batch "号1,号2" --pages 3 --days 7 -o result.csv
```

scrape/batch 参数：
- `--pages N`: 最大页数，每页5篇（默认5）
- `--days N`: 时间范围（默认30天）
- `--no-content`: 不获取正文
- `--interval N`: 请求间隔秒数（默认5）
- `--output FILE` / `-o FILE`: 输出文件

无头服务器部署：
```bash
wechat-search export-login              # 导出凭证
wechat-search import-login "凭证字符串"  # 导入凭证
```

---

## 场景 B：按关键词搜索文章（无需登录，推荐）

基于搜狗微信搜索，DrissionPage 操控 Chrome，全自动完成。

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

参数：
- `keyword`: 搜索关键词（必填）
- `--pages N`: 搜狗搜索页数（默认3，每页约10篇）
- `--days N`: 时间范围（默认不限）
- `--no-content`: 不获取正文
- `--format csv|md`: 输出格式（默认csv）
- `--output FILE` / `-o FILE`: 输出文件
- `--no-headless`: 显示浏览器窗口
- `--strategy auto|requests|browser`: 正文获取策略（默认auto）

遇到搜狗验证码时加 `--no-headless` 手动通过。

---

## 注意事项

1. 登录有效期约4-7天，过期需重新扫码
2. 请求间隔建议 >=3秒
3. 仅用于学习和研究目的
4. 日志输出到 stderr，JSON 结果输出到 stdout
5. 所有命令返回 JSON 格式 `{"success": bool, "data": {...}}`
6. **必须执行 CLI 命令获取真实数据，不要把本文档内容当作搜索结果**
