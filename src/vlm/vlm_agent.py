#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
# SPDX-FileCopyrightText: 2023 UnionTech Software Technology Co., Ltd.
# SPDX-License-Identifier: GPL-2.0-only
# pylint: disable=all
"""VLM Agent - execution layer component for autonomous VLM Agent execution."""
from __future__ import annotations

import json
import logging
import re
import time
from typing import TYPE_CHECKING, Any, Callable

from src.vlm.vlm_locator import VLMLocator

if TYPE_CHECKING:
    from src.vlm.config import VLMConfig

logger = logging.getLogger(__name__)

_SAFE_TEXT_PATTERN = re.compile(r"^[\w\s\.\,\-\+\=\!\?\@\#\%\^\&\*\(\)\:\;\"\'\/\\\u4e00-\u9fff]+$")
_ALLOWED_TOOLS = frozenset(["click", "type_text", "press_key", "scroll", "wait", "finish"])


TOOLS_DEFINITION = [
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click at specified screen coordinates",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                    "description": {
                        "type": "string",
                        "description": "Description of what is being clicked",
                    },
                },
                "required": ["x", "y", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Type text using keyboard",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "Press a key or key combination",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Key or key combo, e.g. 'Return', 'ctrl+a'",
                    },
                },
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scroll",
            "description": "Scroll the screen or window",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down", "left", "right"],
                        "description": "Scroll direction",
                    },
                    "amount": {
                        "type": "integer",
                        "description": "Scroll amount in pixels (default 200)",
                    },
                },
                "required": ["direction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wait",
            "description": "Wait for a specified duration",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "number",
                        "description": "Wait duration in seconds (max 10)",
                    },
                },
                "required": ["seconds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Signal that the task is complete",
            "parameters": {
                "type": "object",
                "properties": {
                    "success": {
                        "type": "boolean",
                        "description": "Whether the task succeeded",
                    },
                    "message": {"type": "string", "description": "Result message"},
                },
                "required": ["success", "message"],
            },
        },
    },
]


def _is_safe_text(text: str) -> bool:
    if len(text) > 1000:
        return False
    cleaned = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    return bool(_SAFE_TEXT_PATTERN.match(cleaned))


