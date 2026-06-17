# YouQu Web Spec 后续开发方案

## 1. 背景

当前 YouQu 已经完成 `web_spec` 子系统的 MVP：

```text
YAML spec → loader 校验 → Playwright runner → action/assertion → screenshot → report → CLI/list/index
```

现有能力主要分布在：

```text
src/web_spec/
cli/web_spec.py
tests/test_web_spec_*.py
examples/web_spec/
```

当前实现已经可以承接 `uos-ai-test` 中结构化 YAML spec 的大部分基础用例，但距离真实项目长期使用仍存在缺口：

1. 高级 UI 动作不足；
2. 高级断言不足；
3. suite 级组织缺失；
4. MCP/job 化缺失；
5. 失败诊断能力不足；
6. 真实浏览器 E2E 测试覆盖不足；
7. 用户文档和迁移指南不足。

本文档给出后续可落地的开发计划。

## 2. 目标

### 2.1 短期目标

把当前 `web_spec` 从 MVP 提升到稳定可用版本，支持真实 Web 项目中常见的 UI 自动化场景。

重点包括：

- 完善常用 action；
- 完善常用 assertion；
- 增加真实 Playwright E2E 测试；
- 补齐 README/用户文档；
- 改善错误信息和迁移体验。

### 2.2 中期目标

支持更完整的项目级测试组织方式：

- suite 级执行；
- setup/teardown；
- 批量执行；
- 测试报告聚合；
- 失败分类；
- MCP job 化。

### 2.3 长期目标

把 `web_spec` 做成 YouQu 中与桌面 YAML 测试并列的一等自动化能力：

```text
desktop yaml spec
web spec
dbus/http/cli spec
MCP remote execution
统一报告与状态管理
```

## 3. 非目标

当前阶段不建议立即做以下事项：

1. 不立即迁移旧 Markdown 自然语言用例；
2. 不立即引入 AI 自动执行自然语言步骤；
3. 不立即重构整个 YouQu spec 生命周期；
4. 不立即做复杂视觉比对；
5. 不立即做分布式并发执行。

原因是当前最需要补的是确定性执行能力，而不是扩大系统复杂度。

## 4. 开发原则

### 4.1 保持确定性优先

`web_spec` 应保持 deterministic runner 的定位：

```text
明确 locator
明确 action
明确 assertion
明确 expected
明确 timeout
```

AI 分析可以作为辅助，但不应成为默认执行路径。

### 4.2 与现有桌面 YAML 解耦

`src/yaml_test/` 和 `src/web_spec/` 应继续保持独立，避免互相污染。

### 4.3 先补表达力，再补平台化

优先级应是：

```text
动作/断言能力 → E2E 验证 → suite → MCP/job → 失败分析
```

如果基础 action/assertion 不够，suite 和 MCP 只会放大问题。

### 4.4 错误信息要面向用例作者

错误信息应尽量告诉用户：

- 哪个 spec；
- 哪个 step；
- 哪个 action/assertion；
- 哪个 locator；
- 匹配 0 个还是多个；
- 建议如何修复。

## 5. 分阶段计划

## Phase 0：稳定 MVP

### 目标

确保当前 `web_spec` MVP 稳定、文档完整、示例可靠。

### 任务

#### 0.1 更新示例索引

当前 `WebSpecIndex` 已有索引版本控制，示例目录中的 `index.yaml` 应同步更新，避免每次 `list` 时自动改写示例文件。

涉及文件：

```text
examples/web_spec/specs/index.yaml
src/web_spec/index.py
```

验收标准：

```bash
youqu web-spec list examples/web_spec/specs
git diff examples/web_spec/specs/index.yaml
```

期望：

- `list` 正常；
- 示例 index 不被意外重写。

#### 0.2 明确 `list` 是否允许写索引

当前行为：

```text
youqu web-spec list <dir>
```

如果索引缺失或版本过旧，会自动 rebuild 并写入 `index.yaml`。

建议保留自动写入，但在文档中明确说明：

> `web-spec list` 会在索引缺失或版本过旧时自动重建 `index.yaml`。

原因是当前框架已有类似自动索引思路，保持简单更适合用户。

#### 0.3 补充 README 文档

建议新增章节：

```markdown
## Web Spec 自动化测试
### 安装依赖
### 配置文件
### Spec 文件结构
### Locator
### Action
### Assertion
### CLI 使用
### 报告输出
### 常见错误
```

涉及文件：

