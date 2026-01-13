"""Persistence helpers for V4L2 control state."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

from .camera import apply_controls, fetch_controls, split_controls_by_precedence, validate_values
from .utils import log


def load_state(path: Path) -> Dict[str, int]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            return {k: int(v) for k, v in data.items() if isinstance(k, str)}
    except Exception as exc:
        log(f"Failed to load state from {path}: {exc}")
    return {}


def save_state(path: Path, values: Dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(values, indent=2, sort_keys=True))
    os.replace(tmp_path, path)


def restore_state(device: str, path: Path) -> None:
    saved = load_state(path)
    if not saved:
        log("No persisted controls to restore")
        return
    controls = fetch_controls(device, include_menus=False)
    try:
        validated = validate_values(saved, controls)
    except ValueError as exc:
        log(f"State validation error: {exc}")
        validated = {}
    if not validated:
        log("No valid persisted controls to apply")
        return
    auto_first, remaining = split_controls_by_precedence(validated)
    ok, out, err, code = apply_controls(device, auto_first)
    if not ok:
        log(f"Failed to restore auto controls: code={code}, err={err or out}")
        return
    ok, out, err, code = apply_controls(device, remaining)
    if ok:
        log(f"Restored {len(validated)} controls from {path}")
    else:
        log(f"Failed to restore controls: code={code}, err={err or out}")
