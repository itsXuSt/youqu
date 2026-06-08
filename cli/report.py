# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only

from pathlib import Path

_DEFAULT_REPORT_DIR = "report"


def _find_autotest_dir(override=None):
    import sys

    if override:
        p = Path(override).resolve()
        if not p.exists():
            print(f"Error: {p} does not exist")
            sys.exit(1)
        return p

    cwd = Path.cwd()
    if (cwd / "autotest").is_dir():
        return cwd / "autotest"
    if (cwd / "case").is_dir() and (cwd / "pytest.ini").exists():
        return cwd
    if (cwd / "pytest.ini").exists() or (cwd / "report").is_dir():
        return cwd

    print("Error: No autotest/ directory found. Run 'youqu make <name>' first.")
    sys.exit(1)


def _find_port(start=8080, max_attempts=100):
    import socket
    for port in range(start, start + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("0.0.0.0", port)) != 0:
                return port
    return start


def _get_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def _serve_report(html_dir):
    import http.server
    import os

    os.chdir(str(html_dir))
    port = _find_port()
    addr = ("0.0.0.0", port)
    ip = _get_ip()
    print(f"http://{ip}:{port}")
    print("Press Ctrl+C to stop")
    http.server.HTTPServer(addr, http.server.SimpleHTTPRequestHandler).serve_forever()


def _generate_report(report_root, clean=False, serve=False):
    try:
        from allure_custom import AllureCustom
    except ImportError:
        return

    if not report_root.is_dir() or not list(report_root.iterdir()):
        return
    html_dir = report_root / "allure_html"
    try:
        AllureCustom.gen(str(report_root), str(html_dir), clean=clean)
        print(f"Report generated: {html_dir}")
    except Exception as e:
        print(f"Report generation failed: {e}")
        return

    if serve:
        _serve_report(html_dir)


def run(autotest_path=None, clean=False, serve=False):
    autotest = _find_autotest_dir(autotest_path)
    _generate_report(autotest / _DEFAULT_REPORT_DIR, clean=clean, serve=serve)
