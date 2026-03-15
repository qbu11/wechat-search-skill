#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号关键词搜索 — 主入口脚本
==================================

通过搜狗微信搜索按关键词搜索微信公众号文章，无需微信登录。

用法:
    python keyword_search.py "AI大模型" --pages 3 --days 7 -o result.csv
    python keyword_search.py "AI大模型" --pages 1 --no-content
    python keyword_search.py "AI大模型" --pages 3 --format md -o result.md
"""

import argparse
import io
import json
import logging
import os
import sys
from datetime import datetime


def _ensure_utf8_stdout():
    """强制 stdout/stderr 使用 UTF-8 编码，解决 Windows 终端乱码问题"""
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except Exception:
            pass

    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)


def _setup_logging():
    """配置日志输出到 stderr"""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S'))
    logger = logging.getLogger("wechat-search")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


def _print_json(data):
    """安全地输出 JSON 到 stdout，确保 UTF-8 编码"""
    text = json.dumps(data, ensure_ascii=False, indent=2)
    try:
        sys.stdout.write(text + '\n')
        sys.stdout.flush()
    except (UnicodeEncodeError, OSError):
        text_ascii = json.dumps(data, ensure_ascii=True, indent=2)
        sys.stdout.write(text_ascii + '\n')
        sys.stdout.flush()


def main():
    _ensure_utf8_stdout()
    logger = _setup_logging()

    parser = argparse.ArgumentParser(
        description="微信公众号关键词搜索（搜狗微信，无需登录）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python keyword_search.py "AI大模型" --pages 3 --days 7 -o result.csv
  python keyword_search.py "AI大模型" --pages 1 --no-content
  python keyword_search.py "AI大模型" --format md -o result.md
        """,
    )
    parser.add_argument("keyword", help="搜索关键词")
    parser.add_argument("--pages", type=int, default=3, help="搜狗搜索页数（默认3，每页约10篇）")
    parser.add_argument("--days", type=int, default=None, help="时间范围（最近N天，默认不限）")
    parser.add_argument("--no-content", action="store_true", help="不获取文章正文（默认获取）")
    parser.add_argument("--format", choices=["csv", "md"], default="csv", help="输出格式（默认 csv）")
    parser.add_argument("--output", "-o", default=None, help="输出文件路径（默认自动生成）")
    parser.add_argument("--no-headless", action="store_true", help="显示浏览器窗口（默认无头模式）")
    parser.add_argument("--strategy", choices=["auto", "requests", "browser"], default="auto", help="正文获取策略（默认 auto）")

    args = parser.parse_args()

    headless = not args.no_headless
    include_content = not args.no_content

    logger.info("关键词搜索: %s (页数=%d, 天数=%s, 正文=%s)", args.keyword, args.pages, args.days, include_content)

    # 同目录导入
    from sogou_search import SogouWeChatSearch
    from url_resolver import SogouUrlResolver
    from content_fetcher import ArticleContentFetcher
    from formatters import save_articles_to_csv, save_articles_to_md

    # Step 1: 搜狗搜索
    searcher = SogouWeChatSearch(headless=headless)
    try:
        articles = searcher.search(args.keyword, max_pages=args.pages, days=args.days)
    finally:
        browser_page = searcher._page
        searcher._owns_page = False  # 防止 close 时关闭

    if not articles:
        _print_json({"success": False, "error": "未找到相关文章"})
        return 1

    logger.info("搜索到 %d 篇文章，开始转换链接...", len(articles))

    # Step 2: 链接转换（复用浏览器实例）
    resolver = SogouUrlResolver(page=browser_page)
    try:
        articles = resolver.batch_resolve(articles)
    finally:
        pass  # 不关闭，后续 content_fetcher 可能还要用

    # Step 3: 获取正文（可选）
    if include_content:
        fetcher = ArticleContentFetcher(strategy=args.strategy, page=browser_page)
        try:
            articles = fetcher.fetch_batch(articles, delay=3)
        finally:
            fetcher._owns_page = False

    # 关闭浏览器
    if browser_page is not None:
        try:
            browser_page.quit()
        except Exception:
            pass

    # Step 4: 输出
    output_file = args.output
    if not output_file:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = 'md' if args.format == 'md' else 'csv'
        output_file = f"keyword_search_{ts}.{ext}"

    if args.format == 'md':
        save_articles_to_md(articles, output_file)
    else:
        save_articles_to_csv(articles, output_file)

    # 构建 JSON 输出
    articles_output = []
    for a in articles:
        item = {
            "title": a.get("title", ""),
            "account": a.get("account", ""),
            "date": a.get("date", ""),
            "link": a.get("link", ""),
        }
        if include_content:
            content = a.get("content", "")
            item["content"] = content[:2000] + "..." if len(content) > 2000 else content
        else:
            item["summary"] = a.get("summary", "")
        articles_output.append(item)

    _print_json({
        "success": True,
        "data": {
            "keyword": args.keyword,
            "total": len(articles_output),
            "output_file": os.path.abspath(output_file),
            "format": args.format,
            "articles": articles_output
        }
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