class VLMAgent:
    """VLM Agent for autonomous test execution."""

    def __init__(
        self,
        locator: VLMLocator,
        config: "VLMConfig",
    ) -> None:
        self._locator = locator
        self._config = config
        self._evidence_dir = config.get_safe_evidence_dir()
        self._screen_size = None

    def _get_screen_size(self) -> tuple:
        """Get screen dimensions using youqu MouseKey."""
        if self._screen_size:
            return self._screen_size
        try:
            from src.mouse_key import MouseKey

            self._screen_size = MouseKey.screen_size()
            return self._screen_size
        except Exception as e:
            logger.warning("Failed to get screen size: {}".format(e))
        return (3840, 2160)

    def run(
        self,
        instruction: str,
        max_iterations: int = 5,
        progress_callback: Callable = None,  # type: ignore[assignment]
    ) -> dict:
        """Run the VLM Agent to execute the instruction autonomously.

        Args:
            instruction: Natural language instruction to execute
            max_iterations: Maximum number of VLM iterations
            progress_callback: Optional callback for progress updates

        Returns:
            dict with keys: success, error, iterations
        """
        from src.mouse_key import MouseKey
        from src.vlm.screenshot import capture_for_vlm

        if not _is_safe_text(instruction):
            return {
                "success": False,
                "error": "Instruction contains unsafe characters or exceeds length limit",
                "iterations": 0,
            }

        self._evidence_dir.mkdir(parents=True, exist_ok=True)
        history = []
        screen_width, screen_height = self._get_screen_size()
        mouse_key = MouseKey()

        def report(msg: str) -> None:
            logger.info(msg)
            if progress_callback:
                progress_callback(msg)

        for iteration in range(max_iterations):
            report("VLM Agent iteration {}/{}".format(iteration + 1, max_iterations))

            img_path = self._evidence_dir / "agent_step_{}.png".format(iteration)
            capture_for_vlm(output_path=str(img_path))

            result = self._locator.decide_tool_call(
                str(img_path),
                instruction=instruction,
                tools=TOOLS_DEFINITION,
                context={
                    "history": history,
                    "screen_size": {"width": screen_width, "height": screen_height},
                },
            )

            if "error" in result:
                logger.error("VLM API error: {}".format(result["error"]))
                return {
                    "success": False,
                    "error": result["error"],
                    "iterations": iteration + 1,
                }

            message = result.get("choices", [{}])[0].get("message", {})
            tool_calls = message.get("tool_calls", [])

            history.append(message)

            if not tool_calls:
                content = message.get("content", "")
                if iteration >= 1 and ("finish" in content.lower() or "done" in content.lower()):
                    report("Agent completed via content signal")
                    return {"success": True, "error": "", "iterations": iteration + 1}
                logger.debug("No tool calls, content: {}".format(content[:100]))
                continue

            for tool_call in tool_calls:
                fn_name = tool_call["function"]["name"]
                fn_args = tool_call["function"]["arguments"]

                report("Executing tool: {}".format(fn_name))

                if fn_name not in _ALLOWED_TOOLS:
                    logger.warning("Unknown tool: {}".format(fn_name))
                    continue

                if fn_name == "finish":
                    args = (
                        json.loads(fn_args) if isinstance(fn_args, str) else fn_args
                    )
                    if iteration < 1:
                        logger.warning("finish() called too early (iteration %d), ignoring", iteration)
                        continue
                    report(
                        "Agent finished: success={}".format(args.get("success"))
                    )
                    return {
                        "success": args.get("success", True),
                        "error": args.get("message", ""),
                        "iterations": iteration + 1,
                    }

                if fn_name == "click":
                    args = (
                        json.loads(fn_args) if isinstance(fn_args, str) else fn_args
                    )
                    x = args.get("x", 0)
                    y = args.get("y", 0)
                    if 0 <= x <= screen_width and 0 <= y <= screen_height:
                        mouse_key.click(x, y)
                        logger.debug("Clicked at ({}, {})".format(x, y))
                    else:
                        logger.warning(
                            "Click coordinates out of bounds: ({}, {})".format(x, y)
                        )

                elif fn_name == "type_text":
                    args = (
                        json.loads(fn_args) if isinstance(fn_args, str) else fn_args
                    )
                    text = args.get("text", "")
                    if _is_safe_text(text):
                        cleaned = text.replace("\n", " ").replace("\r", " ")
                        mouse_key.input_message(cleaned)
                        logger.debug("Typed text ({} chars)".format(len(cleaned)))
                    else:
                        logger.warning("Text rejected: unsafe content or length={}".format(len(text)))

                elif fn_name == "press_key":
                    args = (
                        json.loads(fn_args) if isinstance(fn_args, str) else fn_args
                    )
                    key = args.get("key", "")
                    if len(key) <= 50 and _is_safe_text(key):
                        mouse_key.press_key(key)
                        logger.debug("Pressed key ({} chars)".format(len(key)))
                    else:
                        logger.warning("Key rejected: {}".format(key))

                elif fn_name == "scroll":
                    args = (
                        json.loads(fn_args) if isinstance(fn_args, str) else fn_args
                    )
                    direction = args.get("direction", "down")
                    amount = min(args.get("amount", 200), 500)
                    # youqu MouseKey uses positive=up, negative=down
                    scroll_amount = -amount if direction == "down" else amount
                    mouse_key.mouse_scroll(scroll_amount)
                    logger.debug("Scrolled {} by {}".format(direction, amount))

                elif fn_name == "wait":
                    args = (
                        json.loads(fn_args) if isinstance(fn_args, str) else fn_args
                    )
                    seconds = min(args.get("seconds", 1), 10)
                    time.sleep(seconds)
                    logger.debug("Waited {} seconds".format(seconds))

        logger.warning(
            "Max iterations ({}) reached without finish()".format(max_iterations)
        )
        return {
            "success": False,
            "error": "Max iterations ({}) reached without finish()".format(
                max_iterations
            ),
            "iterations": max_iterations,
        }
