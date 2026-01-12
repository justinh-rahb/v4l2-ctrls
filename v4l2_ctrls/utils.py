"""Utility helpers for v4l2-ctrls."""

from __future__ import annotations

import time
from typing import Dict, List


def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def normalize_prefix(prefix: str) -> str:
    if not prefix:
        return prefix
    if not prefix.startswith("/"):
        prefix = f"/{prefix}"
    if not prefix.endswith("/"):
        prefix = f"{prefix}/"
    return prefix


def parse_stream_prefixes(items: List[str]) -> Dict[str, str]:
    prefixes: Dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"Invalid --stream-prefix value: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            raise SystemExit(f"Invalid --stream-prefix value: {item}")
        prefixes[key] = normalize_prefix(value)
    return prefixes


def format_stream_path(template: str, data: Dict[str, str]) -> str:
    try:
        return template.format(**data)
    except KeyError:
        return template


def build_storage_prefix(app_base_url: str, port: int, socket_mode: bool) -> str:
    path_part = (
        app_base_url.strip("/").replace("/", "-")
        if app_base_url and app_base_url != "./"
        else ""
    )
    if socket_mode:
        return path_part or "default"
    if path_part:
        return f"{port}-{path_part}"
    return str(port)