```text
README.md
examples/web_spec/web_spec.yaml
examples/web_spec/specs/*.yaml
```

验收标准：

用户仅看 README，可以完成：

```bash
pip install -e .[webui]
playwright install chromium
youqu web-spec run examples/web_spec/specs --config examples/web_spec/web_spec.yaml --dry-run
youqu web-spec list examples/web_spec/specs
```

#### 0.4 增加真实 Playwright E2E 测试

新增一个最小 HTML 测试页面，覆盖真实浏览器链路。

建议结构：

```text
tests/fixtures/web_spec_app/
  index.html
tests/test_web_spec_e2e.py
```

覆盖场景：

- 打开本地页面；
- 点击按钮；
- 输入文本；
- 断言文本；
- 生成 report；
- 生成 screenshot。

验收标准：

```bash
python -m pytest -c pytest-tests.ini tests/test_web_spec_e2e.py -m e2e
```

## Phase 1：补齐真实 UI 常用 Action

### 目标

支持真实 Web 项目中最常见的交互动作。

### 1.1 新增 `right_click`

Spec 示例：

```yaml
- type: right_click
  locator:
    strategy: bem_css
    value: ".message-item"
```

实现建议：

- 在 `ActionType` 中新增 `RIGHT_CLICK = "right_click"`；
- `action_executor.py` 中调用：

```python
locator.click(button="right", timeout=action.timeout_ms)
```

测试：

- mock locator 验证传入 `button="right"`；
- E2E 验证右键菜单出现。

### 1.2 新增 `dblclick`

Spec 示例：

```yaml
- type: dblclick
  locator:
    strategy: text
    value: "文件名.txt"
    exact: true
```

实现建议：

```python
locator.dblclick(timeout=action.timeout_ms)
```

### 1.3 新增 `drag_to`

Spec 示例：

```yaml
- type: drag_to
  locator:
    strategy: bem_css
    value: ".outline-section:nth-child(1)"
  target:
    strategy: bem_css
    value: ".outline-section:nth-child(3)"
```

需要调整模型：

```python
class ActionSpec(BaseModel):
    ...
    target: Optional[Locator] = None
```

实现建议：

```python
source.drag_to(target)
```

适用场景：

- 大纲拖拽排序；
- 列表拖拽；
- 卡片拖拽。

### 1.4 新增 `upload_file`

Spec 示例：

```yaml
- type: upload_file
  locator:
    strategy: css
    value: "input[type=file]"
  value: "/tmp/demo.png"
```

实现建议：

```python
locator.set_input_files(action.value)
```

### Phase 1 验收标准

新增 action 后，以下用例可以表达：

- 右键菜单；
- 双击打开；
- 拖拽排序；
- 上传附件。

测试要求：

```bash
python -m pytest -c pytest-tests.ini tests/test_web_spec_action_executor.py
python -m pytest -c pytest-tests.ini tests/test_web_spec_e2e.py -m e2e
```

## Phase 2：补齐真实 UI 常用 Assertion

### 目标

让 spec 可以表达输入框、属性、样式、顺序、URL 等真实页面状态。

### 2.1 新增 input value 断言

建议新增：

```text
input_value_equals
input_value_contains
```

Spec 示例：

```yaml
- type: input_value_equals
  locator:
    strategy: bem_css
    value: ".input-area__field"
  expected: "测试内容"
```

实现建议：

```python
actual = locator.input_value()
```

适用场景：

- 输入框内容校验；
- textarea 校验；
- 表单回填校验。

### 2.2 新增 attribute 断言

建议新增：

```text
attribute_equals
attribute_contains
```

Spec 示例：

```yaml
- type: attribute_equals
  locator:
    strategy: css
    value: "button.submit"
  attribute: "aria-disabled"
  expected: "true"
```

需要扩展 `AssertionSpec`：

```python
attribute: Optional[str] = None
```

实现建议：

```python
actual = locator.get_attribute(assertion.attribute)
```

### 2.3 新增 class/style 断言

建议新增：

```text
class_contains
style_equals
style_contains
```

Spec 示例：

```yaml
- type: class_contains
  locator:
    strategy: bem_css
    value: ".theme-root"
  expected: "dark"
```

CSS style 示例：

```yaml
- type: style_equals
  locator:
    strategy: bem_css
    value: ".sidebar"
  property: "display"
  expected: "flex"
```

需要扩展：

```python
property: Optional[str] = None
```

实现建议：

```python
actual = locator.evaluate(
    "(el, prop) => getComputedStyle(el).getPropertyValue(prop)",
    prop,
)
```

