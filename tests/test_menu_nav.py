"""Unit tests for src/menu_nav.py — fully mocked, no desktop deps."""

import importlib.util as _ilu
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest


_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_menu_nav():
    """Load src/menu_nav.py via spec; bypasses tests/__init__.py's
    sys.modules['src'] = MagicMock() stub."""
    mod_path = _PROJECT_ROOT / "src" / "menu_nav.py"
    spec = _ilu.spec_from_file_location("src.menu_nav", str(mod_path))
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    mod.__package__ = "src"
    sys.modules["src.menu_nav"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_menu_nav = _load_menu_nav()
MenuNavigator = _menu_nav.MenuNavigator
MenuNotFoundError = _menu_nav.MenuNotFoundError


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *_a, **_kw: None)


def _make_node(name="", role="menu item", states=None, children=None):
    n = MagicMock()
    n.name = name
    n.roleName = role
    n.states = states if states is not None else []
    n.children = children if children is not None else []
    return n


def _make_app_with_focused(focused_name):
    focused = _make_node(name=focused_name, states=["focused", "showing"])
    other = _make_node(name="其他", states=["showing"])
    app = _make_node(role="application", children=[focused, other])
    return app, focused, other


def _patch_deps(monkeypatch, app_node):
    mock_mk_inst = MagicMock()
    mock_mk_class = MagicMock(return_value=mock_mk_inst)
    mock_dog_inst = MagicMock()
    mock_dog_inst.obj = app_node
    mock_dog_class = MagicMock(return_value=mock_dog_inst)

    fake_mk_mod = MagicMock()
    fake_mk_mod.MouseKey = mock_mk_class
    fake_dog_mod = MagicMock()
    fake_dog_mod.DogtailUtils = mock_dog_class
    monkeypatch.setitem(sys.modules, "src.mouse_key", fake_mk_mod)
    monkeypatch.setitem(sys.modules, "src.dogtail_utils", fake_dog_mod)
    return mock_mk_inst, mock_mk_class, mock_dog_inst, mock_dog_class


class TestOpenMainMenu:
    def test_open_main_menu(self, monkeypatch):
        app, _, _ = _make_app_with_focused("")
        mk_inst, _, _, _ = _patch_deps(monkeypatch, app)

        nav = MenuNavigator("test-app", "Test App")
        nav.open_main_menu()
        mk_inst.press_key.assert_called_once_with("Alt")


class TestOpenContextMenu:
    def test_open_context_menu(self, monkeypatch):
        app, _, _ = _make_app_with_focused("")
        mk_inst, _, _, _ = _patch_deps(monkeypatch, app)

        nav = MenuNavigator("test-app", "Test App")
        nav.open_context_menu(120, 80)
        mk_inst.right_click.assert_called_once_with(120, 80)


class TestNavigateSingle:
    def test_navigate_to_single_item(self, monkeypatch):
        app, _, _ = _make_app_with_focused("复制")
        mk_inst, _, _, _ = _patch_deps(monkeypatch, app)

        nav = MenuNavigator("test-app", "Test App")
        nav.navigate_to(["复制"])
        assert mk_inst.press_key.call_count == 0


class TestNavigateMultiple:
    def test_navigate_to_multiple_items(self, monkeypatch):
        mk_inst = MagicMock()
        monkeypatch.setattr(MenuNavigator, "_ensure_mk", lambda self: mk_inst)
        monkeypatch.setattr(MenuNavigator, "_ensure_app_node", lambda self: MagicMock())

        nav = MenuNavigator("test-app", "Test App")
        nav._ensure_mk = lambda: mk_inst

        sequence = iter(["文件", "文件", "打开", "打开"])
        monkeypatch.setattr(
            MenuNavigator,
            "_read_focused_item",
            lambda self: next(sequence),
        )
        nav.navigate_to(["文件", "打开"])

        calls = [c.args[0] for c in mk_inst.press_key.call_args_list]
        assert "Right" in calls


