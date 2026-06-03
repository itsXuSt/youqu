import json
import sys
from unittest.mock import MagicMock, patch

from src.vlm.vlm_agent import VLMAgent

MOCK_MK = MagicMock()
MK_CLS = MagicMock(return_value=MOCK_MK)


def _make_agent(tmp_path):
    locator = MagicMock()
    config = MagicMock()
    config.get_safe_evidence_dir.return_value = tmp_path
    agent = VLMAgent(locator=locator, config=config)
    agent._screen_size = (1920, 1080)
    return agent


def _tool_call(name, args=None):
    if args is None:
        args = {}
    return {"function": {"name": name, "arguments": json.dumps(args)}}


def _result(tool_calls=None, content="", error=None):
    msg = {"content": content, "tool_calls": tool_calls or []}
    if error:
        return {"error": error}
    return {"choices": [{"message": msg}]}


class TestUnsafeInstruction:
    def test_unsafe_chars_rejected(self, tmp_path):
        agent = _make_agent(tmp_path)
        result = agent.run("run $(whoami)")
        assert result["success"] is False
        assert result["iterations"] == 0
        assert "unsafe" in result["error"]

    def test_pipe_in_instruction_rejected(self, tmp_path):
        agent = _make_agent(tmp_path)
        result = agent.run("cat /etc/passwd | sort")
        assert result["success"] is False
        assert result["iterations"] == 0

    def test_overlong_instruction_rejected(self, tmp_path):
        agent = _make_agent(tmp_path)
        result = agent.run("a" * 1001)
        assert result["success"] is False
        assert result["iterations"] == 0


class TestVLMAPIError:
    def test_api_error_returns_with_iteration(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(error="API timeout")
            result = agent.run("safe instruction")
        assert result["success"] is False
        assert result["iterations"] == 1
        assert "API timeout" in result["error"]


class TestNoToolCallsContentSignal:
    def test_finish_signal_on_second_iteration(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
            patch("time.sleep"),
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.side_effect = [
                _result(tool_calls=[_tool_call("wait", {"seconds": 1})]),
                _result(content="Task is now finished"),
            ]
            result = agent.run("safe instruction")
        assert result["success"] is True
        assert result["error"] == ""
        assert result["iterations"] == 2

    def test_done_signal_on_second_iteration(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
            patch("time.sleep"),
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.side_effect = [
                _result(tool_calls=[_tool_call("wait", {"seconds": 1})]),
                _result(content="All done!"),
            ]
            result = agent.run("safe instruction")
        assert result["success"] is True
        assert result["iterations"] == 2

    def test_no_signal_continues_to_max(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(content="processing")
            result = agent.run("safe instruction", max_iterations=3)
        assert result["success"] is False
        assert result["iterations"] == 3
        assert "Max iterations" in result["error"]

    def test_signal_ignored_on_first_iteration(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.side_effect = [
                _result(content="I am finished"),
                _result(content="still processing"),
                _result(content="keep going"),
            ]
            result = agent.run("safe instruction", max_iterations=3)
        assert result["success"] is False
        assert result["iterations"] == 3


class TestUnknownTool:
    def test_unknown_tool_skipped(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("explode")]
            )
            result = agent.run("safe instruction", max_iterations=2)
        MOCK_MK.click.assert_not_called()
        assert result["iterations"] == 2


class TestFinishTool:
    def test_finish_early_iteration_zero_ignored(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            call_count = 0

            def side_effect(*a, **kw):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return _result(tool_calls=[_tool_call("finish", {"success": True, "message": "done"})])
                return _result(content="working")

            agent._locator.decide_tool_call.side_effect = side_effect
            result = agent.run("safe instruction", max_iterations=3)
        assert result["success"] is False
        assert result["iterations"] == 3

    def test_finish_on_iteration_one_returns(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
            patch("time.sleep"),
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.side_effect = [
                _result(tool_calls=[_tool_call("wait", {"seconds": 1})]),
                _result(tool_calls=[_tool_call("finish", {"success": True, "message": "ok"})]),
            ]
            result = agent.run("safe instruction", max_iterations=3)
        assert result["success"] is True
        assert result["iterations"] == 2
        assert "ok" in result["error"]

    def test_finish_returns_success(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
            patch("time.sleep"),
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.side_effect = [
                _result(tool_calls=[_tool_call("wait", {"seconds": 1})]),
                _result(
                    tool_calls=[
                        _tool_call("finish", {"success": True, "message": "task completed"})
                    ]
                ),
            ]
            result = agent.run("safe instruction")
        assert result["success"] is True
        assert result["iterations"] == 2
        assert "task completed" in result["error"]

    def test_finish_returns_failure(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
            patch("time.sleep"),
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.side_effect = [
                _result(tool_calls=[_tool_call("wait", {"seconds": 1})]),
                _result(
                    tool_calls=[
                        _tool_call("finish", {"success": False, "message": "element not found"})
                    ]
                ),
            ]
            result = agent.run("safe instruction")
        assert result["success"] is False
        assert "element not found" in result["error"]


class TestClickTool:
    def setup_method(self):
        MOCK_MK.reset_mock()

    def test_click_valid_coordinates(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("click", {"x": 100, "y": 200, "description": "button"})]
            )
            result = agent.run("safe instruction", max_iterations=1)
        MOCK_MK.click.assert_called_once_with(100, 200)

    def test_click_out_of_bounds_negative(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("click", {"x": -1, "y": 100, "description": "oob"})]
            )
            result = agent.run("safe instruction", max_iterations=1)
        MOCK_MK.click.assert_not_called()

    def test_click_out_of_bounds_exceeds_screen(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("click", {"x": 2000, "y": 2000, "description": "oob"})]
            )
            result = agent.run("safe instruction", max_iterations=1)
        MOCK_MK.click.assert_not_called()


class TestTypeTextTool:
    def setup_method(self):
        MOCK_MK.reset_mock()

    def test_safe_text_typed(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("type_text", {"text": "hello world"})]
            )
            result = agent.run("safe instruction", max_iterations=1)
        MOCK_MK.input_message.assert_called_once_with("hello world")

    def test_unsafe_text_rejected(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("type_text", {"text": "rm -rf / && $(whoami)"})]
            )
            result = agent.run("safe instruction", max_iterations=1)
        MOCK_MK.input_message.assert_not_called()

    def test_long_text_rejected(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("type_text", {"text": "a" * 1001})]
            )
            result = agent.run("safe instruction", max_iterations=1)
        MOCK_MK.input_message.assert_not_called()


class TestPressKeyTool:
    def setup_method(self):
        MOCK_MK.reset_mock()

    def test_safe_key_pressed(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("press_key", {"key": "Return"})]
            )
            result = agent.run("safe instruction", max_iterations=1)
        MOCK_MK.press_key.assert_called_once_with("Return")

    def test_unsafe_key_rejected(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("press_key", {"key": "$(echo hacked)"})]
            )
            result = agent.run("safe instruction", max_iterations=1)
        MOCK_MK.press_key.assert_not_called()

    def test_long_key_rejected(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("press_key", {"key": "a" * 51})]
            )
            result = agent.run("safe instruction", max_iterations=1)
        MOCK_MK.press_key.assert_not_called()


