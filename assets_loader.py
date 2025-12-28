# assets_loader.py
import json
from tools import load_image
from typing import Any, Dict


def _load_recursive(node: Any) -> Any:
    if isinstance(node, str):
        return load_image(node)

    if isinstance(node, dict):
        return {k: _load_recursive(v) for k, v in node.items()}

    if isinstance(node, list):
        return [_load_recursive(v) for v in node]

    return node


def load_assets(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assets = _load_recursive(data)

    if "bars" in assets:
        assets["bars"] = {int(k): v for k, v in assets["bars"].items()}

    return assets
