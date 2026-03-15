#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多策略文章正文获取模块
======================

提供三种策略获取微信公众号文章全文：
1. requests + BeautifulSoup — 最快，复用 article_utils.get_article_content
2. DrissionPage 浏览器渲染 — 处理 JS 渲染内容
3. Camoufox (可选) — 最高质量，需安装 wechat-article-for-ai

auto 模式：先试 requests，失败则用 browser。
"""

import logging
import re
import socket
import time

logger = logging.getLogger("wechat-search")


class ArticleContentFetcher:
    """多策略文章正文获取器"""

    def __init__(self, strategy="auto", page=None):
        self.strategy = strategy
        self._page = page
        self._owns_page = False

    def fetch(self, url):
        """获取文章全文

        Returns:
            dict: {title, content_md, images, author, publish_time}
        """
        if not url:
            return self._empty_result()

        if self.strategy == "requests":
            return self._fetch_by_requests(url)
        elif self.strategy == "browser":
            return self._fetch_by_browser(url)
        elif self.strategy == "camoufox":
            return self._fetch_by_camoufox(url)
        else:
            # auto: 先 requests，失败则 browser
            result = self._fetch_by_requests(url)
            if result['content_md'] and len(result['content_md'].strip()) > 50:
                return result

            logger.info("requests 策略内容不足，切换到 browser 策略")
            return self._fetch_by_browser(url)

    def fetch_batch(self, articles, delay=3):
        """批量获取文章正文

        Args:
            articles: 文章列表（需含 link 字段）
            delay: 每篇之间的延迟（秒）

        Returns:
            list: 更新后的文章列表（新增 content 字段）
        """
        total = len(articles)
        for i, article in enumerate(articles):
            url = article.get('link', '')
            if not url or 'mp.weixin.qq.com' not in url:
                logger.warning("跳过非微信链接 (%d/%d): %s", i + 1, total, url[:60])
                article['content'] = ''
                continue

            logger.info("获取正文 (%d/%d): %s...", i + 1, total, article.get('title', '')[:40])
            try:
                result = self.fetch(url)
                article['content'] = result.get('content_md', '')
                if not article.get('account') and result.get('author'):
                    article['account'] = result['author']
            except Exception as e:
                logger.error("获取正文失败 (%d/%d): %s", i + 1, total, e)
                article['content'] = ''

            if i < total - 1:
                time.sleep(delay)

        return articles

    def _fetch_by_requests(self, url):
        """使用 requests + BeautifulSoup 获取正文"""
        try:
            from article_utils import get_article_content

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }

            content_md = get_article_content(url, headers)
            title, author, publish_time, images = self._extract_metadata_requests(url, headers)

            return {
                'title': title,
                'content_md': content_md or '',
                'images': images,
                'author': author,
                'publish_time': publish_time,
            }

        except Exception as e:
            logger.warning("requests 策略失败: %s", e)
            return self._empty_result()

    def _extract_metadata_requests(self, url, headers):
        """用 requests 提取文章元数据"""
        import requests
        import bs4

        title = ''
        author = ''
        publish_time = ''
        images = []

        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                return title, author, publish_time, images

            soup = bs4.BeautifulSoup(resp.text, 'lxml')

            title_el = soup.select_one('#activity-name, .rich_media_title, h1')
            if title_el:
                title = title_el.get_text(strip=True)

            author_el = soup.select_one('#js_name, .rich_media_meta_nickname')
            if author_el:
                author = author_el.get_text(strip=True)

            ts_match = re.search(r'var\s+create_time\s*=\s*"(\d+)"', resp.text)
            if ts_match:
                from datetime import datetime
                ts = int(ts_match.group(1))
                publish_time = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

            for img in soup.select('#js_content img[data-src], #js_content img[src]'):
                src = img.get('data-src') or img.get('src') or ''
                if src and 'mmbiz.qpic.cn' in src and 'data:image' not in src:
                    images.append(src)

        except Exception as e:
            logger.debug("提取元数据失败: %s", e)

        return title, author, publish_time, images

    def _fetch_by_browser(self, url):
        """使用 DrissionPage 浏览器渲染后提取 DOM"""
        try:
            page = self._get_browser_page()
            page.get(url)

            page.wait.doc_loaded(timeout=15)
            time.sleep(2)

            title = ''
            title_el = page.ele('css:#activity-name', timeout=3) or page.ele('css:h1', timeout=2)
            if title_el:
                title = title_el.text.strip()

            author = ''
            author_el = page.ele('css:#js_name', timeout=2)
            if author_el:
                author = author_el.text.strip()

            content_md = ''
            content_el = page.ele('css:#js_content', timeout=5)
            if content_el:
                inner_html = content_el.inner_html
                content_md = self._html_to_markdown(inner_html)

            images = []
            for img in page.eles('css:#js_content img'):
                src = img.attr('data-src') or img.attr('src') or ''
                if src and 'mmbiz.qpic.cn' in src and 'data:image' not in src:
                    images.append(src)

            publish_time = ''
            html_text = page.html or ''
            ts_match = re.search(r'var\s+create_time\s*=\s*"(\d+)"', html_text)
            if ts_match:
                from datetime import datetime
                ts = int(ts_match.group(1))
                publish_time = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

            return {
                'title': title,
                'content_md': content_md,
                'images': images,
                'author': author,
                'publish_time': publish_time,
            }

        except Exception as e:
            logger.error("browser 策略失败: %s", e)
            return self._empty_result()

    def _html_to_markdown(self, html):
        """将 HTML 转换为 Markdown"""
        try:
            import bs4
            from article_utils import md, _preprocess_lazy_images

            soup = bs4.BeautifulSoup(html, 'lxml')
            _preprocess_lazy_images(soup)
            return md(soup, keep_inline_images_in=["section", "span"])
        except Exception as e:
            logger.debug("HTML→Markdown 转换失败: %s", e)
            try:
                import bs4
                soup = bs4.BeautifulSoup(html, 'lxml')
                return soup.get_text(separator='\n', strip=True)
            except Exception:
                return html

    def _fetch_by_camoufox(self, url):
        """使用 Camoufox (wechat-article-for-ai) 获取正文"""
        try:
            from wechat_to_md.scraper import fetch_article_html
            from wechat_to_md.parser import parse_article
            from wechat_to_md.converter import convert_to_markdown

            html = fetch_article_html(url)
            parsed = parse_article(html)
            md_content = convert_to_markdown(parsed)

            return {
                'title': parsed.get('title', ''),
                'content_md': md_content,
                'images': parsed.get('images', []),
                'author': parsed.get('author', ''),
                'publish_time': parsed.get('publish_time', ''),
            }

        except ImportError:
            logger.warning("camoufox 策略不可用: 未安装 wechat-article-for-ai")
            return self._empty_result()
        except Exception as e:
            logger.error("camoufox 策略失败: %s", e)
            return self._empty_result()

    def _get_browser_page(self):
        """获取或创建浏览器实例"""
        if self._page is not None:
            return self._page

        from DrissionPage import ChromiumPage, ChromiumOptions

        co = ChromiumOptions()
        co.headless(True)
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-dev-shm-usage')
        co.set_argument('--disable-gpu')
        co.set_argument('--disable-blink-features=AutomationControlled')
        co.set_user_agent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
        co.set_local_port(port)

        self._page = ChromiumPage(addr_or_opts=co)
        self._owns_page = True
        return self._page

    def _empty_result(self):
        return {
            'title': '',
            'content_md': '',
            'images': [],
            'author': '',
            'publish_time': '',
        }

    def close(self):
        """关闭浏览器（仅当由本实例创建时）"""
        if self._owns_page and self._page is not None:
            try:
                self._page.quit()
            except Exception:
                pass
            self._page = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
