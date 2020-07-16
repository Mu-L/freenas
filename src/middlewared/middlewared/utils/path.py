# -*- coding=utf-8 -*-

import importlib.util
import logging
import os

logger = logging.getLogger(__name__)

__all__ = ["is_child", "module_from_file"]


def is_child(child: str, parent: str):
    rel = os.path.relpath(child, parent)
    return rel == "." or not rel.startswith("..")


def module_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