### 2.4 新增 URL 断言

建议新增：

```text
url_contains
url_equals
```

Spec 示例：

```yaml
- type: url_contains
  expected: "/chat"
```

适用场景：

- 页面跳转；
- 登录后 redirect；
- 路由校验。

### 2.5 新增文本序列断言

建议新增：

```text
text_sequence
```

Spec 示例：

```yaml
- type: text_sequence
  locator:
    strategy: bem_css
    value: ".assistant-item"
  expected:
    - "帮我写作"
    - "帮我翻译"
    - "帮我总结"
```

语义：

- 获取所有匹配元素的文本；
- 断言 expected 中的文本按顺序出现；
- 可配置是否要求完全一致。

可先实现简单版本：

```text
actual_texts == expected
```

后续再加：

```yaml
mode: contains_order
```

### Phase 2 验收标准

以下场景可直接表达：

- placeholder；
- input value；
- disabled attribute；
- class 切换；
- style 改变；
- URL 路由；
- 列表顺序。

## Phase 3：迁移兼容和质量检查

### 目标

降低 `uos-ai-test` 结构化 YAML spec 迁移到 YouQu 的成本。

### 3.1 新增 spec lint/check 命令

建议 CLI：

```bash
youqu web-spec check specs/
```

检查内容：

1. YAML 是否能加载；
2. action 类型是否支持；
3. assertion 类型是否支持；
4. locator 是否缺少 strategy/value；
5. `text/css` locator 是否可能过宽；
6. 长等待 action 是否缺 timeout；
7. `wait_for` 是否缺 locator 且 timeout 过长；
8. 是否存在旧字段；
9. 是否存在高风险 selector：

```text
:nth-child
:last-child
div > div > div
```

输出示例：

```text
[WARN] specs/ai-writing.yaml step 4 action 1:
  selector ".outline-section:nth-child(1)" 较脆弱，建议使用 test_id 或更稳定 class

[WARN] specs/menu.yaml step 2 action 1:
  text locator "删除" 可能多匹配，建议加 exact/first 或改用更精确 locator
```

### 3.2 增强 locator 错误信息

当前多匹配已经会报错，但可以增强为：

```text
Locator matched multiple elements.

spec: specs/menu.yaml
step: 2 标题栏菜单交互验证
action: click
locator:
  strategy: text
  value: 删除
  exact: true

matched_count: 3

建议：
1. 使用更精确的 selector；
2. 或设置 locator.first: true；
3. 或改用 role/test_id。
```

### 3.3 dry-run 增强

当前 dry-run 只输出数量，建议增加：

```bash
youqu web-spec run specs --dry-run --verbose
```

输出：

```text
spec: 01.侧边栏布局验证
  actions:
    click: 1
    input_text: 1
  assertions:
    visible: 3
    text_contains: 2
  unsupported: 0
```

### Phase 3 验收标准

对从 `uos-ai-test` 迁移来的 spec 目录执行：

```bash
youqu web-spec check specs/
```

可以在不启动浏览器的情况下发现大部分 schema 和兼容性问题。

## Phase 4：Suite 层能力

### 目标

支持项目级测试组织，不再只是“目录递归跑所有 YAML”。

### 4.1 新增 suite.yaml

建议结构：

```yaml
id: ai-writing-suite
name: AI 写作流程测试
module: AI 写作
tags: [e2e, writing]
timeout: 1500
fast_fail: true

setup:
  - type: click
    locator:
      strategy: text
      value: 新会话
      exact: true

specs:
  - 01.模板输入框校验.yaml
  - 02.大纲生成校验.yaml
  - 03.大纲编辑校验.yaml
  - 04.大纲拖拽排序校验.yaml

teardown:
  - type: press_key
    key: Escape
```

### 4.2 新增 suite runner

新增模块建议：

```text
src/web_spec/suite.py
src/web_spec/suite_runner.py
```

执行流程：

```text
load suite.yaml
load suite setup
按顺序 load specs
执行 suite setup
执行 spec 1
执行 spec 2
...
执行 suite teardown
输出 suite report
```

### 4.3 CLI 支持

新增：

```bash
youqu web-spec suite path/to/suite.yaml
youqu web-spec suite path/to/suite.yaml --dry-run
youqu web-spec suite path/to/suite.yaml --headed
```

建议单独加 `suite` 子命令，避免和普通 spec 混淆。

### Phase 4 验收标准

可以表达：

