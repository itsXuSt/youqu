# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
# SPDX-License-Identifier: GPL-2.0-only
"""Web spec CLI commands."""

from __future__ import annotations

import sys
import time
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
    elif command == "init":
        _init_config(args)
    elif command == "suite":
        _run_suite(args)
    else:
        print("Error: missing web-spec subcommand: run/list/index/check/init/suite", file=sys.stderr)
        sys.exit(1)


def _run_specs(args) -> None:
    from web_spec.config import find_web_spec_config, load_web_spec_config
    from web_spec.loader import SpecValidationError
    from web_spec.reporter import print_suite_summary
    from web_spec.runner import WebSpecRunner
    from web_spec.tui import SpecProgressReporter

    try:
        suites, specs = _load_run_targets(args.spec_path)
    except (FileNotFoundError, SpecValidationError, ValueError) as exc:
        print(f"spec 加载失败: {exc}", file=sys.stderr)
        sys.exit(1)

    config_path = args.config or find_web_spec_config(args.spec_path)
    overrides = {
        "headless": False if args.headed else None,
        "report_dir": args.report_dir,
        "screenshot_on_step": False if args.no_screenshot else None,
    }
    try:
        config = load_web_spec_config(config_path, overrides=overrides)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Web spec 配置加载失败: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        for suite_spec in suites:
            _print_suite_dry_run(suite_spec)
        for spec in specs:
            _print_spec_dry_run(spec)
        total_specs = len(specs) + sum(len(_suite_report_specs(suite_spec)) for suite_spec in suites)
        if suites:
            print(f"\n共 {len(suites)} 个 suite, {total_specs} 个 spec")
        else:
            print(f"\n共 {total_specs} 个 spec")
        return

    reporter = SpecProgressReporter(verbose=getattr(args, "verbose", False))
    runner = WebSpecRunner(config, reporter=reporter)
    report_dir = args.report_dir or _timestamp_report_dir(config.report_dir)
    has_failure = False
    run_summaries = []
    for suite_spec in suites:
        suite = runner.run_suite(suite_spec, report_dir=report_dir)
        run_summaries.append(suite)
        print_suite_summary(suite)
        has_failure = has_failure or suite.failed > 0 or suite.blocked > 0 or suite.cancelled > 0
    if specs:
        suite = runner.run_all(specs, report_dir=report_dir)
        run_summaries.append(suite)
        print_suite_summary(suite)
        has_failure = has_failure or suite.failed > 0 or suite.blocked > 0 or suite.cancelled > 0
    if len(run_summaries) > 1:
        from web_spec.reporter import save_suite_summary
        from web_spec.result import SuiteRecord

        summary = SuiteRecord(suite_name="Web Spec Summary")
        summary.start_time = min(item.start_time for item in run_summaries)
        for item in run_summaries:
            summary.specs.extend(item.specs)
            if item.error:
                summary.error = item.error if not summary.error else f"{summary.error}; {item.error}"
        summary.finalize()
        save_suite_summary(summary, report_dir)
    if has_failure:
        sys.exit(1)


def _timestamp_report_dir(base: str | Path) -> Path:
    return Path(base) / time.strftime("%Y%m%d_%H%M%S")


def _suite_report_specs(suite_spec):
    if getattr(suite_spec, "single_case", False) and getattr(suite_spec, "source_specs", None):
        return suite_spec.source_specs
    return suite_spec.specs


def _load_run_targets(spec_path: str):
    from web_spec.kind import find_suite_file, is_suite_file
    from web_spec.loader import load_spec_dir, load_specs
    from web_spec.suite import load_suite

    root = Path(spec_path)
    if root.is_file():
        if is_suite_file(root):
            return [load_suite(root)], []
        return [], load_specs(root)

    suite_file = find_suite_file(root)
    if suite_file is not None:
        return [load_suite(suite_file)], []

    suites = [load_suite(path) for path in sorted(root.rglob("*.y*ml")) if is_suite_file(path)]
    referenced_sources = {
        Path(spec.source).resolve()
        for suite in suites
        for spec in suite.source_specs
        if spec.source
    }
    specs = [spec for spec in load_spec_dir(root) if not spec.source or Path(spec.source).resolve() not in referenced_sources]
    return suites, specs


def _print_spec_dry_run(spec) -> None:
    action_count = len(spec.setup) + sum(len(step.actions) for step in spec.steps)
    assertion_count = sum(len(step.assertions) for step in spec.steps)
    print(f"[DRY-RUN] {spec.id}: {spec.title}")
    print(
        f"  steps: {len(spec.steps)}, actions: {action_count}, "
        f"assertions: {assertion_count}"
    )


def _print_suite_dry_run(suite_spec) -> None:
    print(f"[DRY-RUN] suite {suite_spec.id}: {suite_spec.name}")
    print(
        f"  module: {suite_spec.module or 'uncategorized'}, "
        f"tags: {','.join(suite_spec.tags)}, fast_fail: {suite_spec.fast_fail}, "
        f"timeout: {suite_spec.timeout or '-'}"
    )
    for spec in _suite_report_specs(suite_spec):
        action_count = len(spec.setup) + sum(len(step.actions) for step in spec.steps)
        assertion_count = sum(len(step.assertions) for step in spec.steps)
        print(
            f"  - {spec.id}: {spec.title} "
            f"steps={len(spec.steps)}, actions={action_count}, assertions={assertion_count}"
        )


