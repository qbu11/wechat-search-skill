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
    wechat-search scrape "人民日报" --pages 5 --days 30
    wechat-search batch "人民日报,新华社" --pages 3 --days 7
"""

import argparse
import io
import json
import os
import sys
import time
from datetime import datetime, timedelta

import requests


def _ensure_utf8_stdout():
    """强制 stdout/stderr 使用 UTF-8 编码，解决 Windows 终端乱码问题"""
    if sys.platform == 'win32':
        # 尝试设置 console code page
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except Exception:
            pass

    # 用 UTF-8 包装 stdout
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)


def _print_json(data):
    """安全地输出 JSON 到 stdout，确保 UTF-8 编码"""
    text = json.dumps(data, ensure_ascii=False, indent=2)
    try:
        sys.stdout.write(text + '\n')
        sys.stdout.flush()
    except (UnicodeEncodeError, OSError):
        # 最后兜底：用 ensure_ascii=True 输出纯 ASCII
        text_ascii = json.dumps(data, ensure_ascii=True, indent=2)
        sys.stdout.write(text_ascii + '\n')
        sys.stdout.flush()


# 延迟导入，避免在 --help 时触发 loguru 初始化
def _lazy_imports():
    from wechat_search.spider.log.utils import logger
    from wechat_search.spider.wechat.login import WeChatSpiderLogin
    from wechat_search.spider.wechat.scraper import WeChatScraper, BatchWeChatScraper
    from wechat_search.spider.wechat.paths import get_default_output_dir, get_wechat_cache_file
    return logger, WeChatSpiderLogin, WeChatScraper, BatchWeChatScraper, get_default_output_dir, get_wechat_cache_file


def cmd_status(args):
    """检查登录状态"""
    logger, WeChatSpiderLogin, *_ = _lazy_imports()
    login_mgr = WeChatSpiderLogin()
    status = login_mgr.check_login_status()

    _print_json({
        "success": status["isLoggedIn"],
        "data": status
    })
    return 0 if status["isLoggedIn"] else 1


def cmd_login(args):
    """执行扫码登录"""
    logger, WeChatSpiderLogin, _, _, _, get_wechat_cache_file = _lazy_imports()
    login_mgr = WeChatSpiderLogin()

    if login_mgr.load_cache() and login_mgr.validate_cache():
        status = login_mgr.check_login_status()
        _print_json({
            "success": True,
            "data": {"message": "已有有效登录缓存", **status}
        })
        return 0

    print("请在弹出的浏览器窗口中扫码登录...", file=sys.stderr)
    if login_mgr.login():
        _print_json({
            "success": True,
            "data": {"message": "登录成功", "cache_file": get_wechat_cache_file()}
        })
        return 0

    _print_json({"success": False, "error": "登录失败"})
    return 1


def _ensure_login():
    """确保已登录，未登录时自动引导扫码。返回 (login_mgr, ok)"""
    _, WeChatSpiderLogin, *_ = _lazy_imports()
    login_mgr = WeChatSpiderLogin()
    if login_mgr.load_cache() and login_mgr.validate_cache():
        return login_mgr, True

    print("检测到未登录或登录已过期，正在启动扫码登录...", file=sys.stderr)
    print("请在弹出的浏览器窗口中用微信扫码登录。", file=sys.stderr)
    if login_mgr.login():
        print("登录成功！继续执行...", file=sys.stderr)
        return login_mgr, True

    _print_json({"success": False, "error": "登录失败，请手动执行 wechat-search login"})
    return login_mgr, False


def cmd_search(args):
    """搜索公众号"""
    logger, _, WeChatScraper, *_ = _lazy_imports()
    login_mgr, ok = _ensure_login()
    if not ok:
        return 1

    token = login_mgr.get_token()
    headers = login_mgr.get_headers()
    scraper = WeChatScraper(token, headers)

    accounts = scraper.search_account(args.query)
    _print_json({
        "success": True,
        "data": {
            "query": args.query,
            "count": len(accounts),
            "accounts": accounts
        }
    })
    return 0


def cmd_scrape(args):
    """爬取单个公众号"""
    logger, _, WeChatScraper, *_ = _lazy_imports()
    login_mgr, ok = _ensure_login()
    if not ok:
        return 1

    token = login_mgr.get_token()
    headers = login_mgr.get_headers()
    scraper = WeChatScraper(token, headers)

    # 搜索公众号
    search_results = scraper.search_account(args.account)
    if not search_results:
        _print_json({"success": False, "error": f"未找到公众号: {args.account}"})
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
    include_content = not args.no_content
    if include_content and articles:
        logger.info(f"正在获取 {len(articles)} 篇文章正文...")
        for i, article in enumerate(articles):
            try:
                scraper.get_article_content_by_url(article)
            except Exception as e:
                logger.warning(f"获取第 {i+1} 篇正文失败: {e}")
            if i < len(articles) - 1:
                time.sleep(args.interval)

    # 保存 CSV
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
        if include_content:
            content = a.get("content", "")
            item["content"] = content[:2000] + "..." if len(content) > 2000 else content
        articles_output.append(item)

    _print_json({
        "success": True,
        "data": {
            "account": account_name,
            "fakeid": fakeid,
            "total": len(articles_output),
            "output_file": os.path.abspath(args.output),
            "articles": articles_output
        }
    })
    return 0


def cmd_batch(args):
    """批量爬取多个公众号"""
    logger, _, _, BatchWeChatScraper, get_default_output_dir, _ = _lazy_imports()
    login_mgr, ok = _ensure_login()
    if not ok:
        return 1

    token = login_mgr.get_token()
    headers = login_mgr.get_headers()

    # 解析公众号列表
    import re
    accounts = re.split(r'[,;，；、\s\t|]+', args.accounts.strip())
    accounts = [a.strip() for a in accounts if a.strip()]

    if not accounts:
        _print_json({"success": False, "error": "公众号列表为空"})
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
        "include_content": not args.no_content,
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
        if not args.no_content:
            content = a.get("content", "")
            item["content"] = content[:1000] + "..." if len(content) > 1000 else content
        articles_output.append(item)

    _print_json({
        "success": True,
        "data": {
            "accounts": accounts,
            "total": len(articles_output),
            "output_file": output_file,
            "articles": articles_output
        }
    })
    return 0


def cmd_doctor(args):
    """环境自检：检查 Python、DrissionPage、Chrome、端口、缓存、网络"""
    import platform
    import socket

    checks = {}

    # 1. Python 版本
    py_ver = platform.python_version()
    py_ok = tuple(int(x) for x in py_ver.split(".")[:2]) >= (3, 8)
    checks["python"] = {"version": py_ver, "ok": py_ok}
    print(f"{'[OK]' if py_ok else '[FAIL]'} Python {py_ver}" + ("" if py_ok else " (需要 >= 3.8)"), file=sys.stderr)

    # 2. DrissionPage
    try:
        import DrissionPage
        dp_ver = getattr(DrissionPage, "__version__", "unknown")
        checks["drissionpage"] = {"version": dp_ver, "ok": True}
        print(f"[OK] DrissionPage {dp_ver}", file=sys.stderr)
    except ImportError:
        checks["drissionpage"] = {"ok": False, "error": "未安装"}
        print("[FAIL] DrissionPage 未安装 (pip install DrissionPage)", file=sys.stderr)

    # 3. Chrome 路径
    from wechat_search.spider.wechat.login import _find_chrome_path
    chrome_path = _find_chrome_path()
    if chrome_path:
        checks["chrome"] = {"path": chrome_path, "ok": True}
        print(f"[OK] Chrome: {chrome_path}", file=sys.stderr)
    else:
        system = platform.system()
        hints = {
            "Windows": "winget install Google.Chrome",
            "Darwin": "brew install --cask google-chrome",
            "Linux": "sudo apt install google-chrome-stable",
        }
        hint = hints.get(system, "https://www.google.com/chrome/")
        checks["chrome"] = {"ok": False, "hint": hint}
        print(f"[FAIL] Chrome 未找到 — 安装: {hint}", file=sys.stderr)

    # 4. 端口 9222 状态
    port = 9222
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            result = s.connect_ex(("127.0.0.1", port))
            if result == 0:
                # 端口有服务在监听，尝试判断是否可接管
                port_status = "occupied_listening"
                port_msg = f"端口 {port} 已有服务监听（可能可接管）"
            else:
                port_status = "available"
                port_msg = f"端口 {port} 可用"
    except Exception:
        port_status = "available"
        port_msg = f"端口 {port} 可用"

    checks["port_9222"] = {"status": port_status, "ok": port_status in ("available", "occupied_listening")}
    print(f"[OK] {port_msg}" if checks["port_9222"]["ok"] else f"[WARN] {port_msg}", file=sys.stderr)

    # 5. 登录缓存状态
    from wechat_search.spider.wechat.paths import get_wechat_cache_file
    cache_file = get_wechat_cache_file()
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            cache_time = datetime.fromtimestamp(cache_data['timestamp'])
            hours_ago = (datetime.now() - cache_time).total_seconds() / 3600
            checks["cache"] = {"exists": True, "hours_ago": round(hours_ago, 1), "file": cache_file}
            print(f"[OK] 登录缓存存在 ({hours_ago:.1f} 小时前保存)", file=sys.stderr)
        except Exception as e:
            checks["cache"] = {"exists": True, "error": str(e), "file": cache_file}
            print(f"[WARN] 登录缓存文件损坏: {e}", file=sys.stderr)
    else:
        checks["cache"] = {"exists": False, "file": cache_file}
        print("[INFO] 无登录缓存（需要执行 wechat-search login）", file=sys.stderr)

    # 6. 网络连通性
    try:
        resp = requests.head("https://mp.weixin.qq.com", timeout=10)
        net_ok = resp.status_code < 500
        checks["network"] = {"ok": net_ok, "status_code": resp.status_code}
        print(f"[OK] mp.weixin.qq.com 可达 (HTTP {resp.status_code})", file=sys.stderr)
    except Exception as e:
        checks["network"] = {"ok": False, "error": str(e)}
        print(f"[FAIL] mp.weixin.qq.com 不可达: {e}", file=sys.stderr)

    # 汇总
    all_ok = all(c.get("ok", True) for c in checks.values())
    _print_json({"success": all_ok, "data": checks})
    return 0 if all_ok else 1


def cmd_install_skill(args):
    """安装 skill 文档到 Claude Code / OpenClaw"""
    from pathlib import Path
    import shutil

    # 优先从包内 skill_data/ 找（pip install 后的标准路径）
    skill_src = Path(__file__).resolve().parent / "skill_data" / "SKILL.md"
    if not skill_src.exists():
        # 开发模式：从项目根目录的 skill/ 找
        pkg_dir = Path(__file__).resolve().parent.parent.parent
        skill_src = pkg_dir / "skill" / "SKILL.md"
    if not skill_src.exists():
        skill_src = pkg_dir.parent / "skill" / "SKILL.md"

    if not skill_src.exists():
        _print_json({"success": False, "error": "找不到 SKILL.md，请确认包完整性"})
        return 1

    home = Path.home()
    targets = []

    claude_dir = home / ".claude" / "skills" / "wechat-search"
    claude_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(skill_src, claude_dir / "SKILL.md")
    targets.append(str(claude_dir / "SKILL.md"))

    ref_src = skill_src.parent / "references"
    if ref_src.exists():
        ref_dst = claude_dir / "references"
        if ref_dst.exists():
            shutil.rmtree(ref_dst)
        shutil.copytree(ref_src, ref_dst)

    openclaw_dir = home / ".openclaw" / "skills" / "wechat-search"
    try:
        openclaw_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(skill_src, openclaw_dir / "SKILL.md")
        targets.append(str(openclaw_dir / "SKILL.md"))
    except Exception:
        pass

    old_cmd = home / ".claude" / "commands" / "wechat-search.md"
    if old_cmd.exists():
        old_cmd.unlink()
        targets.append(f"removed: {old_cmd}")

    _print_json({
        "success": True,
        "data": {
            "message": "Skill 文档已安装",
            "installed_to": targets
        }
    })
    return 0


def cmd_export_login(args):
    """导出登录凭证为可分享字符串"""
    from wechat_search.spider.wechat.cache_codec import encode_cache_file
    from wechat_search.spider.wechat.paths import get_wechat_cache_file

    cache_file = get_wechat_cache_file()
    if not os.path.exists(cache_file):
        _print_json({"success": False, "error": "未找到登录缓存，请先执行 wechat-search login"})
        return 1

    try:
        encoded = encode_cache_file(cache_file)
        _print_json({
            "success": True,
            "data": {
                "message": "登录凭证已导出，请复制下方字符串到目标机器执行 import-login",
                "encoded": encoded
            }
        })
        return 0
    except Exception as e:
        _print_json({"success": False, "error": f"导出失败: {e}"})
        return 1


def cmd_import_login(args):
    """从编码字符串导入登录凭证"""
    from wechat_search.spider.wechat.cache_codec import decode_to_cache_file
    from wechat_search.spider.wechat.paths import get_wechat_cache_file

    encoded_str = args.token_string
    if not encoded_str:
        _print_json({"success": False, "error": "请提供编码字符串"})
        return 1

    cache_file = get_wechat_cache_file()
    try:
        data = decode_to_cache_file(encoded_str, cache_file)
        # 验证导入后是否可用
        _, WeChatSpiderLogin, *_ = _lazy_imports()
        login_mgr = WeChatSpiderLogin()
        if login_mgr.load_cache() and login_mgr.validate_cache():
            status = login_mgr.check_login_status()
            _print_json({
                "success": True,
                "data": {"message": "登录凭证导入成功且验证有效", **status}
            })
            return 0
        else:
            _print_json({
                "success": True,
                "data": {"message": "登录凭证已导入，但验证失败（可能已过期）", "cache_file": cache_file}
            })
            return 0
    except Exception as e:
        _print_json({"success": False, "error": f"导入失败: {e}"})
        return 1


def main():
    _ensure_utf8_stdout()

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
    sp_scrape.add_argument("--no-content", action="store_true", help="不获取文章正文（默认获取）")
    sp_scrape.add_argument("--interval", type=int, default=5, help="请求间隔秒数（默认5）")
    sp_scrape.add_argument("--output", "-o", default="result.csv", help="输出CSV文件路径（默认 result.csv）")

    # batch
    sp_batch = subparsers.add_parser("batch", help="批量爬取多个公众号")
    sp_batch.add_argument("accounts", help="公众号列表，逗号分隔")
    sp_batch.add_argument("--pages", type=int, default=3, help="每号最大页数（默认3）")
    sp_batch.add_argument("--days", type=int, default=30, help="时间范围（默认30天）")
    sp_batch.add_argument("--no-content", action="store_true", help="不获取正文（默认获取）")
    sp_batch.add_argument("--interval", type=int, default=10, help="请求间隔秒数（默认10）")
    sp_batch.add_argument("--output-dir", help="输出目录")

    # install-skill
    subparsers.add_parser("install-skill", help="安装 Skill 文档到 Claude Code / OpenClaw")

    # export-login
    subparsers.add_parser("export-login", help="导出登录凭证（用于复制到服务器）")

    # import-login
    sp_import = subparsers.add_parser("import-login", help="导入登录凭证（从其他机器复制）")
    sp_import.add_argument("token_string", help="export-login 导出的编码字符串")

    # doctor
    subparsers.add_parser("doctor", help="环境自检（Chrome、端口、缓存、网络）")

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
        "doctor": cmd_doctor,
        "install-skill": cmd_install_skill,
        "export-login": cmd_export_login,
        "import-login": cmd_import_login,
    }

    return cmd_map[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
