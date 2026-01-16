"""Persistence helpers for V4L2 control state."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

from .camera import (
    apply_controls,
    fetch_controls,
    order_controls_by_precedence,
    validate_values,
)
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
    succeeded = []
    failed = []
    for name, value in order_controls_by_precedence(validated):
        ok, out, err, _code = apply_controls(device, {name: value})
        if ok:
            succeeded.append(name)
        else:
            failed.append(name)
            log(f"Failed to restore {name}: {err or out}")
    if succeeded:
        log(f"Restored {len(succeeded)} controls from {path}")
    if failed:
        log(f"Failed to restore {len(failed)} controls: {', '.join(failed)}")
