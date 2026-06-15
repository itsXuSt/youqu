# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.web_spec.models."""

import pytest
from pydantic import ValidationError

from web_spec.models import AssertionType, LocatorStrategy, TestSpec


def test_parse_minimal_web_spec():
    spec = TestSpec.model_validate({
        "id": "login_smoke",
        "title": "登录冒烟测试",
        "steps": [{
            "order": 1,
            "description": "点击登录按钮",
            "actions": [{
                "type": "click",
                "locator": {"strategy": "role", "value": "button", "name": "登录"},
            }],
            "assertions": [{
                "type": "visible",
                "locator": {"strategy": "text", "value": "欢迎"},
            }],
        }],
    })

    assert spec.id == "login_smoke"
    assert spec.steps[0].actions[0].locator.strategy == LocatorStrategy.ROLE
    assert spec.steps[0].assertions[0].type == AssertionType.VISIBLE


def test_order_assertion_is_not_exposed():
    with pytest.raises(ValidationError):
        TestSpec.model_validate({
            "id": "order_case",
            "title": "顺序断言",
            "steps": [{
                "description": "检查顺序",
                "assertions": [{"type": "order", "expected": ["A", "B"]}],
            }],
        })


def test_locator_first_flag_is_supported():
    spec = TestSpec.model_validate({
        "id": "first_case",
        "title": "取第一个匹配元素",
        "steps": [{
            "description": "点击第一个",
            "actions": [{
                "type": "click",
                "locator": {"strategy": "css", "value": ".item", "first": True},
            }],
        }],
    })

    assert spec.steps[0].actions[0].locator.first is True
