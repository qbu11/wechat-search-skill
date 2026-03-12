#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众平台登录模块
==================

实现微信公众平台的自动化登录流程，获取爬虫运行所需的认证信息。
"""

import json
import os
import random
import time
import platform
import tempfile
import shutil
import subprocess
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import re

from wechat_search.spider.log.utils import logger
from wechat_search.spider.wechat.paths import get_wechat_cache_file

# 缓存文件路径（存储在用户数据目录）
CACHE_FILE = get_wechat_cache_file()

# 缓存有效期：4 天（微信 token 一般 4-7 天过期）
CACHE_EXPIRE_HOURS = 24 * 4


class WeChatSpiderLogin:
    """
    微信公众平台登录管理器

    负责处理登录认证的完整生命周期，包括：
    - 缓存的读取、验证和保存
    - 浏览器的启动和配置
    - 登录流程的执行和监控
    - 资源的清理和释放
    """

    def __init__(self, cache_file=CACHE_FILE):
        self.token = None
        self.cookies = None
        self.cache_file = cache_file
        self.cache_expire_hours = CACHE_EXPIRE_HOURS
        self.driver = None
        self.temp_user_data_dir = None

    def save_cache(self):
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

    def load_cache(self):
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

            if hours_diff > self.cache_expire_hours:
                logger.info(f"缓存已过期（{hours_diff:.1f}小时前），需要重新登录")
                return False

            self.token = cache_data['token']
            self.cookies = cache_data['cookies']
            logger.info(f"从缓存加载登录信息（{hours_diff:.1f}小时前保存）")
            return True

        except Exception as e:
            logger.error(f"读取缓存失败: {e}，需要重新登录")
            return False

    def validate_cache(self):
        """验证缓存的登录信息是否仍然有效"""
        if not self.token or not self.cookies:
            return False

        try:
            headers = {
                "HOST": "mp.weixin.qq.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
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

    def clear_cache(self):
        """清除本地缓存文件"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                logger.info("缓存已清除")
            return True
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
            return False

    def _setup_chrome_options(self):
        """配置 Chrome 浏览器启动选项"""
        options = webdriver.ChromeOptions()

        self.temp_user_data_dir = tempfile.mkdtemp()
        options.add_argument(f"--user-data-dir={self.temp_user_data_dir}")

        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--force-device-scale-factor=0.9")
        options.add_argument("--high-dpi-support=0.9")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36")

        return options

    def _cleanup_chrome_processes(self):
        """清理残留的 Chrome 进程"""
        try:
            system = platform.system()
            if system == "Windows":
                subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"],
                              stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            elif system in ("Linux", "Darwin"):
                subprocess.run(["pkill", "-f", "chrome"],
                              stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            logger.debug("残留浏览器进程已清理")
        except Exception as e:
            logger.warning(f"清理Chrome进程时出现警告: {e}")

    def _cleanup_temp_files(self):
        """清理临时用户数据目录"""
        if self.temp_user_data_dir and os.path.exists(self.temp_user_data_dir):
            try:
                shutil.rmtree(self.temp_user_data_dir, ignore_errors=True)
                logger.debug("临时用户数据目录已清理")
            except Exception as e:
                logger.warning(f"清理临时目录时出现警告: {e}")

    def login(self):
        """执行登录流程"""
        logger.info("\n" + "="*60)
        logger.info("开始登录微信公众号平台...")
        logger.info("="*60)

        if self.load_cache() and self.validate_cache():
            logger.success("使用有效的缓存登录信息")
            return True
        else:
            logger.info("缓存无效或不存在，需要重新扫码登录")
            self.clear_cache()

        self._cleanup_chrome_processes()

        try:
            logger.info("正在启动Chrome浏览器...")

            chrome_options = self._setup_chrome_options()

            try:
                service = ChromeService()
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.success("Chrome浏览器启动成功")
            except Exception as e:
                logger.error(f"Chrome浏览器启动失败: {e}")
                return False

            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            logger.info("正在访问微信公众号平台...")
            self.driver.get('https://mp.weixin.qq.com/')
            logger.success("页面加载完成")

            logger.info("请在浏览器窗口中扫码登录...")
            logger.info("等待登录完成（最长等待5分钟）...")

            wait = WebDriverWait(self.driver, 300)
            wait.until(EC.url_contains('token'))

            current_url = self.driver.current_url
            logger.success("检测到登录成功！正在获取登录信息...")

            token_match = re.search(r'token=(\d+)', current_url)
            if token_match:
                self.token = token_match.group(1)
                logger.success(f"Token获取成功: {self.token}")
            else:
                logger.error("无法从URL中提取token")
                return False

            raw_cookies = self.driver.get_cookies()
            self.cookies = {item['name']: item['value'] for item in raw_cookies}
            logger.success(f"Cookies获取成功，共{len(self.cookies)}个")

            if self.save_cache():
                logger.success("登录信息已保存到缓存")

            logger.success("登录完成！")
            return True

        except Exception as e:
            logger.error(f"登录过程中出现错误: {e}")
            return False

        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    logger.debug("浏览器已关闭")
                except:
                    pass

            self._cleanup_chrome_processes()
            self._cleanup_temp_files()

    def check_login_status(self):
        """获取当前登录状态的详细信息"""
        if self.load_cache() and self.validate_cache():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                cache_time = datetime.fromtimestamp(cache_data['timestamp'])
                expire_time = cache_time + timedelta(hours=self.cache_expire_hours)
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
            except:
                pass

        return {
            'isLoggedIn': False,
            'message': '未登录或登录已过期'
        }

    def logout(self):
        """退出登录并清理所有相关资源"""
        logger.info("正在退出登录...")
        self.clear_cache()
        self.token = None
        self.cookies = None
        self._cleanup_chrome_processes()
        self._cleanup_temp_files()
        logger.success("退出登录完成")
        return True

    def get_token(self):
        """获取访问令牌"""
        if not self.token and not (self.load_cache() and self.validate_cache()):
            return None
        return self.token

    def get_cookies(self):
        """获取 cookie 字典"""
        if not self.cookies and not (self.load_cache() and self.validate_cache()):
            return None
        return self.cookies

    def get_cookie_string(self):
        """获取 HTTP 请求头格式的 cookie 字符串"""
        cookies = self.get_cookies()
        if not cookies:
            return None
        return '; '.join([f"{key}={value}" for key, value in cookies.items()])

    def get_headers(self):
        """获取完整的 HTTP 请求头"""
        cookie_string = self.get_cookie_string()
        if not cookie_string:
            return None
        return {
            "cookie": cookie_string,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
        }

    def is_logged_in(self):
        """快速检查是否处于登录状态"""
        return self.check_login_status()['isLoggedIn']


def quick_login():
    """快速登录便捷函数"""
    login_manager = WeChatSpiderLogin()
    if login_manager.login():
        return (
            login_manager.get_token(),
            login_manager.get_cookies(),
            login_manager.get_headers()
        )
    return (None, None, None)


def check_login():
    """检查登录状态便捷函数"""
    login_manager = WeChatSpiderLogin()
    return login_manager.check_login_status()
