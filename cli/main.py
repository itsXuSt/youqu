# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only

"""YouQu CLI entry point.

Registered as console_scripts: youqu = "youqu.cli.main:main"
"""

import argparse
import sys
from pathlib import Path

_YOUQU_PKG = Path(__file__).resolve().parent.parent

_INJECT_PATHS = (
    _YOUQU_PKG,
    _YOUQU_PKG / "src",
    _YOUQU_PKG / "setting",
    _YOUQU_PKG / "src" / "depends",
)


def _inject_paths():
    for p in _INJECT_PATHS:
        p_str = str(p)
        if p_str not in sys.path:
            sys.path.insert(0, p_str)


def main():
    _inject_paths()
    try:
        from importlib.metadata import version as _get_version
        _youqu_version = _get_version("youqu-framework")
    except Exception:
        _youqu_version = "unknown"

    parser = argparse.ArgumentParser(
        prog="youqu",
        description="YouQu test framework CLI",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {_youqu_version}"
    )
    sub = parser.add_subparsers(dest="command")

    # youqu make <name>
    p_make = sub.add_parser("make", help="Generate autotest/ skeleton")
    p_make.add_argument("name", help="App name (e.g. terminal)")
    p_make.add_argument("--dir", default=".", help="Output directory (default: CWD)")
    p_make.add_argument(
        "--format",
        default="yaml",
        choices=["yaml", "py", "all"],
        help="Skeleton format: yaml (default), py (Python only), all (both)",
    )

    # youqu run [pytest args...]
    p_run = sub.add_parser("run", help="Run tests from autotest/")
    p_run.add_argument("-a", "--app", default="", help="Override autotest path")

    # youqu report
    p_report = sub.add_parser("report", help="Generate Allure HTML report")
    p_report.add_argument("-a", "--app", default="", help="Override autotest path")
    p_report.add_argument(
        "--clean",
        action="store_true",
        help="Clean output directory before generating",
    )
    p_report.add_argument(
        "--serve",
        action="store_true",
        help="Serve report via HTTP after generation (dynamic port, 0.0.0.0)",
    )

    # youqu mcp
    p_mcp = sub.add_parser("mcp", help="Start MCP server")
    p_mcp.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse", "http"],
        help="Transport protocol (default: stdio)",
    )
    p_mcp.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    p_mcp.add_argument("--port", type=int, default=8000, help="HTTP port (default: 8000)")

    # youqu doctor
    sub.add_parser("doctor", help="Check and fix environment issues")

    # youqu index
    p_index = sub.add_parser("index", help="Manage YAML test index")
    p_index.add_argument("--rebuild", action="store_true", help="Rebuild index from YAML files")
    p_index.add_argument("--list", action="store_true", help="List test cases")
    p_index.add_argument("--app", default="", help="Filter by app")
    p_index.add_argument("--module", default="", help="Filter by module")
    p_index.add_argument("--tag", default="", help="Filter by tag (comma-separated)")

    # youqu web-spec
    p_web_spec = sub.add_parser("web-spec", help="Run and manage Web specs")
    web_spec_sub = p_web_spec.add_subparsers(dest="web_spec_command")

    p_web_run = web_spec_sub.add_parser("run", help="Run Web spec file or directory")
    p_web_run.add_argument("spec_path", help="Web spec file or directory")
    p_web_run.add_argument("--config", default=None, help="Web spec config path")
    p_web_run.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    p_web_run.add_argument("--report-dir", default=None, help="Report output directory")
    p_web_run.add_argument("--dry-run", action="store_true", help="Load and validate specs only")
    p_web_run.add_argument("--no-screenshot", action="store_true", help="Disable step screenshots")
    p_web_run.add_argument("--verbose", action="store_true", help="Show action and assertion details")

    p_web_list = web_spec_sub.add_parser("list", help="List Web specs")
    p_web_list.add_argument("spec_dir", help="Web spec directory")
    p_web_list.add_argument("--module", default="", help="Filter by module")
    p_web_list.add_argument("--feature", default="", help="Filter by feature")
    p_web_list.add_argument("--tag", default="", help="Filter by tag (comma-separated)")

    p_web_index = web_spec_sub.add_parser("index", help="Rebuild Web spec index")
    p_web_index.add_argument("spec_dir", help="Web spec directory")

    p_web_check = web_spec_sub.add_parser("check", help="Statically check Web specs")
    p_web_check.add_argument("spec_path", help="Web spec file or directory")

    # youqu startproject <name>
    p_sp = sub.add_parser("startproject", help="Create project from template")
    p_sp.add_argument("name", nargs="?", help="Project name (default: youqu)")

    # youqu inspect <app_path> [app_args...]
    p_inspect = sub.add_parser("inspect", help="Inspect app accessibility events (NDJSON output)")
    p_inspect.add_argument("app_path", help="Application executable path")
    p_inspect.add_argument("app_args", nargs="*", help="Arguments passed to application")

    args, extra = parser.parse_known_args()

    if args.command == "make":
        from youqu.cli.make import generate
        generate(args.name, args.dir, fmt=args.format)
    elif args.command == "run":
        from youqu.cli.run import run
        run(autotest_path=args.app or None, extra=extra)
    elif args.command == "report":
        from youqu.cli.report import run as report_run
        report_run(autotest_path=args.app or None, clean=args.clean, serve=args.serve)
    elif args.command == "mcp":
        from youqu.src.mcp.server import start as mcp_start
        mcp_start(transport=args.transport, port=args.port, host=args.host)
    elif args.command == "doctor":
        from youqu.cli.doctor import run as doctor_run
        doctor_run()
    elif args.command == "index":
        from youqu.cli.index import run as index_run
        index_run(args)
    elif args.command == "web-spec":
        from youqu.cli.web_spec import run as web_spec_run
        web_spec_run(args)
    elif args.command == "startproject":
        from youqu.src.startproject import cli
        cli()
    elif args.command == "inspect":
        try:
            from youqu.src.atspi_inspector import AtspiInspector
            inspector = AtspiInspector()
            inspector.inspect(args.app_path, args.app_args)
        except ImportError as e:
            print(f"AT-SPI inspector requires: sudo apt install at-spi2-core python3-pyatspi\n{e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
