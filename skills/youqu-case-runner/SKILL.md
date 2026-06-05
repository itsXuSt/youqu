---
name: youqu-case-runner
version: "0.1.0"
description: >
  Execute YouQu test cases via natural language. Translates intent to
  `manage.py run` CLI arguments and interprets test output.
  Triggers: 运行用例, 执行测试, 跑用例, run test cases,
  run L1 tests, run smoke tests, 运行所有用例.
---

# YouQu Case Runner

Execute YouQu Python test cases through natural language. This skill translates
user intent into `manage.py run` CLI invocations, runs tests, and summarizes
results. All execution goes through `manage.py run` — never raw `pytest`.

**Workflow context**: This skill works with `youqu-case-generator`. The generator
produces Python test files from xlsx/csv source documents + AT-SPI tree data.
This runner executes those generated test files.

---

## Step 0: Locate Framework and App Project

YouQu is installed as a Python package (`youqu-framework`). Two locations need
discovery:

- **Framework**: where `manage.py` lives — found via `pip show`
- **App project**: where `apps/`, `globalconfig.ini` live — user-provided or cwd

```bash
# Framework — find manage.py via pip
YOUQU_FRAMEWORK=$(pip show youqu-framework --format=json | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('Location',''))")
YOUQU_MANAGE="${YOUQU_FRAMEWORK}/manage.py"
[ -f "${YOUQU_FRAMEWORK}/manage.py" ] || YOUQU_MANAGE="${YOUQU_FRAMEWORK}/.."

# App project — convention: contains apps/ directory
if [ -d "$(pwd)/apps" ]; then
  YOUQU_APP_ROOT="$(pwd)"
fi
# Otherwise ask the user for their app project path
```

**Resolution order**: user-provided → `pip show` → cwd check → ask user.

---

## Step 1: Launch Test Application

**CRITICAL**: Before executing any test, the target application must be running
and its window must be in the foreground. Otherwise AT-SPI operations will
fail silently or operate on wrong elements, producing false results.

The application binary can be:
- System-installed (e.g. `/usr/bin/deepin-terminal`)
- Custom build (e.g. PR artifact: `/path/to/build/bin/deepin-terminal`)

**Actions**:
1. Ask user for the application binary path (if not already known)
2. Kill any existing instance to ensure clean state
3. Launch the application
4. Wait for window to appear
5. Verify the window is focused/foreground

```bash
# Example: launch deepin-terminal from a custom build
APP_BIN="/path/to/build/bin/deepin-terminal"

# Kill existing instance
pkill -f deepin-terminal || true
sleep 1

# Launch in background
nohup ${APP_BIN} &>/dev/null &
sleep 3  # Wait for window to appear

# Verify process is running
pgrep -f $(basename ${APP_BIN}) || echo "FAILED: app not running"

# Verify window is visible (via X11)
xdotool search --name "终端" || echo "FAILED: window not found"
```

**For Wayland**: Replace `xdotool` with `wlr-randr` or D-Bus Autotool for
window checks. The app project's `globalconfig.ini` `[basic] IS_WAYLAND` flag
determines the display server protocol.

**If the test suite covers multiple applications**: Each test case's Widget
method handles its own app launch. But the primary application should still be
pre-launched here for the first case to find its target.

---

## Step 2: Discover Available Tests

Before executing, understand what tests exist:

```bash
# List all APP projects
ls ${YOUQU_APP_ROOT}/apps/

# List test files in a specific app
ls ${YOUQU_APP_ROOT}/apps/autotest_deepin_music/case/test_*.py
```

Present available apps and test counts to the user before running.

---

## Step 3: Parse Intent → CLI

| User Intent | CLI Translation |
|-------------|----------------|
| "运行音乐所有用例" | `-a apps/autotest_deepin_music` |
| "运行音乐 L1 用例" | `-a apps/autotest_deepin_music -t L1` |
| "运行 music 的 test_play_005" | `-a apps/autotest_deepin_music -k test_music_play_005` |
| "运行所有 L1+L2" | `-t "L1 or L2"` |
| "包括跳过的" | `--noskip` |
| "忽略 fixed 标记" | `--ifixed yes` |
| "只跑上次失败的" | `--lastfailed` |
| "失败重跑2次" | `--reruns 2` |
| "用例文件列表" | `-f cases/list.txt` |
| "实时报错" | `--duringfail` |
| "重跑3次" | `--repeat 3` |

