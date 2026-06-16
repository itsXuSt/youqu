# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.web_spec.reporter."""

import json

from web_spec.reporter import save_spec_report, save_suite_summary
from web_spec.result import ActionRecord, RunRecord, StepRecord, SuiteRecord


def test_save_spec_report(tmp_path):
    report_dir = tmp_path / "spec"
    record = RunRecord(spec_id="login", spec_title="登录测试", report_dir=str(report_dir))
    record.steps.append(StepRecord(order=1, description="点击", actions=[ActionRecord(type="click")]))
    record.finalize()

    save_spec_report(record)

    data = json.loads((report_dir / "report.json").read_text(encoding="utf-8"))
    assert data["spec_id"] == "login"
    assert data["status"] == "passed"
    assert (report_dir / "report.html").exists()


def test_save_suite_summary(tmp_path):
    suite = SuiteRecord(suite_id="smoke", suite_name="冒烟套件", module="认证", tags=["smoke"])
    record = RunRecord(spec_id="login", spec_title="登录测试", report_dir=str(tmp_path / "login"))
    record.finalize()
    suite.specs.append(record)
    suite.finalize()

    save_suite_summary(suite, tmp_path)

    data = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert data["suite_id"] == "smoke"
    assert data["suite_name"] == "冒烟套件"
    assert data["total"] == 1
    assert data["passed"] == 1
    assert (tmp_path / "summary.html").exists()
