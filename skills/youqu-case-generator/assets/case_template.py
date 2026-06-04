#!/usr/bin/env python3
# _*_ coding:utf-8 _*_

from apps.autotest_{APP}.case.base_case import BaseCase
from apps.autotest_{APP}.widget.{module}_widget import {Module}Widget


class Test{CaseName}(BaseCase):

    def test_{case_name}_{nnn}(self):
        widget = {Module}Widget()
        # TODO: replace with actual test steps
        widget.click_{target}_by_attr()
        self.assert_true(True)
