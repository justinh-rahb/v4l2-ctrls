"""V4L2 device discovery and control parsing."""

from __future__ import annotations

import glob
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .utils import format_stream_path, log, normalize_prefix

CONTROL_ORDER = [
    "focus_auto",
    "focus_automatic_continuous",
    "focus_absolute",
    "exposure_auto",
    "exposure_absolute",
    "exposure_time_absolute",
    "white_balance_temperature_auto",
    "white_balance_temperature",
    "brightness",
    "contrast",
    "saturation",
    "sharpness",
    "gain",
]

AUTO_FIRST_CONTROLS = {
    "exposure_auto",
    "white_balance_temperature_auto",
    "focus_auto",
    "focus_automatic_continuous",
}


@dataclass(frozen=True)
class Camera:
    cam: str
    device: str
    prefix: str
    streams: Dict[str, str]
    index: int
    basename: str


def parse_listed_devices(output: str) -> List[str]:
    devices = []
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("/dev/"):
            continue
        devices.append(line.split()[0])
    return devices


def run_v4l2(args: List[str], timeout: float = 3.0) -> Tuple[int, str, str]:
    try:
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        return 124, "", f"Timeout running {' '.join(args)}: {exc}"


def detect_devices(limit: int = 8) -> List[str]:
    devices: List[str] = []
    code, out, _ = run_v4l2(["v4l2-ctl", "--list-devices"], timeout=2.0)
    if code == 0:
        devices = parse_listed_devices(out)
    if not devices:
        subdevs = sorted(glob.glob("/dev/v4l-subdev*"))
        videos = sorted(glob.glob("/dev/video*"))
        devices = subdevs + videos
    subdevs = [device for device in devices if "/dev/v4l-subdev" in device]
    others = [device for device in devices if device not in subdevs]
    devices = subdevs + others
    preferred = "/dev/v4l-subdev2"
    if preferred in devices:
        devices.remove(preferred)
        devices.insert(0, preferred)
    return devices[:limit]


def normalize_type(ctrl_type: Optional[str]) -> str:
    if not ctrl_type:
        return "unknown"
    if ctrl_type == "bool":
        return "bool"
    if ctrl_type.startswith("int"):
        return "int"
    if ctrl_type == "menu":
        return "menu"
    return ctrl_type


def get_int_from_parts(parts: List[str], field: str) -> Optional[int]:
    token = next((p for p in parts if p.startswith(f"{field}=")), None)
    if not token:
        return None
    try:
        return int(token.split("=", 1)[1])
    except ValueError:
        return None


def parse_ctrls(output: str) -> List[Dict]:
    controls = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("Error"):
            continue

        if "0x" not in line:
            continue

        parts = line.split()
        if not parts:
            continue
        name = parts[0]
        type_start = line.find("(")
        type_end = line.find(")")
        ctrl_type = None
        if type_start != -1 and type_end != -1:
            ctrl_type = line[type_start + 1 : type_end].strip()
        controls.append(
            {
                "name": name,
                "type": normalize_type(ctrl_type),
                "min": get_int_from_parts(parts, "min"),
                "max": get_int_from_parts(parts, "max"),
                "step": get_int_from_parts(parts, "step"),
                "value": get_int_from_parts(parts, "value"),
                "menu": [],
            }
        )
    return controls


def parse_ctrl_menus(output: str) -> Dict[str, List[Dict[str, str]]]:
    """Parse v4l2-ctl --list-ctrls-menus output."""
    menus: Dict[str, List[Dict[str, str]]] = {}
    current = None

    for line in output.splitlines():
        if not line.strip():
            continue

        stripped = line.strip()

        if stripped in [
            "User Controls",
            "Camera Controls",
            "Video Controls",
            "Image Controls",
        ]:
            continue

        if stripped and stripped[0].isdigit() and ":" in stripped:
            if current is None:
                continue
            parts = stripped.split(":", 1)
            try:
                value = int(parts[0].strip())
                label = parts[1].strip()
                menus[current].append({"value": value, "label": label})
            except (ValueError, IndexError):
                continue
        elif "0x" in stripped:
            name = stripped.split()[0]
            current = name
            menus.setdefault(current, [])

    return menus


def sort_controls(controls: List[Dict]) -> List[Dict]:
    order_map = {name: idx for idx, name in enumerate(CONTROL_ORDER)}
    indexed = list(enumerate(controls))

    def sort_key(item: Tuple[int, Dict]) -> Tuple[int, int]:
        original_idx, ctrl = item
        idx = order_map.get(ctrl["name"], len(CONTROL_ORDER))
        return (idx, original_idx)

    return [ctrl for _, ctrl in sorted(indexed, key=sort_key)]


