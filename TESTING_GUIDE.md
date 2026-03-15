# wechat-search keyword-search 测试指南

## 环境准备

在目标机器上执行以下命令，克隆并安装：

```bash
cd ~/projects  # 或你的工作目录
git clone -b drissionpage https://github.com/qbu11/wechat-search-skill.git wechat-search-skill-dev
```

### macOS / Linux（Homebrew Python 需要 venv）

```bash
cd wechat-search-skill-dev
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

之后每次使用前需要先 `source .venv/bin/activate`，或者直接用 `.venv/bin/wechat-search`。

### Windows

```bash
pip install -e ./wechat-search-skill-dev
```

### 验证安装

```bash
wechat-search doctor
wechat-search keyword-search --help
```

## 测试用例

### 测试 1：搜索不含正文（最快，验证搜索+链接转换）

```bash
wechat-search keyword-search "AI大模型" --pages 1 --no-content
```

预期：
- 返回约 10 篇文章的 JSON
- 每篇含 title, account, date, link（mp.weixin.qq.com 域名）
- account 字段非空（公众号名称）
- 自动生成 CSV 文件

### 测试 2：搜索含正文，CSV 输出

```bash
wechat-search keyword-search "AI大模型" --pages 1 --days 30 -o test_csv.csv
```

预期：
- 获取正文后保存到 test_csv.csv
- CSV 含列：公众号、标题、发布时间、链接、摘要、内容
- content 字段有 Markdown 格式正文

### 测试 3：Markdown 输出

```bash
wechat-search keyword-search "AI大模型" --pages 1 --days 30 --format md -o test_md.md
```

预期：
- 生成 Markdown 文件，含文章标题、来源、正文

### 测试 4：显示浏览器窗口（调试模式）

```bash
wechat-search keyword-search "DeepSeek" --pages 1 --no-content --no-headless
```

预期：
- 弹出 Chrome 窗口，可以看到搜狗搜索过程
- 如果遇到验证码，可以手动完成

### 测试 5：指定正文获取策略

```bash
# 仅用 requests（最快，但可能内容不完整）
wechat-search keyword-search "人工智能" --pages 1 --days 7 --strategy requests -o test_requests.csv

# 仅用浏览器渲染（较慢，但内容更完整）
wechat-search keyword-search "人工智能" --pages 1 --days 7 --strategy browser -o test_browser.csv
```

## 给 Claude Code 的提示词

直接复制以下内容发给其他机器上的 Claude Code：

---

**提示词 1：安装并验证**

```
帮我在本机安装 wechat-search-skill 的 drissionpage 分支，然后运行 doctor 自检。

步骤：
1. git clone -b drissionpage https://github.com/qbu11/wechat-search-skill.git ~/wechat-search-skill-dev
2. cd ~/wechat-search-skill-dev
3. python3 -m venv .venv && source .venv/bin/activate  （macOS/Linux 必须用 venv，Windows 可跳过）
4. pip install -e .
5. wechat-search doctor
6. wechat-search keyword-search --help

如果遇到 "externally-managed-environment" 错误，说明必须用 venv。
确认所有命令正常运行。
```

**提示词 2：端到端测试**

```
运行 wechat-search keyword-search 的端到端测试：

1. 先测试搜索不含正文：
   wechat-search keyword-search "AI大模型" --pages 1 --no-content
   确认返回 JSON 中 articles 非空，每篇有 title/account/date/link

2. 再测试含正文 CSV 输出：
   wechat-search keyword-search "AI大模型" --pages 1 --days 30 -o test_result.csv
   确认 CSV 文件生成，content 列有内容

3. 测试 Markdown 输出：
   wechat-search keyword-search "AI大模型" --pages 1 --days 30 --format md -o test_result.md
   确认 MD 文件生成

4. 如果遇到搜狗验证码，用 --no-headless 模式手动通过验证码后重试

报告每个测试的结果。
```

**提示词 3：验证码处理**

```
如果 wechat-search keyword-search 遇到搜狗验证码（返回 0 篇文章），请：
1. 用 --no-headless 模式运行：wechat-search keyword-search "AI大模型" --pages 1 --no-content --no-headless
2. 在弹出的浏览器窗口中手动完成验证码
3. 验证码通过后程序会自动继续
```

## 已知问题

1. **搜狗验证码**：频繁搜索会触发验证码，用 `--no-headless` 手动通过
2. **Windows 终端编码**：部分中文可能显示乱码，但 JSON/CSV 数据是正确的（UTF-8）
3. **正文获取失败**：部分文章可能因反爬限制获取不到正文，auto 策略会自动切换 requests → browser
4. **Chrome 未安装**：需要安装 Chrome 浏览器，`wechat-search doctor` 会检测

## 清理

测试完成后删除测试文件：
```bash
rm -f test_csv.csv test_md.md test_requests.csv test_browser.csv test_result.csv test_result.md
```
