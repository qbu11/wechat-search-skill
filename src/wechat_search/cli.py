#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号爬虫 CLI 入口
======================

无 GUI 依赖的命令行接口，供 Claude Code / OpenClaw 等工具调用。

子命令:
    status   - 检查登录状态
    login    - 扫码登录（需要 Chrome 浏览器）
    search   - 搜索公众号
    scrape   - 爬取单个公众号文章
    batch    - 批量爬取多个公众号

用法:
    wechat-search status
    wechat-search search "人民日报"
    wechat-search scrape "人民日报" --pages 5 --days 30 --content
    wechat-search batch "人民日报,新华社" --pages 3 --days 7
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta

from wechat_search.spider.log.utils import logger
from wechat_search.spider.wechat.login import WeChatSpiderLogin
from wechat_search.spider.wechat.scraper import WeChatScraper, BatchWeChatScraper
from wechat_search.spider.wechat.paths import get_default_output_dir, get_wechat_cache_file


def cmd_status(args):
    """检查登录状态"""
    login_mgr = WeChatSpiderLogin()
    status = login_mgr.check_login_status()

    result = {
        "success": status["isLoggedIn"],
        "data": status
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if status["isLoggedIn"] else 1


def cmd_login(args):
    """执行扫码登录"""
    login_mgr = WeChatSpiderLogin()

    if login_mgr.load_cache() and login_mgr.validate_cache():
        status = login_mgr.check_login_status()
        result = {
            "success": True,
            "data": {"message": "已有有效登录缓存", **status}
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print("请在弹出的浏览器窗口中扫码登录...", file=sys.stderr)
    if login_mgr.login():
        result = {
            "success": True,
            "data": {"message": "登录成功", "cache_file": get_wechat_cache_file()}
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    result = {"success": False, "error": "登录失败"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1


def cmd_search(args):
    """搜索公众号"""
    login_mgr = WeChatSpiderLogin()
    if not (login_mgr.load_cache() and login_mgr.validate_cache()):
        result = {"success": False, "error": "未登录或登录已过期，请先执行 login"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    token = login_mgr.get_token()
    headers = login_mgr.get_headers()
    scraper = WeChatScraper(token, headers)

    accounts = scraper.search_account(args.query)
    result = {
        "success": True,
        "data": {
            "query": args.query,
            "count": len(accounts),
            "accounts": accounts
        }
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_scrape(args):
    """爬取单个公众号"""
    login_mgr = WeChatSpiderLogin()
    if not (login_mgr.load_cache() and login_mgr.validate_cache()):
        result = {"success": False, "error": "未登录或登录已过期，请先执行 login"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    token = login_mgr.get_token()
    headers = login_mgr.get_headers()
    scraper = WeChatScraper(token, headers)

    # 搜索公众号
    search_results = scraper.search_account(args.account)
    if not search_results:
        result = {"success": False, "error": f"未找到公众号: {args.account}"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    account_info = search_results[0]
    fakeid = account_info["wpub_fakid"]
    account_name = account_info["wpub_name"]

    logger.info(f"匹配公众号: {account_name} (fakeid: {fakeid})")

    # 获取文章列表
    articles = scraper.get_account_articles(account_name, fakeid, max_pages=args.pages)

    # 日期过滤
    if args.days:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=args.days)
        articles = scraper.filter_articles_by_date(articles, start_date, end_date)

    # 获取正文
    if args.content and articles:
        logger.info(f"正在获取 {len(articles)} 篇文章正文...")
        for i, article in enumerate(articles):
            scraper.get_article_content_by_url(article)
            if i < len(articles) - 1:
                time.sleep(args.interval)

    # 输出
    if args.output:
        scraper.save_articles_to_csv(articles, args.output)
        logger.info(f"结果已保存到: {args.output}")

    # 构建简洁输出（正文太长时截断）
    articles_output = []
    for a in articles:
        item = {
            "title": a.get("title", ""),
            "publish_time": a.get("publish_time", ""),
            "link": a.get("link", ""),
        }
        if args.content:
            content = a.get("content", "")
            item["content"] = content[:2000] + "..." if len(content) > 2000 else content
        articles_output.append(item)

    result = {
        "success": True,
        "data": {
            "account": account_name,
            "fakeid": fakeid,
            "total": len(articles_output),
            "articles": articles_output
        }
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_batch(args):
    """批量爬取多个公众号"""
    login_mgr = WeChatSpiderLogin()
    if not (login_mgr.load_cache() and login_mgr.validate_cache()):
        result = {"success": False, "error": "未登录或登录已过期，请先执行 login"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    token = login_mgr.get_token()
    headers = login_mgr.get_headers()

    # 解析公众号列表
    import re
    accounts = re.split(r'[,;，；、\s\t|]+', args.accounts.strip())
    accounts = [a.strip() for a in accounts if a.strip()]

    if not accounts:
        result = {"success": False, "error": "公众号列表为空"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=args.days)

    output_dir = args.output_dir or get_default_output_dir()
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"wechat_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

    batch_scraper = BatchWeChatScraper()

    config = {
        "accounts": accounts,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "token": token,
        "headers": headers,
        "max_pages_per_account": args.pages,
        "request_interval": args.interval,
        "include_content": args.content,
        "output_file": output_file,
    }

    articles = batch_scraper.start_batch_scrape(config)

    articles_output = []
    for a in articles:
        item = {
            "account": a.get("name", ""),
            "title": a.get("title", ""),
            "publish_time": a.get("publish_time", ""),
            "link": a.get("link", ""),
        }
        if args.content:
            content = a.get("content", "")
            item["content"] = content[:1000] + "..." if len(content) > 1000 else content
        articles_output.append(item)

    result = {
        "success": True,
        "data": {
            "accounts": accounts,
            "total": len(articles_output),
            "output_file": output_file,
            "articles": articles_output
        }
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_install_skill(args):
    """安装 skill 文档到 Claude Code / OpenClaw"""
    from pathlib import Path
    import shutil

    # 找到 skill 源文件
    pkg_dir = Path(__file__).resolve().parent.parent.parent  # wechat-search-skill/
    # 尝试两个可能的位置：开发模式 vs 安装模式
    skill_src = pkg_dir / "skill" / "SKILL.md"
    if not skill_src.exists():
        # editable install: 从 src 同级的 skill 目录找
        skill_src = pkg_dir.parent / "skill" / "SKILL.md"
    if not skill_src.exists():
        # 最后尝试从包内 data 找
        skill_src = Path(__file__).resolve().parent / "skill_data" / "SKILL.md"

    if not skill_src.exists():
        print(json.dumps({"success": False, "error": f"找不到 SKILL.md，请确认包完整性"}, ensure_ascii=False, indent=2))
        return 1

    home = Path.home()
    targets = []

    # Claude Code: ~/.claude/skills/wechat-search/SKILL.md
    claude_dir = home / ".claude" / "skills" / "wechat-search"
    claude_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(skill_src, claude_dir / "SKILL.md")
    targets.append(str(claude_dir / "SKILL.md"))

    # references 目录
    ref_src = skill_src.parent / "references"
    if ref_src.exists():
        ref_dst = claude_dir / "references"
        if ref_dst.exists():
            shutil.rmtree(ref_dst)
        shutil.copytree(ref_src, ref_dst)

    # OpenClaw: ~/.openclaw/skills/wechat-search/SKILL.md
    openclaw_dir = home / ".openclaw" / "skills" / "wechat-search"
    try:
        openclaw_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(skill_src, openclaw_dir / "SKILL.md")
        targets.append(str(openclaw_dir / "SKILL.md"))
    except Exception:
        pass  # OpenClaw 可选

    # 同时删除旧的 commands 文件（如果存在）
    old_cmd = home / ".claude" / "commands" / "wechat-search.md"
    if old_cmd.exists():
        old_cmd.unlink()
        targets.append(f"removed: {old_cmd}")

    result = {
        "success": True,
        "data": {
            "message": "Skill 文档已安装",
            "installed_to": targets
        }
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="微信公众号爬虫 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # status
    subparsers.add_parser("status", help="检查登录状态")

    # login
    subparsers.add_parser("login", help="扫码登录微信公众平台")

    # search
    sp_search = subparsers.add_parser("search", help="搜索公众号")
    sp_search.add_argument("query", help="搜索关键词")

    # scrape
    sp_scrape = subparsers.add_parser("scrape", help="爬取单个公众号文章")
    sp_scrape.add_argument("account", help="公众号名称")
    sp_scrape.add_argument("--pages", type=int, default=5, help="最大页数（每页5篇，默认5）")
    sp_scrape.add_argument("--days", type=int, default=30, help="时间范围（最近N天，默认30）")
    sp_scrape.add_argument("--content", action="store_true", help="是否获取文章正文")
    sp_scrape.add_argument("--interval", type=int, default=5, help="请求间隔秒数（默认5）")
    sp_scrape.add_argument("--output", "-o", help="输出CSV文件路径")

    # batch
    sp_batch = subparsers.add_parser("batch", help="批量爬取多个公众号")
    sp_batch.add_argument("accounts", help="公众号列表，逗号分隔")
    sp_batch.add_argument("--pages", type=int, default=3, help="每号最大页数（默认3）")
    sp_batch.add_argument("--days", type=int, default=30, help="时间范围（默认30天）")
    sp_batch.add_argument("--content", action="store_true", help="是否获取正文")
    sp_batch.add_argument("--interval", type=int, default=10, help="请求间隔秒数（默认10）")
    sp_batch.add_argument("--output-dir", help="输出目录")

    # install-skill
    subparsers.add_parser("install-skill", help="安装 Skill 文档到 Claude Code / OpenClaw")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    cmd_map = {
        "status": cmd_status,
        "login": cmd_login,
        "search": cmd_search,
        "scrape": cmd_scrape,
        "batch": cmd_batch,
        "install-skill": cmd_install_skill,
    }

    return cmd_map[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
