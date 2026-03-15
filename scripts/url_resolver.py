#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜狗链接转换模块
================

将搜狗微信搜索的跳转链接转换为 mp.weixin.qq.com 真实 URL。
搜狗搜索结果中的链接是搜狗中间页，需要通过浏览器跟随跳转获取真实地址。
"""

import logging
import random
import socket
import time

logger = logging.getLogger("wechat-search")


class SogouUrlResolver:
    """搜狗链接 → mp.weixin.qq.com 真实 URL 转换器"""

    def __init__(self, page=None):
        self._page = page
        self._owns_page = page is None

    @property
    def page(self):
        if self._page is None:
            self._page = self._create_page()
            self._owns_page = True
        return self._page

    def _create_page(self):
        """创建浏览器实例"""
        from DrissionPage import ChromiumPage, ChromiumOptions

        co = ChromiumOptions()
        co.headless(True)
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-dev-shm-usage')
        co.set_argument('--disable-gpu')
        co.set_argument('--disable-blink-features=AutomationControlled')

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
        co.set_local_port(port)

        return ChromiumPage(addr_or_opts=co)

    def resolve(self, sogou_url, timeout=15):
        """将搜狗跳转链接转换为 mp.weixin.qq.com 真实 URL

        Args:
            sogou_url: 搜狗搜索结果中的链接
            timeout: 等待跳转的超时时间（秒）

        Returns:
            str: mp.weixin.qq.com 真实 URL，失败返回原始 URL
        """
        if not sogou_url:
            return sogou_url

        if 'mp.weixin.qq.com' in sogou_url:
            return sogou_url

        try:
            self.page.get(sogou_url)

            start = time.time()
            while time.time() - start < timeout:
                current_url = self.page.url or ''
                if 'mp.weixin.qq.com' in current_url:
                    logger.debug("链接转换成功: %s... -> %s...", sogou_url[:50], current_url[:80])
                    return current_url
                time.sleep(0.5)

            final_url = self.page.url or sogou_url
            logger.warning("链接转换超时，当前 URL: %s...", final_url[:80])
            return final_url

        except Exception as e:
            logger.error("链接转换失败: %s", e)
            return sogou_url

    def batch_resolve(self, articles, delay_range=(1, 3)):
        """批量转换文章链接

        Args:
            articles: 文章列表（每个 dict 需含 sogou_link 字段）
            delay_range: 每次转换之间的随机延迟范围（秒）

        Returns:
            list: 更新后的文章列表（新增 link 字段为真实 URL）
        """
        total = len(articles)
        resolved = 0
        failed = 0

        for i, article in enumerate(articles):
            sogou_link = article.get('sogou_link', '')
            if not sogou_link:
                article['link'] = ''
                continue

            logger.info("转换链接 (%d/%d): %s...", i + 1, total, article.get('title', '')[:30])
            real_url = self.resolve(sogou_link)
            article['link'] = real_url

            if 'mp.weixin.qq.com' in real_url:
                resolved += 1
            else:
                failed += 1

            if i < total - 1:
                time.sleep(random.uniform(*delay_range))

        logger.info("链接转换完成: 成功 %d, 失败 %d, 共 %d", resolved, failed, total)
        return articles

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
