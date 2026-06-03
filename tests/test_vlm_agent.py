import re

import pytest


class TestSafeTextPattern:
    def test_ascii_alphanumeric(self):
        from src.vlm.vlm_agent import _is_safe_text

        assert _is_safe_text("hello world")

    def test_chinese_text(self):
        from src.vlm.vlm_agent import _is_safe_text

        assert _is_safe_text("你好世界")

    def test_mixed_chinese_ascii(self):
        from src.vlm.vlm_agent import _is_safe_text

        assert _is_safe_text("文件名.txt")

    def test_common_punctuation(self):
        from src.vlm.vlm_agent import _is_safe_text

        assert _is_safe_text("test@example.com")
        assert _is_safe_text("http://localhost:8080")
        assert _is_safe_text("price: 100.00")

    def test_newline_cleaned(self):
        from src.vlm.vlm_agent import _is_safe_text

        text = "hello\nworld"
        cleaned = text.replace("\n", " ")
        assert _is_safe_text(cleaned)

    def test_carriage_return_cleaned(self):
        from src.vlm.vlm_agent import _is_safe_text

        text = "hello\rworld"
        cleaned = text.replace("\r", " ")
        assert _is_safe_text(cleaned)

    def test_tab_cleaned(self):
        from src.vlm.vlm_agent import _is_safe_text

        text = "hello\tworld"
        cleaned = text.replace("\t", " ")
        assert _is_safe_text(cleaned)

    def test_whitespace_only(self):
        from src.vlm.vlm_agent import _is_safe_text

        assert _is_safe_text("   ")

    def test_path_with_slash(self):
        from src.vlm.vlm_agent import _is_safe_text

        assert _is_safe_text("/home/user/file.txt")

    def test_empty_string(self):
        from src.vlm.vlm_agent import _is_safe_text

        assert not _is_safe_text("")

    def test_length_limit(self):
        from src.vlm.vlm_agent import _is_safe_text

        assert not _is_safe_text("a" * 1001)
        assert _is_safe_text("a" * 1000)

    def test_dollar_sign_rejected(self):
        from src.vlm.vlm_agent import _is_safe_text

        assert not _is_safe_text("$HOME")

    def test_tilde_rejected(self):
        from src.vlm.vlm_agent import _is_safe_text

        assert not _is_safe_text("~/file.txt")

    def test_backtick_rejected(self):
        from src.vlm.vlm_agent import _is_safe_text

        assert not _is_safe_text("$(whoami)")
        assert not _is_safe_text("`id`")

    def test_pipe_rejected(self):
        from src.vlm.vlm_agent import _is_safe_text

        assert not _is_safe_text("cat /etc/passwd | sort")

    def test_shell_commands_safe_after_clean(self):
        from src.vlm.vlm_agent import _is_safe_text

        assert _is_safe_text("rm -rf /")
        assert _is_safe_text("sudo su")

    def test_special_chars_in_pattern(self):
        from src.vlm.vlm_agent import _is_safe_text, _SAFE_TEXT_PATTERN

        safe_chars = ".\,\-\+\=\!\?\@\#\%\^\&\*\(\)\:\;\"\'\/\\"
        for char in safe_chars:
            assert _is_safe_text("a{}b".format(char)), "char '{}' should be safe".format(char)

    def test_special_chars_not_in_pattern(self):
        from src.vlm.vlm_agent import _is_safe_text

        unsafe = ["$", "`", "~", "|", "<", ">", "{", "}"]
        for char in unsafe:
            assert not _is_safe_text("a{}b".format(char)), "char '{}' should be unsafe".format(char)


class TestAllowedTools:
    def test_all_defined_tools(self):
        from src.vlm.vlm_agent import _ALLOWED_TOOLS

        expected = {"click", "type_text", "press_key", "scroll", "wait", "finish"}
        assert _ALLOWED_TOOLS == expected

    def test_tools_match_definition(self):
        from src.vlm.vlm_agent import _ALLOWED_TOOLS, TOOLS_DEFINITION

        defined = {t["function"]["name"] for t in TOOLS_DEFINITION}
        assert defined == _ALLOWED_TOOLS

    def test_tools_definition_schema(self):
        from src.vlm.vlm_agent import TOOLS_DEFINITION

        for tool in TOOLS_DEFINITION:
            assert tool["type"] == "function"
            fn = tool["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn
            params = fn["parameters"]
            assert params["type"] == "object"
            assert "properties" in params
            assert "required" in params

    def test_click_tool_params(self):
        from src.vlm.vlm_agent import TOOLS_DEFINITION

        click = next(t for t in TOOLS_DEFINITION if t["function"]["name"] == "click")
        required = set(click["function"]["parameters"]["required"])
        assert required == {"x", "y", "description"}
        props = click["function"]["parameters"]["properties"]
        assert props["x"]["type"] == "integer"
        assert props["y"]["type"] == "integer"

    def test_type_text_tool_params(self):
        from src.vlm.vlm_agent import TOOLS_DEFINITION

        tt = next(t for t in TOOLS_DEFINITION if t["function"]["name"] == "type_text")
        assert set(tt["function"]["parameters"]["required"]) == {"text"}

    def test_scroll_tool_direction_enum(self):
        from src.vlm.vlm_agent import TOOLS_DEFINITION

        scroll = next(t for t in TOOLS_DEFINITION if t["function"]["name"] == "scroll")
        assert set(scroll["function"]["parameters"]["properties"]["direction"]["enum"]) == {"up", "down", "left", "right"}

    def test_wait_tool_max_in_doc(self):
        from src.vlm.vlm_agent import TOOLS_DEFINITION

        wait = next(t for t in TOOLS_DEFINITION if t["function"]["name"] == "wait")
        assert "max 10" in wait["function"]["parameters"]["properties"]["seconds"]["description"]

    def test_finish_tool_params(self):
        from src.vlm.vlm_agent import TOOLS_DEFINITION

        finish = next(t for t in TOOLS_DEFINITION if t["function"]["name"] == "finish")
        assert set(finish["function"]["parameters"]["required"]) == {"success", "message"}
