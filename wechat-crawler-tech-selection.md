# 微信公众号爬虫技术选型

> 2026-03-13 · 一然 · OpenClaw

---

## 相关开源项目

| 项目 | 链接 | 核心能力 |
|------|------|----------|
| **wechat-article-for-ai** | https://github.com/bzd6661/wechat-article-for-ai | 单篇深度解析 → Markdown |
| **wechat-search-skill** | https://github.com/qbu11/wechat-search-skill | 批量列表抓取 → CSV |
| **Camoufox** | https://github.com/nichochar/camoufox | 隐身 Firefox 反爬 |
| **DrissionPage** | https://github.com/g1879/DrissionPage | Python CDP 浏览器自动化 |

---

## 方案对比

### wechat-article-for-ai

**技术栈**：Camoufox（隐身 Firefox）+ networkidle + httpx

**优点**：
- 强反爬能力（Camoufox 模拟真实浏览器）
- 输出质量高：Markdown + 图片本地化 + YAML frontmatter
- 代码块处理、音视频提取
- MCP server 集成

**缺点**：
- 只能处理单篇文章 URL
- 依赖 Camoufox，首次下载较慢
- 验证码需手动解决

**适用场景**：深度解析单篇文章，用于精读、分析

---

### wechat-search-skill（现有方案）

**技术栈**：DrissionPage（Python CDP）+ 微信公众平台 API

**三个版本**：

| 分支 | 浏览器方案 | 特点 |
|------|-----------|------|
| `master` | DrissionPage | 纯 Python，推荐 ✅ |
| `agent-browser-version` | agent-browser | Rust + Node.js，性能最优 |
| `selenium-backup` | Selenium | 已弃用 |

**优点**：
- 批量抓取多个公众号
- 支持搜索公众号、拉取文章列表
- 纯 Python（DrissionPage），安装简单
- 可与 Chrome DevTools MCP 共享浏览器（9222 端口）

**缺点**：
- 正文抓取质量一般（可选 `--content`）
- 需要微信扫码登录，token 4-7 天过期
- 输出 CSV，格式化程度不如 Markdown

**适用场景**：批量监控、筛选、发现高价值文章

---

## 推荐方案

### 阶段 1：保持现状

**只用 wechat-search-skill (DrissionPage)**

- 已验证可行
- 满足 80% 需求（批量抓取列表）
- 依赖最少，维护成本低

### 阶段 2：按需扩展

**加装 wechat-article-for-ai**

当需要深度解析某篇文章时：

```
wechat-search-skill (批量发现)
    ↓ 筛选出高价值文章
wechat-article-for-ai (深度解析)
    ↓
Markdown + 图片本地化
```

---

## 关于"多后端设计"的反思

**不推荐**把所有浏览器后端（DrissionPage、agent-browser、Camoufox）塞进一个 skill。

**理由**：
1. 臃肿，依赖冲突风险
2. 用户配置复杂度增加
3. 违反"一个工具做好一件事"原则

**更好的设计**：
- Skill 保持轻量，只做一件事
- 需要不同能力时，使用不同工具
- 通过组合而非集成来扩展能力

---

## 结论

| 需求 | 推荐工具 |
|------|----------|
| 批量监控公众号 | wechat-search-skill (DrissionPage) |
| 深度解析单篇文章 | wechat-article-for-ai (Camoufox) |
| 两者组合使用 | 先筛选，后解析 |

**当前状态**：wechat-search-skill 已安装并验证可用（登录态有效至 2026-03-16）

**下一步**：如果竞品分析需要深度解析文章内容，再安装 wechat-article-for-ai