```text
suite setup → 多个 spec 顺序执行 → 任一失败 fast-fail → teardown 必执行 → suite report
```

## Phase 5：MCP/job 化

### 目标

让 Web spec 能被 MCP 客户端远程调用，支持批量运行、状态查询和取消。

### 5.1 MCP 工具设计

建议新增工具：

```text
web_spec_list
web_spec_run_batch
web_spec_get_status
web_spec_cancel
```

### 5.2 工具行为

#### web_spec_list

输入：

```json
{
  "spec_dir": "examples/web_spec/specs",
  "module": "聊天区",
  "tags": ["smoke"]
}
```

输出：

```json
{
  "total": 3,
  "specs": [
    {
      "id": "03.聊天输入区交互验证",
      "file": "03.聊天输入区交互验证.yaml",
      "module": "聊天区",
      "tags": []
    }
  ]
}
```

#### web_spec_run_batch

输入：

```json
{
  "spec_dir": "examples/web_spec/specs",
  "module": "聊天区",
  "headed": false,
  "report_dir": "report/web_spec"
}
```

输出：

```json
{
  "job_id": "web-spec-20260615-001",
  "status": "running"
}
```

#### web_spec_get_status

输出：

```json
{
  "job_id": "web-spec-20260615-001",
  "status": "running",
  "passed": 3,
  "failed": 1,
  "blocked": 0,
  "report_dir": "report/web_spec/..."
}
```

#### web_spec_cancel

输入：

```json
{
  "job_id": "web-spec-20260615-001"
}
```

输出：

```json
{
  "cancelled": true
}
```

### 5.3 Runner 支持 cancel token

需要给 `WebSpecRunner` 增加取消检查：

```python
class WebSpecRunner:
    def __init__(..., cancel_event=None):
        self.cancel_event = cancel_event

    def _check_cancelled(self):
        if self.cancel_event and self.cancel_event.is_set():
            raise RunCancelled()
```

检查点：

- spec 开始前；
- step 开始前；
- action 前；
- assertion 前；
- teardown 前。

### Phase 5 验收标准

MCP 可以：

- 启动 Web spec 批量任务；
- 查询进度；
- 获取报告路径；
- 取消任务；
- 并正确标记 `cancelled`。

## Phase 6：失败诊断

### 目标

提升失败可读性，帮助区分：

```text
环境问题
产品问题
脚本问题
定位问题
超时问题
```

### 6.1 先做规则型分类

建议新增模块：

```text
src/web_spec/failure_classifier.py
```

分类规则：

| 失败类型 | 分类 |
|---|---|
| Playwright 未安装 | `blocked_env` |
| 浏览器启动失败 | `blocked_env` |
| locator 匹配 0 个 | `script_locator_not_found` 或 `product_element_missing` |
| locator 匹配多个 | `script_locator_ambiguous` |
| action timeout | `product_or_env_timeout` |
| assertion actual != expected | `product_assertion_mismatch` |
| YAML 解析失败 | `script_spec_invalid` |

输出结构：

```json
{
  "category": "script_locator_ambiguous",
  "message": "locator 匹配多个元素",
  "suggestion": "请使用更精确 selector，或设置 locator.first: true"
}
```

### 6.2 报告中展示诊断

报告中增加：

```json
{
  "failure": {
    "category": "...",
    "message": "...",
    "suggestion": "..."
  }
}
```

HTML 报告显示：

```text
失败分类：定位器多匹配
建议：使用更精确 locator 或设置 first: true
```

### 6.3 可选 AI 分析

后续可以增加：

```bash
youqu web-spec run specs --ai-analyze
```

但 AI 分析应作为可选能力，不影响默认 deterministic runner。

## 6. 测试策略

### 6.1 单元测试

每新增一个 action/assertion，都必须有单元测试：

```text
tests/test_web_spec_action_executor.py
tests/test_web_spec_assertion_executor.py
tests/test_web_spec_models.py
tests/test_web_spec_loader.py
```

### 6.2 集成测试

重点覆盖：

```text
loader + runner + reporter
CLI + dry-run
CLI + run
index + list
suite runner
MCP job
```

### 6.3 E2E 测试

使用本地静态 HTML，避免依赖外部服务。

建议测试页面包含：

- button；
- input；
- textarea；
- select；
- right-click menu；
- draggable list；
- theme class；
- route/hash；
- hidden/visible element。

### 6.4 测试命令

常规测试：

```bash
python -m pytest -c pytest-tests.ini tests/test_web_spec_*.py
```

