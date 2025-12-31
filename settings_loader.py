# settings_loader.py
import json
from dataclasses import fields, replace
from typing import get_origin
from settings_schema import SettingsSchema


def _cast(value, target_type):
    origin = get_origin(target_type)

    if origin is tuple:
        return tuple(value)
    if origin is list:
        return list(value)
    if target_type is bool:
        return bool(value)
    if target_type is int:
        return int(value)
    if target_type is float:
        return float(value)
    if target_type is str:
        return str(value)

    return value


def load(path: str) -> SettingsSchema:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    schema = SettingsSchema()
    schema_fields = {f.name: f for f in fields(SettingsSchema)}

    updates = {}

    for key, value in raw.items():
        if key not in schema_fields:
            raise KeyError(f"Unknown setting key: {key}")

        field = schema_fields[key]
        try:
            updates[key] = _cast(value, field.type)
        except Exception as e:
            raise TypeError(
                f"Invalid type for '{key}': expected {field.type}, got {value}"
            ) from e

    return replace(schema, **updates)
