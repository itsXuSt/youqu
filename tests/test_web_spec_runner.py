# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.web_spec.runner helpers."""

from web_spec.config import WebSpecConfig
from web_spec.models import TestSpec
from web_spec.runner import WebSpecRunner


def test_entry_url_joins_base_url_and_route():
    runner = WebSpecRunner(WebSpecConfig(base_url="http://example.test/app", entry_route="/chat"))
    spec = TestSpec.model_validate({
        "id": "case",
        "title": "Case",
        "steps": [{
            "description": "检查",
            "assertions": [{"type": "visible", "locator": {"strategy": "text", "value": "ok"}}],
        }],
    })

    assert runner._entry_url(spec) == "http://example.test/app/chat"


def test_spec_entry_url_wins():
    runner = WebSpecRunner(WebSpecConfig(base_url="http://example.test", entry_route="/chat"))
    spec = TestSpec.model_validate({
        "id": "case",
        "title": "Case",
        "entry_url": "http://other.test/start",
        "steps": [{
            "description": "检查",
            "assertions": [{"type": "visible", "locator": {"strategy": "text", "value": "ok"}}],
        }],
    })

    assert runner._entry_url(spec) == "http://other.test/start"
