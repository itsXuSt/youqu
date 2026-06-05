# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.yaml_test.parser."""

import pytest
from pydantic import ValidationError

from src.yaml_test.parser import parse_testcase


def _write_yaml(tmp_path, content):
    p = tmp_path / "test_case.yaml"
    p.write_text(content, encoding="utf-8")
    (tmp_path / "elements.yaml").write_text(
        "app: test\nelements:\n  ok:\n    name: OK\n", encoding="utf-8"
    )
    return p


class TestParseSimple:
    def test_parse_simple_testcase(self, tmp_path):
        p = _write_yaml(tmp_path, """
name: "打开关于对话框"
app: "deepin-reader"
setup:
  - action: session_start
    command: "deepin-reader"
steps:
  - name: "点击按钮"
    action: element_action
    selector: {name: "OK"}
    do: click
teardown:
  - action: session_stop
""")
        tc = parse_testcase(p)
        assert tc.name == "打开关于对话框"
        assert tc.app == "deepin-reader"
        assert len(tc.setup) == 1
        assert tc.setup[0].action == "session_start"
        assert tc.setup[0].command == "deepin-reader"
        assert len(tc.steps) == 1
        assert tc.steps[0].selector.name == "OK"
        assert tc.steps[0].do == "click"
        assert len(tc.teardown) == 1

    def test_parse_minimal_testcase(self, tmp_path):
        p = _write_yaml(tmp_path, """
name: "最小用例"
steps:
  - action: wait
    wait: 0.1
""")
        tc = parse_testcase(p)
        assert tc.name == "最小用例"
        assert tc.app == ""
        assert tc.screenshot is False
        assert len(tc.steps) == 1


class TestVariableSubstitution:
    def test_parse_with_vars(self, tmp_path):
        p = _write_yaml(tmp_path, """
name: "变量替换"
vars:
  APP_NAME: "deepin-music"
setup:
  - action: session_start
    command: "${APP_NAME}"
steps:
  - action: wait
    wait: 0.0
""")
        tc = parse_testcase(p)
        assert tc.setup[0].command == "deepin-music"

    def test_parse_nested_vars(self, tmp_path):
        p = _write_yaml(tmp_path, """
name: "嵌套变量"
vars:
  PREFIX: "/home/user"
  FILE: "doc.pdf"
setup:
  - action: session_start
    command: "${PREFIX}/${FILE}"
steps:
  - action: wait
    wait: 0.0
""")
        tc = parse_testcase(p)
        assert tc.setup[0].command == "/home/user/doc.pdf"

    def test_parse_undefined_var_preserved(self, tmp_path):
        p = _write_yaml(tmp_path, """
name: "未定义变量"
vars:
  A: "hello"
steps:
  - action: keyboard_type
    text: "${A} ${UNDEFINED}"
""")
        tc = parse_testcase(p)
        assert tc.steps[0].text == "hello ${UNDEFINED}"


class TestValidation:
    def test_parse_missing_name_raises(self, tmp_path):
        p = _write_yaml(tmp_path, """
steps:
  - action: wait
    wait: 0.0
""")
        with pytest.raises(ValidationError):
            parse_testcase(p)

    def test_parse_empty_file_raises(self, tmp_path):
        p = _write_yaml(tmp_path, "")
        with pytest.raises((ValueError, ValidationError)):
            parse_testcase(p)

    def test_parse_non_mapping_raises(self, tmp_path):
        p = _write_yaml(tmp_path, "- item1\n- item2")
        with pytest.raises((ValueError, ValidationError)):
            parse_testcase(p)


class TestComplexFields:
    def test_parse_with_wait_for(self, tmp_path):
        p = _write_yaml(tmp_path, """
name: "wait_for 测试"
steps:
  - name: "等待对话框"
    action: element_action
    selector: {name: "OK"}
    do: click
    wait_for:
      selector: {role: "dialog"}
      timeout: 3000
      interval: 100
""")
        tc = parse_testcase(p)
        assert tc.steps[0].wait_for is not None
        assert tc.steps[0].wait_for.timeout == 3000
        assert tc.steps[0].wait_for.interval == 100
        assert tc.steps[0].wait_for.selector.role == "dialog"

    def test_parse_with_asserts(self, tmp_path):
        p = _write_yaml(tmp_path, """
name: "断言测试"
steps:
  - name: "点击并验证"
    action: element_action
    selector: {name: "确定"}
    do: click
    assert:
      - type: element_visible
        selector: {name: "OK"}
      - type: process_running
        app: "deepin-reader"
""")
        tc = parse_testcase(p)
        assert len(tc.steps[0].assert_steps) == 2
        assert tc.steps[0].assert_steps[0].type == "element_visible"
        assert tc.steps[0].assert_steps[1].app == "deepin-reader"

    def test_parse_full_testcase(self, tmp_path):
        p = _write_yaml(tmp_path, """
name: "完整用例"
app: "test-app"
screenshot: true
vars:
  FILE_PATH: "/tmp/test.pdf"
setup:
  - action: session_start
    command: "test-app ${FILE_PATH}"
    wait: 2.0
steps:
  - name: "点击按钮"
    action: element_action
    selector: {name: "打开", role: "push button"}
    do: click
    wait_after: 500
    wait_for:
      selector: {role: "dialog"}
      timeout: 5000
    assert:
      - type: element_visible
        selector: {name: "OK"}
      - type: element_numbers
        selector: {name: "tab"}
        number: 3
teardown:
  - action: session_stop
  - action: screenshot
""")
        tc = parse_testcase(p)
        assert tc.name == "完整用例"
        assert tc.app == "test-app"
        assert tc.screenshot is True
        assert tc.vars["FILE_PATH"] == "/tmp/test.pdf"
        assert tc.setup[0].command == "test-app /tmp/test.pdf"
        assert tc.setup[0].wait == 2.0
        assert tc.steps[0].wait_after == 500
        assert len(tc.steps[0].assert_steps) == 2
        assert tc.steps[0].assert_steps[1].number == 3
        assert len(tc.teardown) == 2
