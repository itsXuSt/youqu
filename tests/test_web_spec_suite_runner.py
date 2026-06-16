# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for WebSpecRunner suite execution."""

from web_spec.config import WebSpecConfig
from web_spec.models import TestSpec
from web_spec.result import RunRecord, RunStatus
from web_spec.runner import WebSpecRunner
from web_spec.suite import SuiteSpec


def _spec(spec_id):
    return TestSpec.model_validate({
        "id": spec_id,
        "title": spec_id,
        "steps": [{
            "description": "检查",
            "assertions": [{"type": "visible", "locator": {"strategy": "text", "value": "ok"}}],
        }],
    })


class FakePage:
    def __init__(self):
        self.closed = False
        self.urls = []
        self.cookies_cleared = False
        self.context = self

    def goto(self, url, wait_until=None):
        self.urls.append(url)

    def close(self):
        self.closed = True

    def clear_cookies(self):
        self.cookies_cleared = True


class FakeContext:
    def __init__(self):
        self.pages = []

    def new_page(self):
        page = FakePage()
        self.pages.append(page)
        return page

    def close(self):
        pass


def test_run_suite_fast_fail_marks_remaining_specs_cancelled(tmp_path, monkeypatch):
    runner = WebSpecRunner(WebSpecConfig(base_url="http://example.test", report_dir=str(tmp_path)))
    runner._context = FakeContext()
    monkeypatch.setattr(runner, "_start_browser", lambda: None)
    monkeypatch.setattr(runner, "_stop_browser", lambda: None)

    def fake_run_spec(spec, report_root=None, spec_index=1, total_specs=1):
        record = RunRecord(spec_id=spec.id, spec_title=spec.title, report_dir=str(tmp_path / spec.id))
        if spec.id == "first":
            record.status = RunStatus.FAILED_PRODUCT
            record.error = "failed"
        record.finalize()
        return record

    monkeypatch.setattr(runner, "run_spec", fake_run_spec)
    suite_spec = SuiteSpec(id="suite", name="Suite", fast_fail=True, specs=[_spec("first"), _spec("second")])

    suite = runner.run_suite(suite_spec, report_dir=tmp_path)

    assert [record.status for record in suite.specs] == [RunStatus.FAILED_PRODUCT, RunStatus.CANCELLED]
    assert "fast_fail" in suite.specs[1].error
    assert (tmp_path / "summary.json").exists()


def test_run_suite_runs_teardown_after_failed_spec(tmp_path, monkeypatch):
    runner = WebSpecRunner(WebSpecConfig(base_url="http://example.test", report_dir=str(tmp_path)))
    context = FakeContext()
    runner._context = context
    monkeypatch.setattr(runner, "_start_browser", lambda: None)
    monkeypatch.setattr(runner, "_stop_browser", lambda: None)
    lifecycle_calls = []

    def fake_lifecycle(teardown, execution):
        lifecycle_calls.append(len(teardown.steps))
        return None

    def fake_run_spec(spec, report_root=None, spec_index=1, total_specs=1):
        record = RunRecord(
            spec_id=spec.id,
            spec_title=spec.title,
            status=RunStatus.FAILED_PRODUCT,
            error="failed",
            report_dir=str(tmp_path / spec.id),
        )
        record.finalize()
        return record

    monkeypatch.setattr(runner, "_run_lifecycle_teardown", fake_lifecycle)
    monkeypatch.setattr(runner, "run_spec", fake_run_spec)
    suite_spec = SuiteSpec.model_validate({
        "id": "suite",
        "name": "Suite",
        "specs": [_spec("first")],
        "teardown": {"steps": [{"type": "press_key", "key": "Escape"}]},
    })

    suite = runner.run_suite(suite_spec, report_dir=tmp_path)

    assert suite.failed == 1
    assert lifecycle_calls == [1]


def test_run_suite_setup_failure_cancels_all_specs(tmp_path, monkeypatch):
    runner = WebSpecRunner(WebSpecConfig(base_url="http://example.test", report_dir=str(tmp_path)))
    runner._context = FakeContext()
    stopped = []
    monkeypatch.setattr(runner, "_start_browser", lambda: None)
    monkeypatch.setattr(runner, "_stop_browser", lambda: stopped.append(True))
    monkeypatch.setattr(runner, "_run_lifecycle_actions", lambda actions, execution: "setup failed")
    suite_spec = SuiteSpec.model_validate({
        "id": "suite",
        "name": "Suite",
        "setup": [{"type": "wait_for", "timeout_ms": 1}],
        "specs": [_spec("first"), _spec("second")],
    })

    suite = runner.run_suite(suite_spec, report_dir=tmp_path)

    assert suite.cancelled == 2
    assert suite.error == "suite setup failed: setup failed"
    assert stopped == [True]
    assert (tmp_path / "summary.json").exists()


def test_run_suite_teardown_resets_page_state(tmp_path, monkeypatch):
    runner = WebSpecRunner(WebSpecConfig(base_url="http://example.test", report_dir=str(tmp_path)))
    context = FakeContext()
    runner._context = context
    monkeypatch.setattr(runner, "_start_browser", lambda: None)
    monkeypatch.setattr(runner, "_stop_browser", lambda: None)
    monkeypatch.setattr(runner, "run_spec", lambda spec, report_root=None, spec_index=1, total_specs=1: RunRecord(
        spec_id=spec.id,
        spec_title=spec.title,
        report_dir=str(tmp_path / spec.id),
    ))
    suite_spec = SuiteSpec.model_validate({
        "id": "suite",
        "name": "Suite",
        "specs": [_spec("first")],
        "teardown": {"reset_page_state": True, "restore_entry_page": True},
    })

    runner.run_suite(suite_spec, report_dir=tmp_path)

    teardown_page = context.pages[-1]
    assert teardown_page.cookies_cleared is True
    assert teardown_page.urls == ["http://example.test/", "http://example.test/"]