class TestNavigateNotFound:
    def test_navigate_to_not_found(self, monkeypatch):
        mk_inst = MagicMock()
        monkeypatch.setattr(MenuNavigator, "_ensure_mk", lambda self: mk_inst)
        monkeypatch.setattr(MenuNavigator, "_ensure_app_node", lambda self: MagicMock())

        nav = MenuNavigator("test-app", "Test App")
        nav.MAX_LOOP = 4
        sequence = iter(["编辑", "查看", "帮助", "工具", "格式"])

        def fake_read(self):
            return next(sequence)

        monkeypatch.setattr(MenuNavigator, "_read_focused_item", fake_read)

        with pytest.raises(MenuNotFoundError, match="未找到"):
            nav.navigate_to(["目标项"])


class TestNavigateWrapAround:
    def test_navigate_to_wrap_around(self, monkeypatch):
        app, _, _ = _make_app_with_focused("编辑")
        mk_inst, _, _, _ = _patch_deps(monkeypatch, app)

        nav = MenuNavigator("test-app", "Test App")
        nav.MAX_LOOP = 5
        monkeypatch.setattr(
            MenuNavigator,
            "_read_focused_item",
            lambda self: "编辑",
        )
        nav.mk = mk_inst

        with pytest.raises(MenuNotFoundError, match="不存在"):
            nav.navigate_to(["目标项"])


class TestSelect:
    def test_select_calls_enter(self, monkeypatch):
        app, _, _ = _make_app_with_focused("复制")
        mk_inst, _, _, _ = _patch_deps(monkeypatch, app)

        nav = MenuNavigator("test-app", "Test App")
        nav.select(["复制"])
        mk_inst.press_key.assert_called_once_with("Return")


class TestCancel:
    def test_cancel_calls_escape(self, monkeypatch):
        app, _, _ = _make_app_with_focused("")
        mk_inst, _, _, _ = _patch_deps(monkeypatch, app)

        nav = MenuNavigator("test-app", "Test App")
        nav.cancel()
        mk_inst.press_key.assert_called_once_with("Escape")


class TestExactMatch:
    def test_exact_match(self, monkeypatch):
        app, _, _ = _make_app_with_focused("复制")
        mk_inst, _, _, _ = _patch_deps(monkeypatch, app)

        nav = MenuNavigator("test-app", "Test App")
        nav.navigate_to(["复制"], exact=True)
        assert mk_inst.press_key.call_count == 0

    def test_exact_match_rejects_substring(self, monkeypatch):
        app, _, _ = _make_app_with_focused("复制粘贴")
        mk_inst, _, _, _ = _patch_deps(monkeypatch, app)

        nav = MenuNavigator("test-app", "Test App")
        nav.MAX_LOOP = 3
        monkeypatch.setattr(
            MenuNavigator,
            "_read_focused_item",
            lambda self: "复制粘贴",
        )
        nav.mk = mk_inst

        with pytest.raises(MenuNotFoundError):
            nav.navigate_to(["复制"], exact=True)


class TestAppNodeCached:
    def test_app_node_cached(self, monkeypatch):
        mock_dog_inst = MagicMock()
        expected_node = MagicMock()
        mock_dog_inst.obj = expected_node
        mock_dog_class = MagicMock(return_value=mock_dog_inst)

        fake_dog_mod = MagicMock()
        fake_dog_mod.DogtailUtils = mock_dog_class
        monkeypatch.setitem(sys.modules, "src.dogtail_utils", fake_dog_mod)

        nav = MenuNavigator("test-app", "Test App")
        node1 = nav._ensure_app_node()
        node2 = nav._ensure_app_node()

        assert node1 is expected_node
        assert node1 is node2
        mock_dog_class.assert_called_once_with("test-app", "Test App")


class TestMenuClosed:
    def test_menu_closed_unexpectedly(self, monkeypatch):
        app, _, _ = _make_app_with_focused("")
        mk_inst, _, _, _ = _patch_deps(monkeypatch, app)

        nav = MenuNavigator("test-app", "Test App")
        nav.MAX_LOOP = 5
        sequence = iter(["", "", "", "", ""])

        def fake_read(self):
            return next(sequence)

        monkeypatch.setattr(MenuNavigator, "_read_focused_item", fake_read)
        nav.mk = mk_inst

        with pytest.raises(MenuNotFoundError, match="菜单已关闭"):
            nav.navigate_to(["目标项"])
