# 微信文章读取规则

## 默认方式

当用户发送 `mp.weixin.qq.com` 链接时，**默认使用 wechat-search skill 的 ArticleContentFetcher** 读取正文。

**禁止使用 WebFetch**（会被微信验证码拦截）。

## 用法

```python
import sys
sys.path.insert(0, r'~/.claude/skills/wechat-search/scripts')
from content_fetcher import ArticleContentFetcher

fetcher = ArticleContentFetcher(strategy="auto")
result = fetcher.fetch("<url>")
# result: {title, content_md, images, author, publish_time}
```

## 优先级

1. ArticleContentFetcher（wechat-search skill）
2. Chrome DevTools MCP（需 Chrome 调试端口开启）
3. WebFetch（最后手段，大概率被拦截）
