#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜狗微信搜索模块
================

通过搜狗微信搜索 (weixin.sogou.com) 按关键词搜索微信公众号文章。
使用 DrissionPage 操控 Chrome 绕过反爬，无需微信登录态。
"""

import logging
import random
import re
import socket
import time
from datetime import datetime, timedelta

logger = logging.getLogger("wechat-search")

# 随机 User-Agent 池
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


class SogouWeChatSearch:
    """搜狗微信关键词搜索

    使用 DrissionPage 操控 Chrome 访问搜狗微信搜索，
    提取文章列表并返回结构化数据。
    """

    def __init__(self, headless=True, page=None):
        self.headless = headless
        self._page = page
        self._owns_page = page is None

    @property
    def page(self):
        if self._page is None:
            self._page = self._create_page()
            self._owns_page = True
        return self._page

    def _create_page(self):
        """创建 DrissionPage 浏览器实例"""
        from DrissionPage import ChromiumPage, ChromiumOptions

        co = ChromiumOptions()
        if self.headless:
            co.headless(True)

        co.set_user_agent(random.choice(_USER_AGENTS))
        co.set_argument('--disable-blink-features=AutomationControlled')
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-dev-shm-usage')
        co.set_argument('--disable-gpu')

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
        co.set_local_port(port)

        return ChromiumPage(addr_or_opts=co)

    def search(self, keyword, max_pages=3, days=None):
        """搜索关键词，返回文章列表

        Args:
            keyword: 搜索关键词
            max_pages: 最大搜索页数（默认 3，每页约 10 篇）
            days: 时间范围（天数），None 表示不限

        Returns:
            list[dict]: 文章列表
        """
        all_articles = []

        try:
            search_url = f"https://weixin.sogou.com/weixin?type=2&query={keyword}"
            logger.info("搜狗搜索: %s (最多 %d 页)", keyword, max_pages)

            self.page.get(search_url)
            time.sleep(random.uniform(2, 4))

            if self._check_captcha():
                logger.warning("检测到搜狗验证码页面，请手动完成验证后重试")
                if not self.headless:
                    logger.info("等待用户手动完成验证码（最多 60 秒）...")
                    self._wait_for_captcha_resolve(timeout=60)
                else:
                    return []

            for page_num in range(max_pages):
                logger.info("正在解析第 %d/%d 页...", page_num + 1, max_pages)

                articles = self._extract_results()
                all_articles.extend(articles)
                logger.info("第 %d 页提取到 %d 篇文章", page_num + 1, len(articles))

                if page_num < max_pages - 1:
                    if not self._next_page():
                        logger.info("没有更多页面了")
                        break
                    time.sleep(random.uniform(2, 5))

                    if self._check_captcha():
                        logger.warning("翻页后遇到验证码")
                        if not self.headless:
                            self._wait_for_captcha_resolve(timeout=60)
                        else:
                            break

        except Exception as e:
            logger.error("搜狗搜索出错: %s", e)

        if days is not None:
            all_articles = self._filter_by_days(all_articles, days)

        logger.info("搜索完成，共获取 %d 篇文章", len(all_articles))
        return all_articles

    def _extract_results(self):
        """从当前页面提取搜索结果"""
        articles = []

        try:
            items = self.page.eles('css:.news-list > li') or self.page.eles('css:ul.news-list li')
            if not items:
                items = self.page.eles('css:.txt-box')

            if not items:
                logger.warning("未找到搜索结果元素")
                return articles

            for item in items:
                try:
                    article = self._parse_single_result(item)
                    if article and article.get('title'):
                        articles.append(article)
                except Exception as e:
                    logger.debug("解析单条结果失败: %s", e)
                    continue

        except Exception as e:
            logger.error("提取搜索结果失败: %s", e)

        return articles

    def _parse_single_result(self, item):
        """解析单条搜索结果"""
        article = {
            'title': '',
            'account': '',
            'timestamp': None,
            'date': '',
            'sogou_link': '',
            'summary': '',
        }

        # 标题和链接
        title_el = item.ele('css:h3 a', timeout=1) or item.ele('css:.txt-box h3 a', timeout=1)
        if title_el:
            article['title'] = title_el.text.strip()
            href = title_el.attr('href')
            if href:
                if href.startswith('//'):
                    href = 'https:' + href
                elif href.startswith('/'):
                    href = 'https://weixin.sogou.com' + href
                article['sogou_link'] = href

        # 公众号名称
        account_el = (
            item.ele('css:.s-p .all-time-y2', timeout=1)
            or item.ele('css:.account', timeout=1)
            or item.ele('css:.s-p a', timeout=1)
        )
        if account_el:
            article['account'] = account_el.text.strip()

        # 摘要
        summary_el = item.ele('css:.txt-info', timeout=1) or item.ele('css:p.txt-info', timeout=1)
        if summary_el:
            article['summary'] = summary_el.text.strip()

        # 时间戳
        sp_el = item.ele('css:.s-p', timeout=1)
        if sp_el:
            sp_html = sp_el.attr('innerHTML') or sp_el.inner_html or ''
            ts_match = re.search(r"timeConvert\('(\d+)'\)", sp_html)
            if ts_match:
                article['timestamp'] = int(ts_match.group(1))
                article['date'] = datetime.fromtimestamp(article['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            else:
                s2_el = item.ele('css:.s2', timeout=1)
                if s2_el:
                    article['date'] = s2_el.text.strip()

        return article

    def _next_page(self):
        """翻到下一页"""
        try:
            next_btn = (
                self.page.ele('css:#sogou_next', timeout=3)
                or self.page.ele('css:a#sogou_next', timeout=2)
                or self.page.ele('text:下一页', timeout=2)
            )
            if next_btn:
                next_btn.click()
                time.sleep(random.uniform(1, 3))
                return True
        except Exception as e:
            logger.debug("翻页失败: %s", e)

        return False

    def _check_captcha(self):
        """检测是否遇到验证码页面"""
        try:
            url = self.page.url or ''
            if '/antispider/' in url:
                return True

            html_text = self.page.html or ''
            captcha_indicators = ['antispider', '请输入验证码', '安全验证', '请完成下方验证']
            return any(indicator in html_text for indicator in captcha_indicators)
        except Exception:
            return False

    def _wait_for_captcha_resolve(self, timeout=60):
        """等待用户手动完成验证码"""
        start = time.time()
        while time.time() - start < timeout:
            if not self._check_captcha():
                logger.info("验证码已通过")
                return True
            time.sleep(2)
        logger.warning("等待验证码超时")
        return False

    def _filter_by_days(self, articles, days):
        """按时间范围过滤文章"""
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_ts = cutoff.timestamp()

        filtered = []
        for article in articles:
            ts = article.get('timestamp')
            if ts is None:
                filtered.append(article)
            elif ts >= cutoff_ts:
                filtered.append(article)

        logger.info("时间过滤 (%d 天内): %d -> %d 篇", days, len(articles), len(filtered))
        return filtered

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
