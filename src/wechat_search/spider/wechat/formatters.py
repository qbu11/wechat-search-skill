#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输出格式化模块
==============

将文章数据输出为 CSV 或 Markdown 格式。
CSV 复用现有 scraper.save_articles_to_csv 的逻辑。
Markdown 支持单文件合并输出或每篇文章一个文件。
"""

import csv
import os
from datetime import datetime

from wechat_search.spider.log.utils import logger


def save_articles_to_csv(articles, filename):
    """保存文章到 CSV 文件

    Args:
        articles: 文章列表，每个 dict 需含 title, account, date/publish_time, link, content 等字段
        filename: 输出文件路径

    Returns:
        bool: 是否成功
    """
    if not articles:
        logger.warning("没有文章可保存")
        return False

    try:
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['公众号', '标题', '发布时间', '链接', '摘要', '内容'])

            for article in articles:
                writer.writerow([
                    article.get('account', article.get('name', '')),
                    article.get('title', ''),
                    article.get('date', article.get('publish_time', '')),
                    article.get('link', article.get('sogou_link', '')),
                    article.get('summary', ''),
                    article.get('content', ''),
                ])

        logger.info(f"CSV 已保存: {filename} ({len(articles)} 篇)")
        return True

    except Exception as e:
        logger.error(f"保存 CSV 失败: {e}")
        return False


def save_articles_to_md(articles, filename):
    """保存文章到 Markdown 文件（合并为单个文件）

    Args:
        articles: 文章列表
        filename: 输出文件路径

    Returns:
        bool: 是否成功
    """
    if not articles:
        logger.warning("没有文章可保存")
        return False

    try:
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

        with open(filename, 'w', encoding='utf-8') as f:
            # 文件头
            f.write(f"# 微信公众号文章搜索结果\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"文章数量: {len(articles)}\n\n")
            f.write("---\n\n")

            for i, article in enumerate(articles):
                title = article.get('title', '无标题')
                account = article.get('account', article.get('name', '未知'))
                date = article.get('date', article.get('publish_time', ''))
                link = article.get('link', article.get('sogou_link', ''))
                summary = article.get('summary', '')
                content = article.get('content', '')

                f.write(f"## {i + 1}. {title}\n\n")
                f.write(f"- 公众号: {account}\n")
                if date:
                    f.write(f"- 发布时间: {date}\n")
                if link:
                    f.write(f"- 链接: [{link[:60]}...]({link})\n")
                f.write("\n")

                if summary and not content:
                    f.write(f"> {summary}\n\n")

                if content:
                    f.write(f"{content}\n\n")

                if i < len(articles) - 1:
                    f.write("---\n\n")

        logger.info(f"Markdown 已保存: {filename} ({len(articles)} 篇)")
        return True

    except Exception as e:
        logger.error(f"保存 Markdown 失败: {e}")
        return False
