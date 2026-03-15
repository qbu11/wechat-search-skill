#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章内容工具模块
================

从 HTML 提取微信公众号文章正文并转换为 Markdown。
包含懒加载图片处理、图片类型文章提取、多级 fallback 等。
"""

import html
import json
import logging
import re

import bs4
import requests
from markdownify import MarkdownConverter

logger = logging.getLogger("wechat-search")


class ImageBlockConverter(MarkdownConverter):
    """自定义 Markdown 转换器，重写图片处理逻辑"""

    def convert_img(self, el, text, parent_tags):
        alt = el.attrs.get('alt', None) or ''
        src = el.attrs.get('src', None) or ''
        if not src:
            src = el.attrs.get('data-src', None) or ''
        title = el.attrs.get('title', None) or ''
        title_part = ' "%s"' % title.replace('"', r'\"') if title else ''
        if ('_inline' in parent_tags
                and el.parent.name not in self.options['keep_inline_images_in']):
            return alt

        return '\n![%s](%s%s)\n' % (alt, src, title_part)


def md(soup, **options):
    """将 BeautifulSoup 对象转换为 Markdown 文本"""
    return ImageBlockConverter(**options).convert_soup(soup)


def _preprocess_lazy_images(soup):
    """预处理微信文章中的懒加载图片"""
    for img in soup.find_all('img'):
        src = img.get('src', '')
        data_src = img.get('data-src', '')

        if data_src and (not src or 'data:image/svg' in src or 'pic_blank' in src):
            img['src'] = data_src
            logger.debug("替换懒加载图片: %s...", data_src[:50])


def _decode_html_entities(text):
    """解码 HTML 实体和 JavaScript 转义字符"""
    if not text:
        return text

    text = html.unescape(text)

    def replace_hex_escape(match):
        hex_val = match.group(1)
        try:
            return chr(int(hex_val, 16))
        except (ValueError, OverflowError):
            return match.group(0)

    text = re.sub(r'\\x([0-9a-fA-F]{2})', replace_hex_escape, text)
    text = html.unescape(text)

    return text


def _extract_fallback_content(soup, content_ele):
    """备用内容提取方法"""
    content_parts = []

    title_ele = soup.select_one('.rich_media_title, #activity-name, h1')
    if title_ele and title_ele.get_text(strip=True):
        content_parts.append(f"# {title_ele.get_text(strip=True)}\n")

    if content_ele:
        text_content = content_ele.get_text(separator='\n', strip=True)
        if text_content:
            content_parts.append(f"\n{text_content}\n")

    if content_ele:
        images = content_ele.find_all('img')
        if images:
            content_parts.append("\n## 图片\n")
            for i, img in enumerate(images, 1):
                src = img.get('src') or img.get('data-src') or ''
                alt = img.get('alt') or f'图片{i}'
                if src and 'mmbiz.qpic.cn' in src and 'data:image' not in src:
                    content_parts.append(f"\n![{alt}]({src})\n")

    return ''.join(content_parts) if content_parts else None


def _extract_image_article_content(soup):
    """提取图片类型文章的内容"""
    content_parts = []
    seen_urls = set()

    def add_image(src, alt=''):
        nonlocal seen_urls
        if not src:
            return
        src = _decode_html_entities(src)
        base_url = src.split('?')[0] if '?' in src else src
        if base_url in seen_urls:
            return
        if 'mmbiz.qpic.cn' not in src:
            return
        if 'pic_blank' in src or 'data:image' in src:
            return
        seen_urls.add(base_url)
        alt = alt or f'图片{len(seen_urls)}'
        content_parts.append(f"\n![{alt}]({src})\n")

    # 1. 提取标题
    title_selectors = ['.rich_media_title', '#activity-name', '#js_image_content h1', 'h1']
    for selector in title_selectors:
        title_ele = soup.select_one(selector)
        if title_ele and title_ele.get_text(strip=True):
            title_text = _decode_html_entities(title_ele.get_text(strip=True))
            content_parts.append(f"# {title_text}\n")
            break

    # 2. 提取描述/摘要
    desc_selectors = ['#js_image_desc', '.share_notice', 'meta[name="description"]']
    for selector in desc_selectors:
        if selector.startswith('meta'):
            desc_ele = soup.select_one(selector)
            if desc_ele and desc_ele.get('content'):
                desc_text = _decode_html_entities(desc_ele.get('content'))
                content_parts.append(f"\n{desc_text}\n")
                break
        else:
            desc_ele = soup.select_one(selector)
            if desc_ele and desc_ele.get_text(strip=True):
                desc_text = _decode_html_entities(desc_ele.get_text(strip=True))
                content_parts.append(f"\n{desc_text}\n")
                break

    # 3. 从 JavaScript 变量中提取图片
    js_images_found = False
    for script in soup.find_all('script'):
        script_text = script.string or ''
        if 'picture_page_info_list' in script_text:
            match = re.search(r'var\s+picture_page_info_list\s*=\s*(\[[\s\S]*?\]);', script_text)
            if match:
                try:
                    json_str = match.group(1)
                    json_str = _decode_html_entities(json_str)
                    pic_list = json.loads(json_str)

                    if pic_list:
                        content_parts.append("\n## 图片内容\n")
                        for pic_info in pic_list:
                            cdn_url = pic_info.get('cdn_url', '')
                            if cdn_url:
                                cdn_url = _decode_html_entities(cdn_url)
                                add_image(cdn_url)
                        js_images_found = True
                except (json.JSONDecodeError, Exception) as e:
                    logger.debug("解析 picture_page_info_list 失败: %s", e)

    # 4. 如果JS方法没找到图片，尝试从 swiper_item 容器提取
    if not js_images_found or len(seen_urls) == 0:
        swiper_items = soup.select('.swiper_item[data-src], div[data-src*="mmbiz.qpic.cn"]')
        if swiper_items:
            if not js_images_found:
                content_parts.append("\n## 图片内容\n")
            for item in swiper_items:
                src = item.get('data-src', '')
                if src:
                    add_image(src)

        swiper_images = soup.select('.swiper_item_img img')
        if swiper_images:
            if not js_images_found and len(seen_urls) == 0:
                content_parts.append("\n## 图片内容\n")
            for img in swiper_images:
                src = img.get('src') or img.get('data-src') or ''
                alt = img.get('alt') or ''
                add_image(src, alt)

        if len(seen_urls) == 0:
            other_selectors = [
                '#js_image_content img',
                '.image_content img',
                '.wx_img_swiper img',
                '.img_swiper_wrp img'
            ]
            for selector in other_selectors:
                images = soup.select(selector)
                if images:
                    if len(seen_urls) == 0:
                        content_parts.append("\n## 图片内容\n")
                    for img in images:
                        src = img.get('src') or img.get('data-src') or ''
                        alt = img.get('alt') or ''
                        add_image(src, alt)
                    if len(seen_urls) > 0:
                        break

    # 5. 通用兜底方法
    if len(seen_urls) == 0:
        logger.info("使用通用兜底方法提取所有微信图片")
        content_parts.append("\n## 图片内容\n")

        all_images = soup.find_all('img')
        for img in all_images:
            src = img.get('src') or img.get('data-src') or img.get('data-original') or ''
            alt = img.get('alt') or ''
            if src:
                add_image(src, alt)

        elements_with_data_src = soup.find_all(attrs={'data-src': True})
        for ele in elements_with_data_src:
            src = ele.get('data-src', '')
            if src:
                add_image(src)

        elements_with_style = soup.find_all(style=True)
        for ele in elements_with_style:
            style = ele.get('style', '')
            bg_matches = re.findall(r'url\(["\']?(https?://mmbiz\.qpic\.cn[^"\')\s]+)["\']?\)', style)
            for bg_url in bg_matches:
                add_image(bg_url)

    # 6. 提取话题标签
    topic_links = soup.select('.wx_topic_link')
    if topic_links:
        topics = []
        for link in topic_links:
            topic_text = link.get_text(strip=True)
            if topic_text:
                topic_text = _decode_html_entities(topic_text)
                topic_text = re.sub(r'<[^>]+>', '', topic_text)
                if topic_text and not topic_text.startswith('<'):
                    topics.append(topic_text)
        if topics:
            content_parts.append(f"\n**话题标签**: {' '.join(topics)}\n")

    return ''.join(content_parts) if content_parts else None


def _extract_all_text_content(soup):
    """最后的兜底方法：提取页面所有可见文本"""
    content_parts = []

    title_ele = soup.select_one('.rich_media_title, #activity-name, h1')
    if title_ele and title_ele.get_text(strip=True):
        content_parts.append(f"# {title_ele.get_text(strip=True)}\n")

    main_content_selectors = [
        '.rich_media_content',
        '#js_content',
        '.rich_media_area_primary',
        'article',
        '.article-content'
    ]

    for selector in main_content_selectors:
        ele = soup.select_one(selector)
        if ele:
            text = ele.get_text(separator='\n', strip=True)
            if text and len(text) > 20:
                content_parts.append(f"\n{text}\n")
                break

    images = soup.select('img[data-src], img[src*="mmbiz.qpic.cn"]')
    if images:
        content_parts.append("\n## 图片\n")
        for i, img in enumerate(images[:20], 1):
            src = img.get('data-src') or img.get('src') or ''
            if src and 'mmbiz.qpic.cn' in src and 'data:image' not in src:
                alt = img.get('alt') or f'图片{i}'
                content_parts.append(f"\n![{alt}]({src})\n")

    return ''.join(content_parts) if content_parts else ""


def get_article_content(url, headers, max_retries=3, retry_delay=2):
    """获取文章正文内容并转换为 Markdown"""
    import time

    CONTENT_SELECTORS = [
        ".rich_media_content",
        "#js_content",
        "#js_image_content",
        ".image_content",
        "#js_image_desc",
        ".share_notice",
        ".swiper_item_img",
        "#img_swiper_content",
        ".share_media_swiper_content",
        ".img_swiper_area",
        "#js_video_content",
        ".video_content",
        ".rich_media_video",
        ".rich_media_area_primary",
        ".rich_media_area_primary_inner",
        "#js_article_content",
        "#js_content_container",
        "#page-content",
        ".rich_media_inner",
        ".rich_media_wrp",
        "article",
        ".article",
        "#article",
    ]

    MIN_CONTENT_LENGTH = 10

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                logger.warning("请求失败，状态码: %d，尝试 %d/%d", response.status_code, attempt + 1, max_retries)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return f"请求失败，状态码: {response.status_code}"

            soup = bs4.BeautifulSoup(response.text, 'lxml')

            _preprocess_lazy_images(soup)

            body_classes = soup.body.get('class', []) if soup.body else []
            is_image_article = 'page_share_img' in body_classes

            has_swiper = bool(soup.select('.swiper_item, .swiper_item_img, .share_media_swiper'))

            if is_image_article or has_swiper:
                logger.info("检测到图片类型文章（page_share_img=%s, swiper=%s），使用特殊处理", is_image_article, has_swiper)
                content = _extract_image_article_content(soup)
                if content and len(content.strip()) >= MIN_CONTENT_LENGTH:
                    return content

            content_ele = None
            for selector in CONTENT_SELECTORS:
                content_ele = soup.select(selector)
                if content_ele:
                    logger.debug("使用选择器 '%s' 匹配到内容元素", selector)
                    break

            content = ""
            if content_ele:
                content = md(content_ele[0], keep_inline_images_in=["section", "span"])

                content_stripped = content.strip()
                if len(content_stripped) < MIN_CONTENT_LENGTH:
                    logger.warning("Markdown转换后内容过短(%d字符)，尝试备用提取方法", len(content_stripped))
                    fallback_content = _extract_fallback_content(soup, content_ele[0])
                    if fallback_content and len(fallback_content.strip()) > len(content_stripped):
                        content = fallback_content
                        logger.info("使用备用提取方法成功获取内容")

            if content and len(content.strip()) >= MIN_CONTENT_LENGTH:
                logger.info("成功获取文章内容，长度: %d 字符", len(content.strip()))
                return content

            if attempt < max_retries - 1:
                logger.warning("内容为空或过短，可能页面未完全加载，%s秒后重试 (%d/%d)", retry_delay, attempt + 1, max_retries)
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 10)
            else:
                logger.warning("重试%d次后仍无法获取有效内容，URL: %s", max_retries, url)
                if not content:
                    content = _extract_all_text_content(soup)
                return content

        except requests.exceptions.Timeout:
            logger.warning("请求超时，尝试 %d/%d", attempt + 1, max_retries)
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return "获取文章内容失败: 请求超时"
        except requests.exceptions.RequestException as e:
            logger.warning("请求异常: %s，尝试 %d/%d", e, attempt + 1, max_retries)
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return f"获取文章内容失败: {str(e)}"
        except Exception as e:
            logger.error("获取文章内容时发生异常: %s", e)
            return f"获取文章内容失败: {str(e)}"

    return ""
