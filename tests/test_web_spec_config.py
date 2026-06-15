# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.web_spec.config."""

from web_spec.config import load_web_spec_config


def test_default_config_values():
    config = load_web_spec_config()

    assert config.entry_route == "/"
    assert config.viewport.width == 1280
    assert config.viewport.height == 720
    assert config.browser == "chromium"
    assert config.report_dir == "report/web_spec"


def test_load_flat_yaml_config(tmp_path):
    config_path = tmp_path / "web_spec.yaml"
    config_path.write_text("""
base_url: http://localhost:3000
entry_route: /chat
headless: false
viewport: 1440x900
browser: firefox
assertion_timeout_ms: 1000
retry_interval_ms: 50
screenshot_on_step: false
report_dir: /tmp/web-report
""", encoding="utf-8")

    config = load_web_spec_config(config_path)

    assert config.base_url == "http://localhost:3000"
    assert config.entry_route == "/chat"
    assert config.headless is False
    assert config.viewport.width == 1440
    assert config.viewport.height == 900
    assert config.browser == "firefox"
    assert config.assertion_timeout_ms == 1000
    assert config.retry_interval_ms == 50
    assert config.screenshot_on_step is False
    assert config.report_dir == "/tmp/web-report"


def test_load_nested_web_spec_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("""
web_spec:
  base_url: http://example.test
  viewport:
    width: 1366
    height: 768
""", encoding="utf-8")

    config = load_web_spec_config(config_path)

    assert config.base_url == "http://example.test"
    assert config.viewport.width == 1366
    assert config.viewport.height == 768


def test_load_legacy_target_engine_paths_shape(tmp_path):
    config_path = tmp_path / "legacy.yaml"
    config_path.write_text("""
target:
  base_url: http://legacy.test
  headless: false
  viewport:
    width: 1024
    height: 768
engine:
  entry_route: /entry
  assertion_timeout_ms: 2000
  assertion_retry_interval_ms: 100
  screenshot_on_step: false
paths:
  logs_dir: ./logs
ai:
  main_model:
    api_key: should-not-be-used
""", encoding="utf-8")

    config = load_web_spec_config(config_path)

    assert config.base_url == "http://legacy.test"
    assert config.entry_route == "/entry"
    assert config.headless is False
    assert config.retry_interval_ms == 100
    assert config.report_dir == "./logs"


def test_cli_overrides_win(tmp_path):
    config_path = tmp_path / "web_spec.yaml"
    config_path.write_text("headless: true\nreport_dir: old\n", encoding="utf-8")

    config = load_web_spec_config(config_path, overrides={"headless": False, "report_dir": "new"})

    assert config.headless is False
    assert config.report_dir == "new"
