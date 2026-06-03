# E2E tests bypass src/__init__.py to avoid the full framework dependency chain.
# VLM submodules only depend on httpx, PIL, and pyscreenshot.
import importlib.util
import os
import sys
from pathlib import Path

_project = Path(__file__).resolve().parent.parent.parent
if str(_project) not in sys.path:
    sys.path.insert(0, str(_project))

os.environ.setdefault("DISPLAY", ":0")
os.environ.setdefault("YOUQU_VLM_ENABLED", "true")


def _load_vlm_module(name):
    """Load a VLM submodule directly without triggering src/__init__.py."""
    fpath = _project / "src" / "vlm" / "{}.py".format(name)
    spec = importlib.util.spec_from_file_location("src.vlm.{}".format(name), str(fpath))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["src.vlm.{}".format(name)] = mod
    spec.loader.exec_module(mod)
    return mod


config_mod = _load_vlm_module("config")
screenshot_mod = _load_vlm_module("screenshot")
locator_mod = _load_vlm_module("vlm_locator")

VLMConfig = config_mod.VLMConfig
CropMeta = screenshot_mod.CropMeta
capture_for_vlm = screenshot_mod.capture_for_vlm
VLMLocator = locator_mod.VLMLocator
ClickTarget = locator_mod.ClickTarget
VLMAssertResult = locator_mod.VLMAssertResult
create_vlm_locator = locator_mod.create_vlm_locator

__all__ = [
    "VLMConfig", "CropMeta", "capture_for_vlm",
    "VLMLocator", "ClickTarget", "VLMAssertResult", "create_vlm_locator",
]
