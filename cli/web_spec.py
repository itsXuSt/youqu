# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
# SPDX-License-Identifier: GPL-2.0-only
"""Web spec CLI commands."""

from __future__ import annotations

import sys
from pathlib import Path


def run(args) -> None:
    """Dispatch youqu web-spec subcommands."""
    command = getattr(args, "web_spec_command", "")
    if command == "run":
        _run_specs(args)
    elif command == "list":
        _list_specs(args)
    elif command == "index":
        _index_specs(args)
    elif command == "check":
        _check_specs(args)
    else:
        print("Error: missing web-spec subcommand: run/list/index/check", file=sys.stderr)
        sys.exit(1)


def _run_specs(args) -> None:
    from web_spec.config import load_web_spec_config
    from web_spec.loader import SpecValidationError, load_specs
    from web_spec.reporter import print_suite_summary
    from web_spec.runner import WebSpecRunner
    from web_spec.tui import SpecProgressReporter

    try:
        specs = load_specs(args.spec_path)
    except (FileNotFoundError, SpecValidationError, ValueError) as exc:
        print(f"spec 加载失败: {exc}", file=sys.stderr)
        sys.exit(1)

    overrides = {
        "headless": False if args.headed else None,
        "report_dir": args.report_dir,
        "screenshot_on_step": False if args.no_screenshot else None,
    }
    try:
        config = load_web_spec_config(args.config, overrides=overrides)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Web spec 配置加载失败: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        for spec in specs:
            action_count = len(spec.setup) + sum(len(step.actions) for step in spec.steps)
            assertion_count = sum(len(step.assertions) for step in spec.steps)
            print(f"[DRY-RUN] {spec.id}: {spec.title}")
            print(
                f"  steps: {len(spec.steps)}, actions: {action_count}, "
                f"assertions: {assertion_count}"
            )
        print(f"\n共 {len(specs)} 个 spec")
        return

    reporter = SpecProgressReporter(verbose=getattr(args, "verbose", False))
    runner = WebSpecRunner(config, reporter=reporter)
    suite = runner.run_all(specs, report_dir=args.report_dir)
    print_suite_summary(suite)
    if suite.failed > 0 or suite.blocked > 0 or suite.cancelled > 0:
        sys.exit(1)


def _list_specs(args) -> None:
    from web_spec.index import WebSpecIndex

    spec_dir = Path(args.spec_dir)
    if not spec_dir.is_dir():
        print(f"Error: spec directory not found: {spec_dir}", file=sys.stderr)
        sys.exit(1)

    idx = WebSpecIndex(spec_dir)
    tags = [tag.strip() for tag in args.tag.split(",") if tag.strip()] if args.tag else None
    specs = idx.query(
        module=args.module or None,
        feature=args.feature or None,
        tags=tags,
    )
    if not specs:
        print("No specs found.")
        return

    print(f"Specs: {len(specs)}")
    for spec in specs:
        tags_str = ",".join(spec.get("tags", []) or [])
        module = spec.get("module", "") or "uncategorized"
        feature = f" ({spec['feature']})" if spec.get("feature") else ""
        print(f"  {spec['id']:30s} {module}{feature} [{tags_str}] {spec.get('name', '')}")

    stats = idx.get_stats()
    print(f"\nModules: {dict(stats.get('modules', {}))}")
    print(f"Tags: {dict(stats.get('tags', {}))}")


def _index_specs(args) -> None:
    from web_spec.index import WebSpecIndex

    spec_dir = Path(args.spec_dir)
    if not spec_dir.is_dir():
        print(f"Error: spec directory not found: {spec_dir}", file=sys.stderr)
        sys.exit(1)

    idx = WebSpecIndex(spec_dir)
    specs = idx.rebuild()
    print(f"Web spec index rebuilt: {len(specs)} spec(s) indexed.")
    stats = idx.get_stats()
    print(f"  Modules: {list(stats.get('modules', {}).keys())}")
    print(f"  Tags: {list(stats.get('tags', {}).keys())}")


def _check_specs(args) -> None:
    from web_spec.checker import check_specs

    try:
        report = check_specs(args.spec_path)
    except FileNotFoundError as exc:
        print(f"Web spec check 失败: {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Web spec check: checked={report.checked}, skipped={report.skipped}, "
        f"errors={report.errors}, warnings={report.warnings}"
    )
    for issue in report.issues:
        location = issue.file
        if issue.step is not None:
            location += f" step {issue.step}"
        if issue.item:
            location += f" {issue.item}"
        print(f"[{issue.severity}] {location}: {issue.message}")
        if issue.suggestion:
            print(f"  建议: {issue.suggestion}")

    if not report.ok:
        sys.exit(1)
