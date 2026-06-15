# SPDX-FileCopyrightText: 2026 UnionTech Software Technology Co., Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for src.web_spec.locator_resolver."""

import pytest

from web_spec.locator_resolver import LocatorError, resolve
from web_spec.models import Locator


class FakeLocator:
    def __init__(self, count):
        self.first = self
        self._count = count

    def count(self):
        return self._count


class FakePage:
    def __init__(self, count):
        self.count = count

    def locator(self, value):
        return FakeLocator(self.count)


def test_interactive_locator_requires_unique_match_by_default():
    locator = Locator(strategy="css", value=".item")

    with pytest.raises(LocatorError):
        resolve(FakePage(2), locator, require_unique=True)


def test_locator_can_explicitly_take_first_match():
    locator = Locator(strategy="css", value=".item", first=True)

    resolved = resolve(FakePage(2), locator, require_unique=True)

    assert resolved.match_count == 2
