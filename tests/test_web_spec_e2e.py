# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""End-to-end tests for src.web_spec runner with a real browser."""

from importlib.util import find_spec
from pathlib import Path

import pytest

from web_spec.config import WebSpecConfig
from web_spec.models import TestSpec
from web_spec.reporter import save_spec_report
from web_spec.result import RunStatus
from web_spec.runner import WebSpecRunner


pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module", autouse=True)
def skip_without_playwright_browser():
    """Skip browser E2E when Playwright or browser binaries are unavailable."""
    if find_spec("playwright") is None:
        pytest.skip("Playwright 未安装")
    from playwright.sync_api import sync_playwright

    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=True)
        browser.close()
        playwright.stop()
    except Exception as exc:
        try:
            playwright.stop()
        except Exception:
            pass
        pytest.skip(f"Playwright Chromium 不可用: {exc}")


def _fixture_url() -> str:
    fixture = Path(__file__).parent / "fixtures" / "web_spec_app" / "index.html"
    return fixture.resolve().as_uri()


def test_web_spec_runner_executes_real_browser_flow(tmp_path):
    spec = TestSpec.model_validate({
        "id": "fixture-flow",
        "title": "Fixture flow",
        "entry_url": _fixture_url(),
        "steps": [
            {
                "description": "提交名称",
                "actions": [
                    {
                        "type": "fill",
                        "locator": {"strategy": "test_id", "value": "name-input"},
                        "value": "YouQu",
                    },
                    {
                        "type": "click",
                        "locator": {"strategy": "test_id", "value": "submit-button"},
                    },
                ],
                "assertions": [
                    {
                        "type": "text_contains",
                        "locator": {"strategy": "test_id", "value": "result"},
                        "expected": "提交成功：YouQu",
                    }
                ],
            },
            {
                "description": "显示详情面板",
                "actions": [
                    {
                        "type": "click",
                        "locator": {"strategy": "test_id", "value": "toggle-button"},
                    }
                ],
                "assertions": [
                    {
                        "type": "visible",
                        "locator": {"strategy": "test_id", "value": "details-panel"},
                    }
                ],
            },
        ],
    })
    runner = WebSpecRunner(WebSpecConfig(headless=True, screenshot_on_step=True))

    record = runner.run_spec(spec, tmp_path)
    save_spec_report(record)

    assert record.status == RunStatus.PASSED
    assert (Path(record.report_dir) / "report.json").exists()
    assert (Path(record.report_dir) / "report.html").exists()
    assert any(step.screenshot_path and Path(step.screenshot_path).exists() for step in record.steps)


def test_web_spec_runner_records_failed_assertion(tmp_path):
    spec = TestSpec.model_validate({
        "id": "fixture-failure",
        "title": "Fixture failure",
        "entry_url": _fixture_url(),
        "steps": [
            {
                "description": "断言不存在的文本",
                "assertions": [
                    {
                        "type": "text_contains",
                        "locator": {"strategy": "test_id", "value": "result"},
                        "expected": "不会出现的文本",
                        "timeout_ms": 100,
                    }
                ],
            }
        ],
    })
    runner = WebSpecRunner(WebSpecConfig(headless=True, screenshot_on_step=True, retry_interval_ms=20))

    record = runner.run_spec(spec, tmp_path)
    save_spec_report(record)

    assert record.status == RunStatus.FAILED_PRODUCT
    assert (Path(record.report_dir) / "report.json").exists()
    assert (Path(record.report_dir) / "report.html").exists()
    assert record.steps[0].assertions[0].success is False
    assert record.steps[0].assertions[0].error
