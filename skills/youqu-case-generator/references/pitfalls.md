# Pitfalls — YouQu Case Generator

## P1: Sub-agents Must Not Modify Framework Source

**Root cause**: Sub-agents tend to "fix" import errors by editing source files.

**Manifestation**: Finding `src/dogtail_utils.py` or `src/assert_common.py` modified
after generation run.

**Prevention**: Every sub-agent prompt MUST include:
> MUST NOT DO: Modify framework source files (src/, setting/, conftest.py at project root)

**Recovery**: `git checkout src/ setting/ conftest.py pytest.ini`


## P2: AT-SPI Selectors Must Match Reality

**Root cause**: Sub-agents guess element names (e.g., "Btn_设置" when the real name is "Btn_settings").

**Manifestation**: Generated tests pass collection but fail at runtime with "element not found".

**Prevention**: Always pass AT-SPI tree results alongside case data. Sub-agents MUST use
only element names confirmed by `atspi_find_element` output.

**Recovery**: Re-run `atspi_find_element` for the failing element, update the widget method
with the correct name, then re-run the test.


## P3: File Name ID Must Match Method Name ID

**Root cause**: Sub-agents create `test_music_play_001.py` with method `test_music_play_002`.

**Manifestation**: Test silently skipped at collection time — no error, no warning.

**Prevention**: The sub-agent prompt must state this rule explicitly:
> File name ID == method name ID. Mismatched IDs cause silent skip.

**Recovery**: Fix the method name to match the file name's ID.


## P4: Non-Automatable Cases Need Files Too

**Root cause**: Sub-agents omit non-automatable cases entirely to "save time".

**Manifestation**: 100 source cases → only 80 generated files. 1:1 broken.

**Prevention**: Sub-agent prompt MUST state:
> Generate a .py file for EVERY case. Non-automatable cases → @pytest.mark.skip + pass.

**Recovery**: Cross-reference source case IDs against generated file IDs. Generate
missing files for any gaps.


## P5: Widget Method Granularity Matters

**Root cause**: Sub-agents create monolithic methods like `def run_full_workflow(self)`.

**Manifestation**: Widget methods that do 5+ operations, no composability, impossible
to reuse across test cases.

**Prevention**: Template the Widget method naming:
> Each method does ONE operation. click_play() + wait_playing() not click_and_verify_play().

**Recovery**: Refactor monolithic methods into atomic operations.


## P6: OCR/implicit Waits Need Padding

**Root cause**: Sub-agents chain actions without waits, expecting UI transitions to be instant.

**Manifestation**: Tests fail intermittently — element not found because dialog hasn't finished opening.

**Prevention**: Prompt includes:
> After any action that triggers a UI transition (dialog open, page switch, menu expand),
> add `time.sleep(0.5)` or use `self.wait_for_element()`.

```python
# WRONG
self.dog.element_click("Btn_设置")
self.dog.element_click("常规")  # might fail, dialog not open yet

# CORRECT
import time
self.dog.element_click("Btn_设置")
time.sleep(0.5)
self.dog.element_click("常规")
```

**Recovery**: Add explicit waits after every UI-triggering action.


## P7: startapp Modifies Templates

**Root cause**: Sub-agents regenerate Widget files that `startapp` already created.

**Manifestation**: Duplicate/conflicting files, or files missing `${VAR}` substitution.

**Prevention**: Always run `startapp` first (Step 2), then generate Widget/test files.
Never regenerate files that `startapp` already created (base_widget.py, base_case.py,
config.py, conftest.py).


## P8: CSV Must Reflect Generated Cases

**Root cause**: New test files exist but CSV doesn't have corresponding rows.

**Manifestation**: Framework's tag system doesn't apply to new cases (no skip, no PMS sync).

**Prevention**: After generation, run:
```bash
youqu manage.py csvctl --pyid2csv -a apps/autotest_<app>
```

**Recovery**: Run the csvctl command above. Then optionally run pmsctl to sync PMS IDs.


## P9: D-Bus Service Name vs App Name Confusion

**Root cause**: Sub-agents use D-Bus service names (com.deepin.Music) as app names for
window_focus or atspi_find_element.

**Manifestation**: `window_focus(app_name="com.deepin.Music")` fails.

**Prevention**: Document the distinction:
- `app_name` for MCP tools: the process/menu name (e.g., "deepin-music", "文件管理器")
- `service` for D-Bus: the D-Bus service name (e.g., "com.deepin.Music")
- These are NOT the same string. Use the process name for window/AT-SPI tools.


## P10: Batch Size and Memory

**Root cause**: Sub-agents process 50+ cases in one batch and hit context limits.

**Manifestation**: Generation truncates, incomplete files, or generic stubs for later cases.

**Prevention**: MAX 10 cases per batch. The export script enforces this.


## P11: Chinese Character Encoding in Error Messages

**Root cause**: `src/__init__.py` and other framework files use `# _*_ coding:utf-8 _*_`
header. Sub-agents writing files without this header may produce encoding issues.

**Prevention**: Template all generated .py files with the header:
```python
#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
```

**Recovery**: Add the encoding header to any files missing it.


## P12: config.UI_INI_PATH Must Exist

**Root cause**: Widget files reference `config.UI_INI_PATH` but the `ui.ini` file
is empty or doesn't exist.

**Manifestation**: `FileNotFoundError` or `NoSectionError` when Widget.__init__()
tries to load the config.

**Prevention**: Ensure `startapp` creates the `widget/ui.ini` file. If Widget
methods don't use ButtonCenter, remove the `config_path` parameter from
`Src.__init__()` call in `BaseWidget.__init__()`.

**Recovery**: Ensure `widget/ui.ini` exists or remove the `config_path` kwarg.
