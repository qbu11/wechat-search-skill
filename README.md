# 微信公众号检索工具

微信公众号文章搜索与爬取命令行工具。通过微信公众平台 API 检索公众号和文章。

## 安装

```bash
# 从本地目录安装
pip install ./wechat-search-skill

# 开发模式安装（可编辑）
pip install -e ./wechat-search-skill
```

## 依赖

- Python >= 3.8
- Chrome 浏览器（登录时需要）

## 快速开始

### 1. 检查登录状态

```bash
wechat-search status
```

### 2. 登录（扫码）

```bash
wechat-search login
```

### 3. 搜索公众号

```bash
wechat-search search "人民日报"
```

### 4. 爬取文章

```bash
# 只获取标题和链接
wechat-search scrape "人民日报" --pages 5 --days 30

# 获取正文内容
wechat-search scrape "人民日报" --pages 5 --days 30 --content

# 保存到 CSV
wechat-search scrape "人民日报" --pages 5 --days 30 --content --output result.csv
```

### 5. 批量爬取

```bash
wechat-search batch "人民日报,新华社,CCTV" --pages 3 --days 7 --content
```

## 命令说明

### status

检查当前登录状态。

### login

通过扫码登录微信公众平台。登录成功后凭证会缓存约 4 天。

### search `<query>`

搜索公众号。

### scrape `<account>`

爬取单个公众号的文章。

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--pages` | 最大页数（每页 5 篇） | 5 |
| `--days` | 时间范围（最近 N 天） | 30 |
| `--content` | 是否获取正文 | False |
| `--interval` | 请求间隔（秒） | 5 |
| `--output` | 输出 CSV 文件 | - |

### batch `<accounts>`

批量爬取多个公众号。公众号名称用逗号分隔。

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--pages` | 每号最大页数 | 3 |
| `--days` | 时间范围 | 30 |
| `--content` | 是否获取正文 | False |
| `--interval` | 请求间隔（秒） | 10 |
| `--output-dir` | 输出目录 | ~/WeChatSpider |

## 输出格式

所有命令输出 JSON：

```json
{
  "success": true,
  "data": {
    "account": "公众号名称",
    "total": 10,
    "articles": [...]
  }
}
```

## 注意事项

1. 登录凭证有效期约 4-7 天
2. 请求间隔建议 >=3 秒
3. 获取正文会显著增加耗时
4. 仅用于学习研究目的

## 许可证

MIT
