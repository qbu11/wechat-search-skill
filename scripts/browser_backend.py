#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器后端抽象层
================

优先级：
1. agent-browser CLI（已安装）
2. 从 vercel-labs/agent-browser 安装
3. DrissionPage（Chrome）
"""

import json
import logging
import os
import re
import shutil
import subprocess
import time

logger = logging.getLogger("wechat-search")


def detect_backend():
    """检测可用的浏览器后端，返回 'drissionpage' 或 'agent-browser'"""
    try:
        import DrissionPage
        logger.info("检测到 DrissionPage")
        return "drissionpage"
    except ImportError:
        pass

    if shutil.which("agent-browser"):
        logger.info("DrissionPage 未安装，使用 agent-browser CLI")
        return "agent-browser"

    if _try_install_agent_browser():
        return "agent-browser"

    logger.warning("无可用浏览器后端（DrissionPage 未安装，agent-browser 不可用）")
    return "none"


def _try_install_agent_browser():
    """尝试从 npm 安装 agent-browser"""
    try:
        result = subprocess.run(
            ["npm", "install", "-g", "agent-browser"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and shutil.which("agent-browser"):
            logger.info("已从 npm 安装 agent-browser")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    try:
        result = subprocess.run(
            ["npx", "-y", "agent-browser", "--version"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            logger.info("可通过 npx 使用 agent-browser")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return False


class AgentBrowserBackend:
    """agent-browser CLI 后端封装"""

    def __init__(self):
        self._cmd = self._resolve_cmd()
        self._current_url = None

    def _resolve_cmd(self):
        if shutil.which("agent-browser"):
            return ["agent-browser"]
        return ["npx", "-y", "agent-browser"]

    def _run(self, *args, timeout=30):
        cmd = self._cmd + list(args)
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            if result.returncode != 0:
                logger.debug("agent-browser 命令失败: %s\nstderr: %s", " ".join(cmd), result.stderr)
                return None
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug("agent-browser 执行异常: %s", e)
            return None

    def open(self, url, timeout=30):
        """导航到 URL"""
        output = self._run("open", url, timeout=timeout)
        if output is not None:
            self._current_url = url
            return True
        return False

    def snapshot(self):
        """获取页面 accessibility tree 快照"""
        return self._run("snapshot", timeout=15)

    def screenshot(self, path=None):
        """截图"""
        if path:
            return self._run("screenshot", path, timeout=15)
        return self._run("screenshot", timeout=15)

    def evaluate(self, js_code, timeout=15):
        """在页面执行 JavaScript 并返回结果"""
        return self._run("eval", js_code, timeout=timeout)

    def click(self, ref):
        """点击元素（用 snapshot 中的 @ref）"""
        return self._run("click", str(ref), timeout=10)

    @property
    def url(self):
        return self._current_url

    def get_page_html(self):
        """通过 JS 获取页面完整 HTML"""
        return self.evaluate("document.documentElement.outerHTML")

    def get_element_html(self, selector):
        """通过 CSS 选择器获取元素 innerHTML"""
        js = f"document.querySelector('{selector}')?.innerHTML || ''"
        return self.evaluate(js)

    def get_element_text(self, selector):
        """通过 CSS 选择器获取元素文本"""
        js = f"document.querySelector('{selector}')?.textContent?.trim() || ''"
        return self.evaluate(js)

    def get_current_url(self):
        """获取当前页面 URL"""
        result = self.evaluate("window.location.href")
        if result:
            self._current_url = result
        return self._current_url

    def wait_for_url_contains(self, substring, timeout=15):
        """等待 URL 包含指定字符串"""
        start = time.time()
        while time.time() - start < timeout:
            url = self.get_current_url()
            if url and substring in url:
                return url
            time.sleep(0.5)
        return self.get_current_url()

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