跳过真实浏览器：

```bash
python -m pytest -c pytest-tests.ini tests/ -m "not e2e"
```

真实浏览器 E2E：

```bash
python -m pytest -c pytest-tests.ini tests/test_web_spec_e2e.py -m e2e
```

## 7. 建议实施顺序

推荐按以下顺序推进：

```text
第 1 轮：Phase 0
第 2 轮：Phase 1 + Phase 2 中最高频断言
第 3 轮：Phase 3
第 4 轮：Phase 4
第 5 轮：Phase 5
第 6 轮：Phase 6
```

具体拆分：

### 迭代一：稳定化

- 更新示例 index；
- 补 README；
- 增加真实 E2E；
- 明确 `list` 自动写索引行为。

预计工作量：1–2 天。

### 迭代二：补动作

- `right_click`
- `dblclick`
- `drag_to`
- `upload_file`

预计工作量：2–3 天。

### 迭代三：补断言

- `input_value_equals`
- `input_value_contains`
- `attribute_equals`
- `attribute_contains`
- `class_contains`
- `style_equals`
- `url_contains`
- `text_sequence`

预计工作量：3–5 天。

### 迭代四：迁移检查

- `youqu web-spec check`
- dry-run verbose 增强；
- locator 错误信息增强。

预计工作量：2–4 天。

### 迭代五：suite

- suite model；
- suite loader；
- suite runner；
- suite CLI；
- suite report。

预计工作量：4–7 天。

### 迭代六：MCP/job

- MCP tools；
- job manager 对接；
- cancel token；
- 状态查询；
- 报告路径返回。

预计工作量：4–7 天。

### 迭代七：失败诊断

- 规则分类；
- 报告展示；
- 可选 AI 分析接口预留。

预计工作量：3–5 天。

## 8. 推荐优先落地的最小任务包

如果只选一个近期最有价值的任务包，建议做：

```text
Phase 0 + Phase 1 部分 + Phase 2 部分
```

即：

1. 补 README；
2. 加真实 Playwright E2E；
3. 新增 `right_click`；
4. 新增 `drag_to`；
5. 新增 `input_value_equals`；
6. 新增 `attribute_equals`；
7. 新增 `text_sequence`；
8. 增强 locator 错误信息。

这组改完后，`web_spec` 对真实项目的覆盖度会明显提升。

## 9. 风险与应对

### 风险 1：action/assertion 越加越多，模型变臃肿

应对：

- 保持 action/assertion 简洁；
- 不要过早支持任意 JS；
- 高级需求先用明确枚举表达；
- 必要时再设计插件扩展。

### 风险 2：suite runner 和普通 runner 重复逻辑

应对：

- suite runner 只负责编排；
- 单个 spec 仍调用 `WebSpecRunner.run_spec()`；
- 不复制 action/assertion 执行逻辑。

### 风险 3：MCP job 和 CLI 行为不一致

应对：

- CLI 和 MCP 共用同一 runner；
- 运行配置统一通过 `WebSpecConfig`；
- 报告结构统一用 `RunRecord/SuiteRecord`。

### 风险 4：真实浏览器 E2E 不稳定

应对：

- 使用本地静态页面；
- 避免外部网络；
- 控制 timeout；
- e2e 标记默认可跳过；
- CI 中单独配置浏览器依赖。

## 10. 最终验收标准

当以下能力都满足时，可以认为 `web_spec` 达到真实项目可用状态：

1. 可以运行结构化 YAML spec；
2. 支持常见 Web UI 动作；
3. 支持常见 DOM/UI 状态断言；
4. 支持真实浏览器 E2E；
5. 支持 spec list/index/check；
6. 支持 suite 顺序执行；
7. 支持报告聚合；
8. 支持 MCP job 执行；
9. 支持取消任务；
10. 失败报告能明确区分定位问题、断言问题、环境问题；
11. README 足够让新用户独立上手。

## 11. 总结

当前 YouQu `web_spec` 已具备清晰主干，后续不应推倒重来，而应沿着当前结构继续增强：

```text
models.py
loader.py
action_executor.py
assertion_executor.py
runner.py
reporter.py
index.py
cli/web_spec.py
```

推荐路线是：

```text
稳定 MVP
→ 补动作和断言
→ 增加迁移检查
→ 支持 suite
→ 接入 MCP/job
→ 增强失败诊断
```

这样能最大化复用现有实现，同时逐步对齐 `uos-ai-test` 真实项目需求。
