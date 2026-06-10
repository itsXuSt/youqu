#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AT-SPI Inspector - 实时监控应用的无障碍事件并输出 NDJSON

用法:
    from src.atspi_inspector import AtspiInspector
    inspector = AtspiInspector()
    inspector.inspect("/usr/bin/deepin-music")

输出格式 (NDJSON):
    {"type":"app_start","timestamp":"2025-06-09T10:30:00.123Z","app":"deepin-music","pid":12345}
    {"type":"event","ts":"2025-06-09T10:30:01.456Z","role":"push button","name":"播放","event":"focus",...}
"""
import os
import sys
import json
import time
import signal
import subprocess
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

try:
    import gi
    gi.require_version('Atspi', '2.0')
    from gi.repository import Atspi, GLib
    ATSPI_AVAILABLE = True
except ImportError:
    ATSPI_AVAILABLE = False


# 监听的事件类型
EVENT_TYPES = [
    "window:activate",
    "window:deactivate",
    "window:create",
    "window:destroy",
    "object:state-changed:focused",
    "object:state-changed:checked",
    "object:state-changed:pressed",
    "object:state-changed:selected",
    "object:state-changed:showing",
    "object:state-changed:expanded",
    "object:state-changed:sensitive",
    "object:children-changed",
]

# 需要输出结构快照的容器类型
_STRUCTURE_ROLES = {"dialog", "frame", "window", "menu", "popup menu", "panel"}

# AT-SPI 状态名称映射
_STATE_NAMES = {}
if ATSPI_AVAILABLE:
    for attr in dir(Atspi.StateType):
        if attr.isupper():
            try:
                val = getattr(Atspi.StateType, attr)
                if isinstance(val, int):
                    _STATE_NAMES[val] = attr
            except Exception:
                pass


class AtspiInspector:
    """AT-SPI 检查器 - 实时监控应用事件并输出 NDJSON"""
    
    def __init__(self):
        if not ATSPI_AVAILABLE:
            raise ImportError(
                "AT-SPI not available. Run: youqu doctor\n"
                "This is a core framework dependency for desktop UI automation."
            )
        
        self._process: Optional[subprocess.Popen] = None
        self._listener: Optional[Atspi.EventListener] = None
        self._event_count = 0
        self._last_events: Dict[str, float] = {}  # 去重缓存
        self._debounce_ms = 200  # 去重时间窗
    
    def inspect(self, app_path: str, app_args: Optional[List[str]] = None):
        """
        启动应用并监听 AT-SPI 事件，实时输出 NDJSON
        
        参数:
            app_path: 应用可执行文件路径
            app_args: 传递给应用的参数列表
        
        行为:
            1. 启动应用 (设置 QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1)
            2. 注册 AT-SPI 事件监听器
            3. 实时输出 NDJSON 到 stdout
            4. 应用退出时停止监听并退出
        """
        app_path = os.path.abspath(app_path)
        if not os.path.isfile(app_path):
            self._error(f"应用不存在: {app_path}")
            return
        
        # 启动应用
        self._launch_app(app_path, app_args or [])
        
        # 设置信号处理 - 应用退出时清理
        signal.signal(signal.SIGTERM, self._on_signal)
        signal.signal(signal.SIGINT, self._on_signal)
        
        # 注册应用退出监控
        GLib.timeout_add(500, self._check_app_alive)
        
        # 启动事件监听
        self._start_monitoring()
    
    def _launch_app(self, app_path: str, app_args: List[str]):
        """启动应用"""
        env = os.environ.copy()
        env["QT_LINUX_ACCESSIBILITY_ALWAYS_ON"] = "1"
        
        self._process = subprocess.Popen(
            [app_path] + app_args,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        
        app_name = os.path.basename(app_path)
        
        # 输出应用启动事件
        self._output({
            "type": "app_start",
            "timestamp": self._timestamp(),
            "app": app_name,
            "pid": self._process.pid,
        })
    
    def _start_monitoring(self):
        """启动 AT-SPI 事件监听"""
        # 等待应用出现在 AT-SPI 树中
        time.sleep(2)
        
        # 注册事件监听器
        self._listener = Atspi.EventListener.new(self._on_event)
        
        for event_type in EVENT_TYPES:
            try:
                Atspi.EventListener.register(self._listener, event_type)
            except Exception as e:
                self._error(f"注册事件监听器失败 [{event_type}]: {e}")
        
        # 启动事件循环
        try:
            Atspi.event_main()
        except Exception as e:
            self._error(f"事件循环异常: {e}")
        finally:
            self._cleanup()
    
    def _on_event(self, event):
        """事件回调 - 过滤、去重、输出"""
        try:
            # 噪声过滤
            if self._is_noise(event):
                return
            
            # 去重检查
            if self._is_duplicate(event):
                return
            
            # 提取事件数据
            event_data = self._extract_event_data(event)
            if event_data:
                self._output(event_data)
                self._event_count += 1
        
        except Exception as e:
            # 单个事件处理失败不影响继续监听
            pass
    
    def _is_noise(self, event) -> bool:
        """判断是否为噪声事件"""
        try:
            # sensitive 状态变化通常是 UI 更新的副效应，对操作路径无价值
            if event.type == "object:state-changed:sensitive":
                return True
            
            # 失去焦点不关心
            if event.type == "object:state-changed:focused" and event.detail1 == 0:
                return True
            
            # 控件隐藏通常是对话框关闭的副效应
            if event.type == "object:state-changed:showing" and event.detail1 == 0:
                return True
            
            # enabled 冗余 (sensitive 已覆盖)
            if event.type == "object:state-changed:enabled":
                return True
            
            # selection-changed 冗余 (单个控件的 selected 更精确)
            if event.type == "object:selection-changed":
                return True
            
            # 无 source 的事件无法定位
            if event.source is None:
                return True
        
        except Exception:
            pass
        
        return False
    
    def _is_duplicate(self, event) -> bool:
        """去重检查"""
        try:
            # 生成稳定标识
            src = event.source
            parent = src.get_parent()
            parent_name = parent.get_name() if parent else ""
            key = f"{parent_name}/{src.get_role_name()}/{src.get_name()}:{event.type}"
            
            # 检查时间窗
            now = time.time()
            last = self._last_events.get(key)
            if last and (now - last) * 1000 < self._debounce_ms:
                return True
            
            self._last_events[key] = now
            return False
        
        except Exception:
            return False
    
    def _extract_event_data(self, event) -> Optional[Dict[str, Any]]:
        """提取事件数据为字典"""
        try:
            src = event.source
            if not src:
                return None
            
            role = src.get_role_name() or "unknown"
            name = self._truncate_name(src.get_name() or "")
            event_type = self._simplify_event_type(event.type)
            
            if event_type == "showing" and event.detail1 == 1 and role in _STRUCTURE_ROLES:
                return self._build_structure_snapshot(src, role, name)
            
            data = {
                "type": "event",
                "ts": self._timestamp(),
                "role": role,
                "name": name,
                "event": event_type,
                "detail1": event.detail1,
            }
            
            data["parent"] = self._get_parent_path(src)
            
            states = self._get_states(src)
            if states:
                data["states"] = states
            
            return data
        
        except Exception:
            return None
    
    def _get_parent_path(self, obj, max_depth=5) -> str:
        """获取父容器路径（如 "主窗口/toolbar"）"""
        parts = []
        current = obj
        
        try:
            for _ in range(max_depth):
                parent = current.get_parent()
                if not parent:
                    break
                
                name = parent.get_name() or ""
                role = parent.get_role_name() or ""
                
                # 跳过 application 和 desktop 层级
                if role in ("application", "desktop frame"):
                    break
                
                if name:
                    parts.insert(0, name)
                
                current = parent
        
        except Exception:
            pass
        
        return "/".join(parts) if parts else ""
    
    def _get_states(self, obj) -> List[str]:
        """获取控件状态列表"""
        states = []
        try:
            state_set = obj.get_state()
            for state_val, state_name in _STATE_NAMES.items():
                try:
                    if state_set.contains(state_val):
                        states.append(state_name)
                except Exception:
                    pass
        except Exception:
            pass
        return states
    
    def _simplify_event_type(self, event_type: str) -> str:
        """简化事件类型（如 object:state-changed:focused -> focused）"""
        parts = event_type.split(":")
        if len(parts) >= 3 and parts[0] == "object" and parts[1] == "state-changed":
            return parts[2]  # 返回状态名: focused, showing, checked...
        if len(parts) >= 2:
            return parts[1]  # 返回主要类型: activate, create...
        return event_type
    
    def _truncate_name(self, name: str, max_len: int = 100) -> str:
        """截断过长的名称"""
        if len(name) > max_len:
            return name[:max_len] + "..."
        return name
    
    def _build_structure_snapshot(self, container, role: str, name: str) -> Dict[str, Any]:
        children = self._enumerate_children(container, max_depth=2)
        
        return {
            "type": "structure",
            "ts": self._timestamp(),
            "role": role,
            "name": name,
            "children": children,
        }
    
    def _enumerate_children(self, obj, max_depth: int = 2, current_depth: int = 0) -> List[Dict[str, Any]]:
        if current_depth >= max_depth:
            return []
        
        children = []
        try:
            child_count = obj.get_child_count()
            for i in range(min(child_count, 50)):  # 防止遍历过深导致性能问题
                try:
                    child = obj.get_child_at_index(i)
                    if not child:
                        continue
                    
                    child_role = child.get_role_name() or "unknown"
                    child_name = self._truncate_name(child.get_name() or "")
                    
                    child_data = {
                        "role": child_role,
                        "name": child_name,
                    }
                    
                    if child.get_child_count() > 0:
                        sub_children = self._enumerate_children(child, max_depth, current_depth + 1)
                        if sub_children:
                            child_data["children"] = sub_children
                    
                    children.append(child_data)
                
                except Exception:
                    continue
        
        except Exception:
            pass
        
        return children
    
    def _timestamp(self) -> str:
        """生成 ISO 8601 时间戳"""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{datetime.now().microsecond // 1000:03d}Z"
    
    def _output(self, data: Dict[str, Any]):
        """输出 NDJSON 到 stdout"""
        try:
            print(json.dumps(data, ensure_ascii=False), flush=True)
        except Exception:
            pass
    
    def _error(self, message: str):
        """输出错误信息到 stderr"""
        print(f"ERROR: {message}", file=sys.stderr, flush=True)
    
    def _check_app_alive(self) -> bool:
        """检查应用是否存活，退出时停止监听"""
        if self._process and self._process.poll() is not None:
            app_name = "unknown"
            if self._process.args:
                first_arg = self._process.args[0]
                if isinstance(first_arg, str):
                    app_name = os.path.basename(first_arg)
                elif isinstance(first_arg, bytes):
                    app_name = os.path.basename(first_arg).decode('utf-8', errors='replace')
            
            self._output({
                "type": "app_exit",
                "timestamp": self._timestamp(),
                "app": app_name,
                "pid": self._process.pid,
                "events_count": self._event_count,
            })
            
            # 停止事件循环
            try:
                Atspi.event_quit()
            except Exception:
                pass
            
            return False  # 停止 GLib timeout
        
        return True  # 继续检查
    
    def _on_signal(self, signum, frame):
        """信号处理 - 优雅退出"""
        self._cleanup()
        sys.exit(0)
    
    def _cleanup(self):
        """清理资源"""
        try:
            # 注销事件监听器
            if self._listener:
                for event_type in EVENT_TYPES:
                    try:
                        Atspi.EventListener.deregister(self._listener, event_type)
                    except Exception:
                        pass
        
        except Exception:
            pass
        
        # 终止应用进程
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
                self._process.wait(timeout=3)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass


def main():
    """CLI 入口（用于直接运行此模块）"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="检查应用的无障碍树和事件流",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  youqu inspect /usr/bin/deepin-music
  youqu inspect /usr/bin/deepin-reader document.pdf
  youqu inspect /path/to/app > result.jsonl
        """
    )
    parser.add_argument("app_path", help="应用可执行文件路径")
    parser.add_argument("app_args", nargs="*", help="传递给应用的参数")
    
    args = parser.parse_args()
    
    inspector = AtspiInspector()
    inspector.inspect(args.app_path, args.app_args)


if __name__ == "__main__":
    main()
