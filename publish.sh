#!/bin/bash
# SPDX-FileCopyrightText: 2023 - 2026 UnionTech Software Technology Co., Ltd.
# SPDX-License-Identifier: GPL-2.0-only

pip3 install --upgrade pip build twine
python3 -m build
twine upload dist/*
