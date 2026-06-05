#!/usr/bin/env python3
# _*_ coding:utf-8 _*_

# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Keyboard navigation menu module.

Uses ↑↓←→Enter to navigate DTK menus (DMenu::exec() transient popups).
More stable than hover-crawl — no mouse coordinate dependency.

DTK menus (DMenu::exec()) create transient popups not in static AT-SPI tree.
This module uses keyboard navigation + AT-SPI focused state reading.
"""

import time
import logging

logger = logging.getLogger(__name__)


class MenuNotFoundError(Exception):
    """Menu item not found."""

    pass


class MenuNavigator:
    """Keyboard navigation menu operator.

    Usage:
        nav = MenuNavigator("deepin-reader", "Deepin Reader")
        nav.open_main_menu()
        nav.select(["文件", "打开"])

        nav.open_context_menu(500, 300)
        nav.select(["复制"])
    """

    MAX_LOOP = 50  # Max iterations per menu level

    def __init__(self, name=None, desc=None):
        self.app_name = name
        self.desc = desc
        self.mk = None  # MouseKey instance, lazy init
        self._app_node = None  # Cached AT-SPI app node

    def _ensure_mk(self):
        """Lazy-init MouseKey to keep module importable without desktop."""
        if self.mk is None:
            from src.mouse_key import MouseKey

            self.mk = MouseKey()
        return self.mk

    def _ensure_app_node(self):
        """Lazy-init AT-SPI app node. Cached for entire navigation session."""
        if self._app_node is None:
            from src.dogtail_utils import DogtailUtils

            dog = DogtailUtils(self.app_name, self.desc) if self.app_name else DogtailUtils()
            self._app_node = dog.obj  # DogtailUtils.obj is the connected app node
        return self._app_node

    def open_main_menu(self):
        """Open main menu via Alt key."""
        self._ensure_mk().press_key("Alt")
        time.sleep(0.3)

    def open_context_menu(self, x, y):
        """Open context menu via right-click at coordinates."""
        self._ensure_mk().right_click(x, y)
        time.sleep(0.3)

    def _walk_menu_items(self, node):
        """Recursively yield menu/menu_item nodes from AT-SPI tree."""
        try:
            children = node.children if hasattr(node, "children") else []
        except Exception:
            return
        for child in children:
            try:
                role = getattr(child, "roleName", "").lower()
            except Exception:
                continue
            if role in (
                "menu item",
                "menu",
                "check menu item",
                "radio menu item",
                "push button",
            ):
                yield child
            yield from self._walk_menu_items(child)

    def _read_focused_item(self):
        """Read current AT-SPI focused menu item text.

        Returns empty string if no focused item found.
        """
        app_node = self._ensure_app_node()
        for child in self._walk_menu_items(app_node):
            try:
                states = set(
                    s.lower() for s in getattr(child, "states", []) if hasattr(child, "states")
                )
            except Exception:
                continue
            if "focused" in states:
                return getattr(child, "name", "") or ""
        return ""

    def navigate_to(self, items, exact=False):
        """Navigate to target menu item(s) using keyboard.

        Args:
            items: Menu path, e.g. ["文件", "打开"] or ["复制"]
            exact: True=exact match, False=substring match (case-insensitive)

        Raises:
            MenuNotFoundError: target item not found or menu closed unexpectedly
        """
        for i, target in enumerate(items):
            found = False
            start_text = self._read_focused_item()

            for iteration in range(self.MAX_LOOP):
                current = self._read_focused_item()

                # Menu closed unexpectedly
                if not current and not start_text and iteration > 0:
                    raise MenuNotFoundError(f"菜单已关闭, 无法导航到 '{target}'")

                # Check match
                matched = (
                    (current == target)
                    if exact
                    else (target.lower() in current.lower() if current else False)
                )

                if matched:
                    found = True
                    break

                # Wrapped around without finding
                if iteration > 0 and current == start_text:
                    raise MenuNotFoundError(f"菜单项 '{target}' 不存在于第 {i + 1} 层菜单")

                # Move down
                self._ensure_mk().press_key("Down")
                time.sleep(0.1)

            if not found:
                raise MenuNotFoundError(f"菜单项 '{target}' 未找到 (超过 {self.MAX_LOOP} 次循环)")

            # Enter submenu if not last item
            if i < len(items) - 1:
                self._ensure_mk().press_key("Right")
                time.sleep(0.3)

    def select(self, items, exact=False):
        """Navigate to target and press Enter."""
        self.navigate_to(items, exact)
        self._ensure_mk().press_key("Return")
        time.sleep(0.3)

    def cancel(self):
        """Close current menu via Escape."""
        self._ensure_mk().press_key("Escape")