---

## Step 4: Build Command

**Base**: `python3 ${YOUQU_MANAGE} run`

| Flag | Config Key | Default | When to Include |
|------|-----------|---------|-----------------|
| `-a <path>` | `APP_NAME` | `""` (all) | Target specific app |
| `-k <keyword>` | `KEYWORDS` | `""` | Filter by nodeid substring |
| `-t <tags>` | `TAGS` | `""` | Tag expression (→ pytest `-m`) |
| `--noskip` | `NOSKIP` | `""` | Override skip marks |
| `--ifixed yes` | `IFIXED` | `""` | Fixed mark loses effect |
| `--reruns N` | `RERUN` | `1` | Retry count (0=disable) |
| `--max_fail N` | `MAX_FAIL` | `1` | Max failures before stopping |
| `--timeout N` | `CASE_TIME_OUT` | `1800` | Per-case timeout (seconds) |
| `--lastfailed` | — | `False` | Only run last-failed (→ `--lf`) |
| `--duringfail` | `DURING_FAIL` | `False` | Show errors immediately |
| `--repeat N` | `REPEAT` | `""` | Run each case N times |
| `-f <file>` | `CASE_FILE` | `""` | `.txt` file with one path per line |
| `--send_pms <mode>` | `SEND_PMS` | `""` | PMS backfill: `async`/`finish` |
| `--task_id <id>` | `TASK_ID` | `""` | PMS test suite ID |
| `--suite_id <id>` | `SUITE_ID` | `""` | PMS suite linkage |
| `--trigger <mode>` | `TRIGGER` | `auto` | PMS trigger: `auto`/`hand` |
| `--clean yes` | `CLEAN_ALL` | `yes` | Kill processes and clean env |

**Only include flags that differ from defaults.** Filters combine additively
(`-a`, `-k`, `-t`, `--noskip` can all be used together).

Tag filtering examples:
```
-t L1                      # single tag
-t "L1 or L2"              # logical OR
-t "L1 and smoke"          # logical AND
-t "not removed"           # negation
```

---

## Step 5: Execute

```bash
cd ${YOUQU_APP_ROOT} && python3 ${YOUQU_MANAGE} run [args...]
```

**What happens internally** (`manage.py` → `_cargo.py` → `LocalRunner`):
1. Parse CLI args, merge with `globalconfig.ini` (CLI takes precedence)
2. `change_working_dir()` → cd to app dir
3. `create_pytest_cmd()` → compose pytest command with `-k`, `-m` (tags), `--app_name`, etc.
4. `pytest.main()` → execute collected test cases
5. Post-test: Allure report + JSON summary to `report/`

---

## Step 6: Summarize Results

Parse stdout for:
- `collected N items / M deselected / K selected` → scope
- `X passed, Y failed, Z skipped in Ts` → final counts
- Individual FAILED lines → error details

Report format:
```
Total: 15 | Passed: 12 | Failed: 2 | Skipped: 1 | Time: 45.3s

Failed:
  - test_music_play_003: AssertionError (track duration mismatch)

Skipped:
  - test_music_gesture_010: skip-触摸操作无法自动化
```

Reports are also written to `report/` (allure/, json/, xml/, logs/).

---

## Pitfalls

1. **App not running = false failures**: AT-SPI operations on non-existent windows
   produce wrong results. ALWAYS launch and verify the app before running tests.

2. **DISPLAY required**: YouQu needs a running X/Wayland session. The machine must
   have a desktop environment.

3. **Tag vs keyword**: `-t L1` filters by pytest mark. `-k test_play_001` filters
   by nodeid substring. Different filters, can be combined.

4. **Long execution**: Full app suites can run for hours. Consider scope before running.

5. **RERUN=1 means 1 retry** → failed case runs twice total. `--reruns 0` disables.

6. **X11 vs Wayland**: Window verification commands differ. Check
   `globalconfig.ini [basic] IS_WAYLAND = true/false` to choose the right tool.
