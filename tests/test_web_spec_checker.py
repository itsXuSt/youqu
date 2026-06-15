# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.web_spec.checker."""

from web_spec.checker import check_specs


def test_check_specs_passes_valid_spec(tmp_path):
    spec_path = tmp_path / "login.yaml"
    spec_path.write_text("""
id: login
title: 登录测试
steps:
  - description: 检查
    assertions:
      - type: visible
        locator: {strategy: test_id, value: submit}
""", encoding="utf-8")

    report = check_specs(spec_path)

    assert report.checked == 1
    assert report.skipped == 0
    assert report.errors == 0
    assert report.warnings == 0


def test_check_specs_reports_yaml_parse_error(tmp_path):
    spec_path = tmp_path / "bad.yaml"
    spec_path.write_text("title: [未闭合\n", encoding="utf-8")

    report = check_specs(spec_path)

    assert report.checked == 1
    assert report.errors == 1
    assert report.issues[0].code == "yaml_parse"


def test_check_specs_skips_desktop_yaml_and_elements(tmp_path):
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    (spec_dir / "elements.yaml").write_text("""
login_button:
  name: 登录
""", encoding="utf-8")
    (spec_dir / "test_desktop.yaml").write_text("""
name: 桌面 YAML 用例
app: deepin-example
steps:
  - action: click
    ref: login_button
""", encoding="utf-8")
    (spec_dir / "web.yaml").write_text("""
title: Web 用例
steps:
  - description: 检查
    assertions:
      - type: visible
        locator: {strategy: text, value: 完成, exact: true}
""", encoding="utf-8")

    report = check_specs(spec_dir)

    assert report.checked == 1
    assert report.skipped == 2
    assert report.errors == 0


def test_check_specs_reports_web_spec_schema_error_when_steps_missing(tmp_path):
    spec_path = tmp_path / "missing_steps.yaml"
    spec_path.write_text("""
title: 缺少步骤
module: 认证
""", encoding="utf-8")

    report = check_specs(spec_path)

    assert report.checked == 1
    assert report.skipped == 0
    assert report.errors == 1
    assert report.issues[0].code == "schema"


def test_check_specs_reports_migrating_web_spec_shape(tmp_path):
    spec_path = tmp_path / "old_shape.yaml"
    spec_path.write_text("""
title: 旧字段迁移
steps:
  - action: click
    locator: {strategy: text, value: 登录}
""", encoding="utf-8")

    report = check_specs(spec_path)

    assert report.checked == 1
    assert report.skipped == 0
    assert report.errors == 1
    assert report.issues[0].code == "schema"


def test_check_specs_reports_missing_expected(tmp_path):
    spec_path = tmp_path / "missing_expected.yaml"
    spec_path.write_text("""
title: 缺少期望
steps:
  - description: 检查数量
    assertions:
      - type: count
        locator: {strategy: css, value: .item}
""", encoding="utf-8")

    report = check_specs(spec_path)

    assert report.checked == 1
    assert report.errors == 1
    assert "missing_expected" in {issue.code for issue in report.issues}


def test_check_specs_warns_about_fragile_and_broad_locators(tmp_path):
    spec_path = tmp_path / "fragile.yaml"
    spec_path.write_text("""
title: 脆弱选择器
steps:
  - description: 检查
    actions:
      - type: click
        locator: {strategy: css, value: "div > div > div .item:nth-child(1)"}
    assertions:
      - type: visible
        locator: {strategy: text, value: 提交}
      - type: count
        locator: {strategy: css, value: div}
        expected: 1
""", encoding="utf-8")

    report = check_specs(spec_path)
    codes = {issue.code for issue in report.issues}

    assert report.errors == 0
    assert "fragile_selector" in codes
    assert "broad_text_locator" in codes
    assert "broad_css_locator" in codes


def test_check_specs_reports_missing_attribute(tmp_path):
    spec_path = tmp_path / "attribute.yaml"
    spec_path.write_text("""
title: 属性断言
steps:
  - description: 检查
    assertions:
      - type: attribute_equals
        locator: {strategy: css, value: button}
        expected: 提交
""", encoding="utf-8")

    report = check_specs(spec_path)

    assert report.errors == 1
    assert "missing_attribute" in {issue.code for issue in report.issues}


def test_check_specs_warns_about_long_static_wait_and_legacy_fields(tmp_path):
    spec_path = tmp_path / "legacy.yaml"
    spec_path.write_text("""
name: 兼容标题
steps:
  - description: 等待
    actions:
      - type: wait_for
        timeout_ms: 20000
    assert:
      - type: url_contains
        expected: /done
        locator: {strategy: css, value: body}
""", encoding="utf-8")

    report = check_specs(spec_path)
    codes = {issue.code for issue in report.issues}

    assert report.errors == 0
    assert "legacy_name" in codes
    assert "legacy_assert" in codes
    assert "long_static_wait" in codes
    assert "unused_locator" in codes
