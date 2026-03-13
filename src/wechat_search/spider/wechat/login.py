#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众平台登录模块 (agent-browser 版本)
==========================================

实现微信公众平台的自动化登录流程，获取爬虫运行所需的认证信息。
使用 Vercel agent-browser CLI 替代 Selenium/DrissionPage。

特点:
    - 通过 subprocess 调用 agent-browser CLI
    - 支持 CDP 连接现有 Chrome (--cdp 9222)
    - 可与 Chrome DevTools MCP 共享浏览器
    - 支持 headed 模式显示浏览器窗口

工作流程:
    1. 检查 agent-browser 是否已安装
    2. 打开微信公众平台登录页面
    3. 等待用户扫码登录
    4. 从 URL 提取 token
    5. 获取 cookies 并缓存

缓存策略:
    - 登录信息保存在用户数据目录
    - 默认缓存有效期 4 天
    - 支持手动清除缓存

依赖:
    - agent-browser CLI (npm install -g agent-browser)
    - requests: HTTP 请求
"""

import json
import os
import platform
import random
import re
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

import requests

from wechat_search.spider.log.utils import logger
from wechat_search.spider.wechat.paths import get_wechat_cache_file

# 缓存文件路径
CACHE_FILE = get_wechat_cache_file()

# 缓存有效期：4 天
CACHE_EXPIRE_HOURS = 24 * 4

# Chrome 调试端口
CHROME_DEBUG_PORT = 9222

# agent-browser 命令
AGENT_BROWSER_CMD = "agent-browser"


def check_agent_browser_installed() -> bool:
    """检查 agent-browser 是否已安装"""
    # Windows 上尝试 .cmd，其他系统直接用命令名
    if platform.system() == "Windows":
        return shutil.which(AGENT_BROWSER_CMD + ".cmd") is not None
    return shutil.which(AGENT_BROWSER_CMD) is not None


def get_agent_browser_cmd() -> str:
    """获取 agent-browser 实际命令（包含 .cmd 扩展名）"""
    if platform.system() == "Windows":
        cmd = AGENT_BROWSER_CMD + ".cmd"
        if shutil.which(cmd):
            return cmd
    return AGENT_BROWSER_CMD


def run_agent_browser(args: List[str], capture_output: bool = True, timeout: int = 300) -> Tuple[int, str, str]:
    """
    运行 agent-browser 命令

    Args:
        args: 命令参数列表
        capture_output: 是否捕获输出
        timeout: 超时时间（秒）

    Returns:
        (return_code, stdout, stderr)
    """
    cmd = [get_agent_browser_cmd()] + args
    logger.debug(f"执行命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode, result.stdout or '', result.stderr or ''
    except subprocess.TimeoutExpired:
        logger.error(f"命令超时: {' '.join(cmd)}")
        return -1, '', 'Command timed out'
    except FileNotFoundError:
        logger.error("agent-browser 未安装，请运行: npm install -g agent-browser")
        return -1, '', 'agent-browser not found'
    except Exception as e:
        logger.error(f"执行命令失败: {e}")
        return -1, '', str(e)


class WeChatSpiderLogin:
    """
    微信公众平台登录管理器 (agent-browser 版本)

    使用 agent-browser CLI 进行浏览器自动化操作。

    Attributes:
        token: 访问令牌
        cookies: 会话 cookie 字典
        cache_file: 缓存文件路径
        debug_port: Chrome 调试端口
        headed: 是否显示浏览器窗口
    """

    def __init__(self, cache_file: str = CACHE_FILE, debug_port: int = CHROME_DEBUG_PORT, headed: bool = True):
        """
        初始化登录管理器

        Args:
            cache_file: 缓存文件路径
            debug_port: Chrome 调试端口
            headed: 是否显示浏览器窗口（False 为 headless 模式）
        """
        self.token: Optional[str] = None
        self.cookies: Optional[Dict[str, str]] = None
        self.cache_file = cache_file
        self.debug_port = debug_port
        self.headed = headed
        self._session_active = False

    def save_cache(self) -> bool:
        """保存登录信息到缓存文件"""
        if self.token and self.cookies:
            cache_data = {
                'token': self.token,
                'cookies': self.cookies,
                'timestamp': datetime.now().timestamp()
            }
            try:
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                logger.success(f"登录信息已保存到缓存文件 {self.cache_file}")
                return True
            except Exception as e:
                logger.error(f"保存缓存失败: {e}")
                return False
        return False

    def load_cache(self) -> bool:
        """从缓存文件加载登录信息"""
        if not os.path.exists(self.cache_file):
            logger.info("缓存文件不存在，需要重新登录")
            return False

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            cache_time = datetime.fromtimestamp(cache_data['timestamp'])
            current_time = datetime.now()
            hours_diff = (current_time - cache_time).total_seconds() / 3600

            if hours_diff > CACHE_EXPIRE_HOURS:
                logger.info(f"缓存已过期（{hours_diff:.1f}小时前），需要重新登录")
                return False

            self.token = cache_data['token']
            self.cookies = cache_data['cookies']
            logger.info(f"从缓存加载登录信息（{hours_diff:.1f}小时前保存）")
            return True

        except Exception as e:
            logger.error(f"读取缓存失败: {e}，需要重新登录")
            return False

    def validate_cache(self) -> bool:
        """验证缓存的登录信息是否仍然有效"""
        if not self.token or not self.cookies:
            return False

        try:
            headers = {
                "HOST": "mp.weixin.qq.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            test_url = 'https://mp.weixin.qq.com/cgi-bin/searchbiz'
            test_params = {
                'action': 'search_biz',
                'token': self.token,
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': '1',
                'random': random.random(),
                'query': 'test',
                'begin': '0',
                'count': '1',
            }

            response = requests.get(
                test_url,
                cookies=self.cookies,
                headers=headers,
                params=test_params,
                timeout=10
            )
            response.raise_for_status()

            result = response.json()

            if 'base_resp' in result:
                if result['base_resp']['ret'] == 0:
                    logger.success("缓存的登录信息验证有效")
                    return True
                elif result['base_resp']['ret'] in (-6, 200013):
                    logger.warning("缓存的token已失效")
                    return False
                else:
                    logger.warning(f"验证失败: {result['base_resp'].get('err_msg', '未知错误')}")
                    return False
            else:
                logger.warning("验证响应格式异常")
                return False

        except Exception as e:
            logger.error(f"验证缓存时发生错误: {e}")
            return False

    def clear_cache(self) -> bool:
        """清除本地缓存文件"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                logger.info("缓存已清除")
            return True
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
            return False

    def _build_base_args(self) -> List[str]:
        """构建基础命令参数"""
        args = []
        if self.headed:
            args.append("--headed")
        # 连接到现有 Chrome 或使用新实例
        args.extend(["--cdp", str(self.debug_port)])
        return args

    def _open_page(self, url: str) -> bool:
        """打开页面"""
        args = self._build_base_args() + ["open", url]
        code, stdout, stderr = run_agent_browser(args, timeout=60)
        if code == 0:
            logger.success(f"页面打开成功: {url}")
            return True
        else:
            logger.error(f"页面打开失败: {stderr}")
            return False

    def _get_current_url(self) -> Optional[str]:
        """获取当前页面 URL"""
        args = self._build_base_args() + ["get", "url"]
        code, stdout, stderr = run_agent_browser(args, timeout=30)
        if code == 0:
            return stdout.strip()
        return None

    def _get_cookies(self) -> Optional[Dict[str, str]]:
        """获取当前页面 cookies"""
        args = self._build_base_args() + ["cookies", "get"]
        code, stdout, stderr = run_agent_browser(args, timeout=30)
        if code == 0:
            try:
                # agent-browser 返回 JSON 格式的 cookies
                cookies_list = json.loads(stdout)
                return {c['name']: c['value'] for c in cookies_list if 'name' in c and 'value' in c}
            except json.JSONDecodeError:
                logger.warning("解析 cookies 失败")
        return None

    def _take_snapshot(self) -> Optional[str]:
        """获取页面快照"""
        args = self._build_base_args() + ["snapshot"]
        code, stdout, stderr = run_agent_browser(args, timeout=30)
        if code == 0:
            return stdout
        return None

    def _close_browser(self) -> bool:
        """关闭浏览器"""
        args = self._build_base_args() + ["close"]
        code, stdout, stderr = run_agent_browser(args, timeout=30)
        return code == 0

    def login(self) -> bool:
        """
        执行登录流程

        Returns:
            bool: 登录成功返回 True
        """
        logger.info("\n" + "="*60)
        logger.info("开始登录微信公众号平台...")
        logger.info("="*60)

        # 检查 agent-browser 是否安装
        if not check_agent_browser_installed():
            logger.error("agent-browser 未安装")
            logger.info("请运行: npm install -g agent-browser")
            logger.info("然后运行: agent-browser install")
            return False

        # 检查缓存
        if self.load_cache() and self.validate_cache():
            logger.success("使用有效的缓存登录信息")
            return True
        else:
            logger.info("缓存无效或不存在，需要重新扫码登录")
            self.clear_cache()

        try:
            # 打开登录页面
            logger.info("正在打开微信公众平台...")
            if not self._open_page('https://mp.weixin.qq.com/'):
                return False

            logger.info("请在浏览器窗口中扫码登录...")
            logger.info("等待登录完成（最长等待5分钟）...")

            # 等待登录成功（URL 包含 token）
            start_time = time.time()
            timeout = 300  # 5 分钟
            current_url = None

            while time.time() - start_time < timeout:
                current_url = self._get_current_url()
                if current_url and 'token=' in current_url:
                    logger.success("检测到登录成功！正在获取登录信息...")
                    break
                time.sleep(2)
            else:
                logger.error("登录超时（5分钟内未检测到登录成功）")
                return False

            # 提取 token
            token_match = re.search(r'token=(\d+)', current_url)
            if token_match:
                self.token = token_match.group(1)
                logger.success(f"Token获取成功: {self.token}")
            else:
                logger.error("无法从URL中提取token")
                return False

            # 获取 cookies
            self.cookies = self._get_cookies()
            if self.cookies:
                logger.success(f"Cookies获取成功，共{len(self.cookies)}个")
            else:
                logger.error("获取 Cookies 失败")
                return False

            # 保存缓存
            if self.save_cache():
                logger.success("登录信息已保存到缓存")

            logger.success("登录完成！")
            return True

        except Exception as e:
            logger.error(f"登录过程中出现错误: {e}")
            return False

    def check_login_status(self) -> Dict[str, Any]:
        """获取当前登录状态的详细信息"""
        if self.load_cache() and self.validate_cache():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                cache_time = datetime.fromtimestamp(cache_data['timestamp'])
                expire_time = cache_time + timedelta(hours=CACHE_EXPIRE_HOURS)
                hours_since_login = (datetime.now() - cache_time).total_seconds() / 3600
                hours_until_expire = (expire_time - datetime.now()).total_seconds() / 3600

                return {
                    'isLoggedIn': True,
                    'loginTime': cache_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'expireTime': expire_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'hoursSinceLogin': round(hours_since_login, 1),
                    'hoursUntilExpire': round(hours_until_expire, 1),
                    'token': self.token,
                    'message': f'已登录 {round(hours_since_login, 1)} 小时'
                }
            except Exception:
                pass

        return {
            'isLoggedIn': False,
            'message': '未登录或登录已过期'
        }

    def logout(self) -> bool:
        """退出登录并清理所有相关资源"""
        logger.info("正在退出登录...")
        self.clear_cache()
        self.token = None
        self.cookies = None
        logger.success("退出登录完成")
        return True

    def get_token(self) -> Optional[str]:
        """获取访问令牌"""
        if not self.token and not (self.load_cache() and self.validate_cache()):
            return None
        return self.token

    def get_cookies(self) -> Optional[Dict[str, str]]:
        """获取 cookie 字典"""
        if not self.cookies and not (self.load_cache() and self.validate_cache()):
            return None
        return self.cookies

    def get_cookie_string(self) -> Optional[str]:
        """获取 HTTP 请求头格式的 cookie 字符串"""
        cookies = self.get_cookies()
        if not cookies:
            return None
        return '; '.join([f"{key}={value}" for key, value in cookies.items()])

    def get_headers(self) -> Optional[Dict[str, str]]:
        """获取完整的 HTTP 请求头"""
        cookie_string = self.get_cookie_string()
        if not cookie_string:
            return None
        return {
            "cookie": cookie_string,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
        }

    def is_logged_in(self) -> bool:
        """快速检查是否处于登录状态"""
        return self.check_login_status()['isLoggedIn']


def quick_login() -> Tuple[Optional[str], Optional[Dict], Optional[Dict]]:
    """快速登录便捷函数"""
    login_manager = WeChatSpiderLogin()
    if login_manager.login():
        return (
            login_manager.get_token(),
            login_manager.get_cookies(),
            login_manager.get_headers()
        )
    return (None, None, None)


def check_login() -> Dict[str, Any]:
    """检查登录状态便捷函数"""
    login_manager = WeChatSpiderLogin()
    return login_manager.check_login_status()
