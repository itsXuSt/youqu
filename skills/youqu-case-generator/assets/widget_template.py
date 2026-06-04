#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
"""
Widget template with all common method patterns included as comments.

Copy this file, replace placeholders, and uncomment relevant patterns.
"""

from apps.autotest_{APP}.widget.base_widget import BaseWidget
from src import log


@log
class {Module}Widget(BaseWidget):
    """Widget methods for {module} functionality."""

    # === AT-SPI attribute-based operations (preferred) ===

    def click_{target}_by_attr(self):
        self.dog.find_element_by_attr("{attr_name}").click()

    def double_click_{target}_by_attr(self):
        self.dog.find_element_by_attr("{attr_name}").double_click()

    def right_click_{target}_by_attr(self):
        self.dog.find_element_by_attr("{attr_name}").right_click()

    def get_{target}_text_by_attr(self):
        return self.dog.find_element_by_attr("{attr_name}").text

    def is_{target}_visible_by_attr(self):
        return self.dog.is_element_exist("{attr_name}")

    def input_{target}_by_attr(self, text):
        self.dog.element_input("{attr_name}", text)

    # === AT-SPI name-based operations (menu items, dialogs) ===

    def click_{target}_in_menu(self):
        self.dog.element_click("{menu_item}")

    def click_{target}_in_submenu(self):
        self.dog.element_click("{parent_menu}")
        self.dog.element_click("{sub_menu_item}")

    def close_dialog(self):
        if self.dog.is_element_exist("{dialog_title}"):
            self.dog.element_click("{close_button}")

    # === Image recognition (maintenance-heavy, use sparingly) ===

    def click_{target}_by_image(self):
        self.image_click("{image_filename}.png")

    def find_{target}_by_image(self):
        return self.find_image("{image_filename}.png")

    # === OCR text recognition (fallback when AT-SPI unavailable) ===

    def click_{target}_by_ocr(self):
        self.click_by_ocr("{target_text}")

    def find_{target}_by_ocr(self):
        return self.ocr("{target_text}")

    # === Keyboard operations ===

    def press_{keyname}(self):
        self.press_key("{key}")

    def hotkey_{action}(self):
        self.hot_key("{combo}")

    def type_text(self, text):
        self.input_message(text)

    # === Composite operations (2-3 steps only) ===

    def open_{feature}_dialog(self):
        self.dog.element_click("{menu_trigger}")
        self.dog.element_click("{dialog_item}")

    def navigate_to_{page}(self):
        self.dog.element_click("{tab_name}")

    # === Wait utilities ===

    def wait_for_{element}(self, timeout=5):
        import time
        start = time.time()
        while time.time() - start < timeout:
            if self.dog.is_element_exist("{attr_name}"):
                return
            time.sleep(0.5)
        raise TimeoutError("{element} not visible within {t}s".format(t=timeout))

    # === File operations ===

    def open_file(self, filepath):
        self.dog.element_click("{open_button}")
        import time; time.sleep(0.5)
        self.hot_key("ctrl+l")
        self.input_message(filepath)
        self.press_key("Return")
        time.sleep(0.5)

    # === List/table interaction ===

    def select_item_in_list(self, item_name):
        children = self.dog.get_children_text("{list_attr}")
        for i, text in enumerate(children):
            if item_name in text:
                self.dog.child_element_click("{list_attr}", i)
                return
        raise ValueError("{item} not found in list".format(item=item_name))
