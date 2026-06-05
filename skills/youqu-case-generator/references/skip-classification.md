# Skip Classification Rules

Every source case must produce a Python file. Non-automatable cases get
`@pytest.mark.skip(reason="...")`, never omitted.

## Automatic Classification

### Category 1: Touch/Gesture

```python
SKIP_GESTURE = "skip-触摸操作无法自动化"
```

Detection: steps or title contain any of:
- `触摸`, `touch`, `手势`, `gesture`, `pinch`, `swipe`, `多点触控`
- `手势缩放`, `双指缩放`, `长按拖动`

Example:
```python
@pytest.mark.skip(reason="skip-触摸操作无法自动化")
def test_gesture_zoom_007(self):
    """手势缩放图片 — 触摸操作无法自动化"""
    pass
```

### Category 2: Performance/Benchmark

```python
SKIP_PERF = "skip-性能压测类不支持自动化"
```

Detection: priority contains `性能` or `压测`, or title/steps contain any of:
- `性能`, `performance`, `压测`, `压力测试`, `并发`, `benchmark`
- `极限`, `高频`, `持续运行`, `负载`

### Category 3: Hardware/Environment Dependency

```python
SKIP_ENV = "skip-依赖特定硬件环境"
```

Detection: steps or precondition contain any of:
- `需要U盘`, `插入USB`, `需要打印机`, `需要蓝牙设备`, `需要耳机`
- `需要外接显示器`, `需要特定硬件`, `需要读卡器`
- `需要扫描仪`, `需要摄像头`, `需要麦克风`

### Category 4: Linglong

```python
SKIP_LINGLONG = "skip-玲珑环境不支持自动化"
```

Detection: title/case_type contains `玲珑` or `linglong`.

### Category 5: System Reboot

```python
SKIP_REBOOT = "skip-重启类场景需要letmego支持"
```

Reboot operation requires letmego framework extension.
Detection: steps contain `重启`, `reboot`, `重启后`, `重启系统`, `注销`.

### Category 6: External App Interaction

```python
SKIP_EXTERNAL = "skip-外部应用交互无法验证"
```

Detection: steps mention operations on apps outside the test target:
- `调用外部应用`, `打开第三方`, `外部程序`
- `跳转到其他应用`, `唤起其他APP`

### Category 7: Manual/Subjective Verification

```python
SKIP_MANUAL = "skip-需要人工主观判断"
```

Detection: expected or steps contain any of:
- `人工确认`, `肉眼观察`, `主观判断`, `听感`
- `视觉效果判断`, `感官`, `主观感受`, `音质`

## Manual Classification (Flag for Review)

These categories cannot be decided automatically. Flag them for human review:

### Multi-machine Interaction

```python
SKIP_MULTIMACHINE = "skip-多机交互待评估"
```

Detection: steps contain `多机`, `协同`, `投屏`, `远程`.
Some multi-machine scenarios are automatable (e.g., D-Bus remote calls).

### Pure Network Dependency

```python
SKIP_NETWORK = "skip-纯网络依赖待评估"
```

Detection: all test actions depend on network services. Flag, don't auto-skip:
some network scenarios can be mocked or tested locally.

### GPU/Rendering Verification

```python
SKIP_GPU = "skip-GPU渲染待评估"
```

Detection: expected mentions `渲染效果`, `GPU`, `显卡`, `3D`, `硬件加速`.
Sometimes screenshot-based verification is sufficient.

## Priority Override Table

When multiple categories match, use the highest priority skip reason:

| Priority | Category | Skip Reason |
|----------|----------|-------------|
| 1 | Linglong | skip-玲珑环境不支持自动化 |
| 2 | Performance | skip-性能压测类不支持自动化 |
| 3 | Touch | skip-触摸操作无法自动化 |
| 4 | Reboot | skip-重启类场景需要letmego支持 |
| 5 | Hardware | skip-依赖特定硬件环境 |
| 6 | External | skip-外部应用交互无法验证 |
| 7 | Manual | skip-需要人工主观判断 |
| 8* | Multi-machine | skip-多机交互待评估 |
| 9* | Network | skip-纯网络依赖待评估 |
| 10* | GPU | skip-GPU渲染待评估 |

*Priority 8-10: flagged for manual review, not auto-skipped.

## CSV Label Integration

Skip reasons in `@pytest.mark.skip(reason="...")` should match the CSV skip
column format. After generating test files, manually update the CSV or run:

```bash
python3 ${YOUQU_MANAGE} csvctl --pyid2csv -a apps/autotest_<app>
```