class TestScrollTool:
    def setup_method(self):
        MOCK_MK.reset_mock()

    def test_scroll_up_positive(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("scroll", {"direction": "up", "amount": 300})]
            )
            result = agent.run("safe instruction", max_iterations=1)
        MOCK_MK.mouse_scroll.assert_called_once_with(300)

    def test_scroll_down_negative(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("scroll", {"direction": "down", "amount": 300})]
            )
            result = agent.run("safe instruction", max_iterations=1)
        MOCK_MK.mouse_scroll.assert_called_once_with(-300)

    def test_scroll_amount_capped_at_500(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("scroll", {"direction": "up", "amount": 999})]
            )
            result = agent.run("safe instruction", max_iterations=1)
        MOCK_MK.mouse_scroll.assert_called_once_with(500)


class TestWaitTool:
    def test_wait_capped_at_10(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
            patch("time.sleep") as mock_sleep,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("wait", {"seconds": 60})]
            )
            result = agent.run("safe instruction", max_iterations=1)
        mock_sleep.assert_called_once_with(10)

    def test_wait_normal(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
            patch("time.sleep") as mock_sleep,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("wait", {"seconds": 3})]
            )
            result = agent.run("safe instruction", max_iterations=1)
        mock_sleep.assert_called_once_with(3)


class TestMaxIterations:
    def test_exhausted_without_finish(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
            patch("time.sleep"),
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("wait", {"seconds": 1})]
            )
            result = agent.run("safe instruction", max_iterations=5)
        assert result["success"] is False
        assert result["iterations"] == 5
        assert "Max iterations (5)" in result["error"]


class TestProgressCallback:
    def test_callback_called_each_iteration(self, tmp_path):
        agent = _make_agent(tmp_path)
        callback_calls = []
        cb = lambda msg: callback_calls.append(msg)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
            patch("time.sleep"),
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(
                tool_calls=[_tool_call("wait", {"seconds": 1})]
            )
            result = agent.run("safe instruction", max_iterations=3, progress_callback=cb)
        assert len(callback_calls) >= 3
        assert any("1/3" in c for c in callback_calls)
        assert any("2/3" in c for c in callback_calls)
        assert any("3/3" in c for c in callback_calls)

    def test_no_callback_no_error(self, tmp_path):
        agent = _make_agent(tmp_path)
        with (
            patch.dict(sys.modules, {"src.mouse_key": MagicMock(MouseKey=MK_CLS)}),
            patch("src.vlm.screenshot", create=True) as ss_mod,
        ):
            ss_mod.capture_for_vlm = MagicMock()
            agent._locator.decide_tool_call.return_value = _result(content="still working")
            result = agent.run("safe instruction", max_iterations=1)
        assert result["iterations"] == 1