def _init_config(args) -> None:
    from web_spec.config import init_web_spec_config

    try:
        config_path = init_web_spec_config(args.config_path, force=args.force)
    except FileExistsError as exc:
        print(f"Web spec 配置初始化失败: {exc}", file=sys.stderr)
        print("  如需覆盖，请添加 --force。", file=sys.stderr)
        sys.exit(1)
    print(f"Web spec config created: {config_path}")



def _run_suite(args) -> None:
    from web_spec.config import find_web_spec_config, load_web_spec_config
    from web_spec.loader import SpecValidationError
    from web_spec.reporter import print_suite_summary
    from web_spec.runner import WebSpecRunner
    from web_spec.suite import load_suite
    from web_spec.tui import SpecProgressReporter

    try:
        suite_spec = load_suite(args.suite_path)
    except (FileNotFoundError, SpecValidationError, ValueError) as exc:
        print(f"suite 加载失败: {exc}", file=sys.stderr)
        sys.exit(1)

    config_path = args.config or find_web_spec_config(args.suite_path)
    overrides = {
        "headless": False if args.headed else None,
        "report_dir": args.report_dir,
        "screenshot_on_step": False if args.no_screenshot else None,
    }
    try:
        config = load_web_spec_config(config_path, overrides=overrides)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Web spec 配置加载失败: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        _print_suite_dry_run(suite_spec)
        print(f"\n共 {len(_suite_report_specs(suite_spec))} 个 spec")
        return

    reporter = SpecProgressReporter(verbose=getattr(args, "verbose", False))
    runner = WebSpecRunner(config, reporter=reporter)
    suite = runner.run_suite(suite_spec, report_dir=args.report_dir)
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

    visible_specs = _print_specs_tree(specs)

    stats = _spec_stats(visible_specs)
    print(f"\n📦 Modules: {dict(stats.get('modules', {}))}")
    print(f"🏷️  Tags: {dict(stats.get('tags', {}))}")


def _print_specs_tree(specs: list[dict]) -> list[dict]:
    suites = [spec for spec in specs if spec.get("kind") == "suite"]
    cases = [spec for spec in specs if spec.get("kind", "case") != "suite"]
    referenced = {
        file
        for suite in suites
        for file in [*(item.get("file") for item in suite.get("specs", []) if item.get("file")), *(suite.get("source_files", []) or [])]
    }
    standalone_cases = [case for case in cases if case.get("file") not in referenced]
    visible_case_count = len(standalone_cases) + sum(len(suite.get("specs", []) or []) for suite in suites)
    print(f"Web specs: {len(suites)} suite(s), {visible_case_count} case(s)")
    for suite in suites:
        tags = _format_tags(suite.get("tags"))
        module = suite.get("module") or "uncategorized"
        print(f"\n▣ {suite.get('id', '')}  {suite.get('name', '')}")
        print(f"  kind: suite    module: {module}    tags: {tags}    file: {suite.get('file', '')}")
        children = suite.get("specs", []) or []
        if suite.get("single_case"):
            print(f"  mode: single case, merged from {len(suite.get('source_files', []) or [])} file(s)")
        if not children:
            print("  └─ (empty)")
        for index, child in enumerate(children):
            branch = "└─" if index == len(children) - 1 else "├─"
            child_tags = _format_tags(child.get("tags"))
            child_module = child.get("module") or "uncategorized"
            print(
                f"  {branch} {child.get('id', '')}  {child.get('name', '')} "
                f"[{child_module}] {child_tags}"
            )
    if standalone_cases:
        print("\n▣ standalone cases")
        for index, case in enumerate(standalone_cases):
            branch = "└─" if index == len(standalone_cases) - 1 else "├─"
            tags = _format_tags(case.get("tags"))
            module = case.get("module") or "uncategorized"
            feature = f" / {case.get('feature')}" if case.get("feature") else ""
            print(f"  {branch} {case.get('id', '')}  {case.get('name', '')} [{module}{feature}] {tags}")
    visible_children = [child for suite in suites for child in suite.get("specs", []) or []]
    return suites + visible_children + standalone_cases


def _spec_stats(specs: list[dict]) -> dict:
    stats = {"modules": {}, "tags": {}}
    for spec in specs:
        module = spec.get("module", "")
        if module:
            stats["modules"][module] = stats["modules"].get(module, 0) + 1
        for tag in spec.get("tags", []) or []:
            stats["tags"][tag] = stats["tags"].get(tag, 0) + 1
    return stats


def _format_tags(tags) -> str:
    tags = tags or []
    return f"[{','.join(tags)}]" if tags else "[]"


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
        f"Web spec check: checked={report.checked}, cases={report.cases}, "
        f"suites={report.suites}, skipped={report.skipped}, "
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
