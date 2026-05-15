# 微信公众号文章搜索 & 读取

Claude Code 插件，让 AI 助手能搜索和读取微信公众号文章。

## 能做什么

- **搜索文章**：输入关键词，自动搜索微信公众号文章并提取全文
- **读取链接**：发送微信文章链接，自动获取标题和正文内容

无需微信登录，开箱即用。

## 安装

```bash
# 1. 下载插件
git clone https://github.com/qbu11/wechat-search-skill.git ~/.claude/skills/wechat-search

# 2. 安装依赖
cd ~/.claude/skills/wechat-search
pip install -r scripts/requirements.txt

# 3. 安装防误用钩子（可选，推荐）
cp hooks/block-webfetch-wechat.js ~/.claude/hooks/

# 4. 安装默认规则（可选，推荐）
cp docs/wechat-reading.md ~/.claude/rules/
```

安装完成后重启 Claude Code 即可使用。

## 怎么用

### 读取一篇文章

直接把微信文章链接发给 Claude：

> https://mp.weixin.qq.com/s/xxxxx

Claude 会自动读取并返回文章全文。

### 搜索文章

对 Claude 说：

> 帮我搜索"AI大模型"相关的微信文章

或者直接运行命令：

```bash
python scripts/keyword_search.py "AI大模型" --pages 3 -o result.csv
```

## 为什么需要钩子和规则

微信文章有反爬机制，Claude 默认的网页读取工具（WebFetch）会被拦截。

安装钩子后，Claude 遇到微信链接会**自动切换**到本插件的专用读取器，无需手动提醒。

### 钩子配置

安装钩子文件后，还需在 `~/.claude/settings.json` 中添加以下配置：

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

如果 `settings.json` 中已有其他 `hooks` 配置，把上面的内容合并进去即可。

## 文件说明

```
├── SKILL.md                        # 插件定义（Claude Code 自动识别）
├── hooks/
│   └── block-webfetch-wechat.js    # 钩子：拦截 WebFetch 访问微信
├── docs/
│   └── wechat-reading.md           # 规则：告诉 Claude 用本插件读微信
└── scripts/
    ├── requirements.txt            # Python 依赖
    ├── keyword_search.py           # 关键词搜索（命令行工具）
    ├── content_fetcher.py          # 文章正文获取（核心）
    ├── sogou_search.py             # 搜狗微信搜索
    ├── url_resolver.py             # 链接解析
    ├── article_utils.py            # HTML 转 Markdown
    └── formatters.py               # 输出格式化
```

## 环境要求

- Python 3.8+
- Chrome 浏览器

## 常见问题

**Q: 搜索时遇到验证码怎么办？**

加 `--no-headless` 参数会弹出浏览器窗口，手动完成验证后继续。

**Q: 读取文章失败？**

插件会自动尝试多种方式读取。如果纯 HTTP 方式失败，会自动切换到浏览器模式。

**Q: 支持哪些链接格式？**

支持所有 `mp.weixin.qq.com` 开头的文章链接。

## 许可证

MIT
