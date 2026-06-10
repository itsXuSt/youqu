#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AT-SPI Inspector 单元测试"""
import json
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from io import StringIO
from unittest.mock import Mock, patch


def test_extract_event_data():
    """测试事件数据提取"""
    from atspi_inspector import AtspiInspector
    
    inspector = AtspiInspector()
    
    # Mock _get_states 方法（避免依赖真实的 Atspi.StateType）
    inspector._get_states = Mock(return_value=["enabled", "focusable"])
    inspector._get_parent_path = Mock(return_value="主窗口")
    
    # 模拟 AT-SPI 事件对象
    mock_event = Mock()
    mock_event.type = "object:state-changed:focused"
    mock_event.detail1 = 1
    
    mock_source = Mock()
    mock_source.get_name.return_value = "播放按钮"
    mock_source.get_role_name.return_value = "push button"
    
    mock_event.source = mock_source
    
    # 测试数据提取
    data = inspector._extract_event_data(mock_event)
    
    assert data is not None, f"data is None, extraction failed"
    assert data["type"] == "event"
    assert data["role"] == "push button"
    assert data["name"] == "播放按钮"
    assert data["event"] == "focused"
    assert data["detail1"] == 1
    assert "enabled" in data["states"]
    print("✓ test_extract_event_data passed")


def test_is_noise_filtering():
    """测试噪声过滤"""
    from atspi_inspector import AtspiInspector
    
    inspector = AtspiInspector()
    
    # 失去焦点应该被过滤
    event1 = Mock()
    event1.type = "object:state-changed:focused"
    event1.detail1 = 0
    event1.source = Mock()
    assert inspector._is_noise(event1) is True
    
    # 获得焦点不应该被过滤
    event2 = Mock()
    event2.type = "object:state-changed:focused"
    event2.detail1 = 1
    event2.source = Mock()
    assert inspector._is_noise(event2) is False
    
    # enabled 事件应该被过滤（冗余）
    event3 = Mock()
    event3.type = "object:state-changed:enabled"
    event3.source = Mock()
    assert inspector._is_noise(event3) is True
    print("✓ test_is_noise_filtering passed")


def test_simplify_event_type():
    """测试事件类型简化"""
    from atspi_inspector import AtspiInspector
    
    inspector = AtspiInspector()
    
    assert inspector._simplify_event_type("object:state-changed:focused") == "focused"
    assert inspector._simplify_event_type("object:state-changed:showing") == "showing"
    assert inspector._simplify_event_type("window:activate") == "activate"
    assert inspector._simplify_event_type("window:create") == "create"
    print("✓ test_simplify_event_type passed")


def test_timestamp_format():
    """测试时间戳格式"""
    from atspi_inspector import AtspiInspector
    
    inspector = AtspiInspector()
    ts = inspector._timestamp()
    
    # ISO 8601 格式检查
    assert "T" in ts
    assert ts.endswith("Z")
    assert len(ts) == 24  # 2025-06-09T10:30:00.123Z
    print("✓ test_timestamp_format passed")


def test_ndjson_output():
    """测试 NDJSON 输出格式"""
    from atspi_inspector import AtspiInspector
    
    inspector = AtspiInspector()
    
    # 捕获 stdout
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        inspector._output({
            "type": "event",
            "ts": "2025-06-09T10:30:00.123Z",
            "role": "push button",
            "name": "测试"
        })
        
        output = mock_stdout.getvalue()
        assert output.endswith("\n")
        
        # 验证 JSON 可解析
        data = json.loads(output.strip())
        assert data["type"] == "event"
        assert data["role"] == "push button"
        assert data["name"] == "测试"
    print("✓ test_ndjson_output passed")


if __name__ == "__main__":
    test_extract_event_data()
    test_is_noise_filtering()
    test_simplify_event_type()
    test_timestamp_format()
    test_ndjson_output()
    print("\n所有测试通过 ✓")