def fetch_controls(device: str, include_menus: bool = True) -> List[Dict]:
    code1, out1, err1 = run_v4l2(["v4l2-ctl", "-d", device, "--list-ctrls"])
    if code1 != 0:
        raise RuntimeError(err1 or out1 or "Failed to list controls")
    controls = parse_ctrls(out1)

    if include_menus:
        code2, out2, err2 = run_v4l2(["v4l2-ctl", "-d", device, "--list-ctrls-menus"])
        if code2 == 0:
            menus = parse_ctrl_menus(out2)
            log(f"Found {len(menus)} controls with menus")
            for ctrl in controls:
                ctrl_name = ctrl["name"]
                if ctrl_name in menus and menus[ctrl_name]:
                    ctrl["menu"] = menus[ctrl_name]
                    ctrl["type"] = "menu"
                    log(f"  {ctrl_name}: {len(menus[ctrl_name])} menu items")
        else:
            log(f"Failed to get menus: code={code2}, err={err2}")

    return sort_controls(controls)


def validate_values(values: Dict[str, int], controls: List[Dict]) -> Dict[str, int]:
    allowlist = {ctrl["name"] for ctrl in controls}
    control_map = {ctrl["name"]: ctrl for ctrl in controls}
    validated: Dict[str, int] = {}

    for key, value in values.items():
        if key not in allowlist:
            raise ValueError(f"Unknown control: {key}")
        if isinstance(value, bool):
            value = int(value)
        if not isinstance(value, int):
            raise ValueError(f"Value for {key} must be integer")
        ctrl_def = control_map.get(key)
        if ctrl_def:
            min_val = ctrl_def.get("min")
            max_val = ctrl_def.get("max")
            if min_val is not None and max_val is not None:
                if not (min_val <= value <= max_val):
                    raise ValueError(f"{key}={value} out of range [{min_val}, {max_val}]")
        validated[key] = value

    return validated


def apply_controls(device: str, values: Dict[str, int]) -> Tuple[bool, str, str, int]:
    if not values:
        return True, "", "", 0
    set_parts = [f"{key}={value}" for key, value in values.items()]
    cmd = ["v4l2-ctl", "-d", device, f"--set-ctrl={','.join(set_parts)}"]
    code, out, err = run_v4l2(cmd)
    return code == 0, out, err, code


def split_controls_by_precedence(
    values: Dict[str, int]
) -> Tuple[Dict[str, int], Dict[str, int]]:
    auto_first = {key: value for key, value in values.items() if key in AUTO_FIRST_CONTROLS}
    remaining = {key: value for key, value in values.items() if key not in AUTO_FIRST_CONTROLS}
    return auto_first, remaining


def infer_default_prefix(device: str, idx: int, use_default_mapping: bool = True) -> str:
    if not use_default_mapping:
        if idx == 1:
            return "/webcam/"
        return f"/webcam{idx}/"

    base = os.path.basename(device)
    match = re.match(r"video(\d+)$", base)
    if match:
        number = int(match.group(1))
        if number >= 11:
            derived_idx = number - 10
            if derived_idx == 1:
                return "/webcam/"
            return f"/webcam{derived_idx}/"
    if idx == 1:
        return "/webcam/"
    return f"/webcam{idx}/"


def build_cams(
    devices: List[str],
    prefixes: Dict[str, str],
    stream_templates: Dict[str, str],
    use_default_mapping: bool = True,
) -> List[Camera]:
    cams = []
    seen = set()
    for idx, device in enumerate(devices, start=1):
        base = os.path.basename(device)
        cam_id = base or f"cam{idx}"
        if cam_id in seen:
            suffix = 2
            while f"{cam_id}-{suffix}" in seen:
                suffix += 1
            cam_id = f"{cam_id}-{suffix}"
        seen.add(cam_id)
        prefix = (
            prefixes.get(device)
            or prefixes.get(base)
            or prefixes.get(cam_id)
            or infer_default_prefix(device, idx, use_default_mapping)
        )
        prefix = normalize_prefix(prefix)
        template_data = {
            "prefix": prefix,
            "cam": cam_id,
            "device": device,
            "basename": base,
            "index": str(idx),
        }
        streams = {}
        for mode, template in stream_templates.items():
            data = dict(template_data)
            data["mode"] = mode
            streams[mode] = format_stream_path(template, data)
        cams.append(
            Camera(
                cam=cam_id,
                device=device,
                prefix=prefix,
                streams=streams,
                index=idx,
                basename=base,
            )
        )
    return cams
