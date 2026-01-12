"""Flask routes for v4l2-ctrls."""

from __future__ import annotations

import json
from typing import Dict, List, Tuple

from flask import Blueprint, current_app, jsonify, render_template, request

from .camera import parse_ctrl_menus, parse_ctrls, run_v4l2, sort_controls
from .utils import build_storage_prefix, log

bp = Blueprint("v4l2_ctrls", __name__)


def get_cam_or_400(cam_index: str, cams: List) -> Tuple[object, object, int | None]:
    if not cam_index:
        return None, jsonify({"error": "Missing camera id"}), 400
    cam = next((item for item in cams if item.cam == cam_index), None)
    if cam is None:
        return None, jsonify({"error": "Camera not found"}), 400
    return cam, None, None


@bp.route("/")
def index():
    title = current_app.config.get("title") or "V4L2 Controls"
    camera_url = current_app.config.get("camera_url")
    app_base_url = current_app.config.get("app_base_url") or "./"
    port = current_app.config.get("port", 5000)
    socket_mode = current_app.config.get("socket_mode", False)
    storage_prefix = build_storage_prefix(app_base_url, port, socket_mode)
    return render_template(
        "index.html",
        title=title,
        camera_url=camera_url,
        app_base_url=app_base_url,
        storage_prefix=storage_prefix,
    )


@bp.route("/api/cams")
def api_cams():
    cams = current_app.config["cams"]
    return jsonify(
        [
            {
                "cam": cam.cam,
                "device": cam.device,
                "prefix": cam.prefix,
                "streams": cam.streams,
                "index": cam.index,
                "basename": cam.basename,
            }
            for cam in cams
        ]
    )


@bp.route("/api/v4l2/ctrls")
def api_ctrls():
    cams = current_app.config["cams"]
    cam_index = request.args.get("cam")
    cam, error, code = get_cam_or_400(cam_index, cams)
    if error:
        return error, code

    code1, out1, err1 = run_v4l2(["v4l2-ctl", "-d", cam.device, "--list-ctrls"])
    if code1 != 0:
        return jsonify({"error": err1 or out1 or "Failed to list controls"}), 500
    controls = parse_ctrls(out1)

    code2, out2, err2 = run_v4l2(
        ["v4l2-ctl", "-d", cam.device, "--list-ctrls-menus"]
    )
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

    controls = sort_controls(controls)
    return jsonify({"controls": controls})


@bp.route("/api/v4l2/set", methods=["POST"])
def api_set():
    cams = current_app.config["cams"]
    cam_index = request.args.get("cam")
    cam, error, code = get_cam_or_400(cam_index, cams)
    if error:
        return error, code
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400
    code1, out1, err1 = run_v4l2(["v4l2-ctl", "-d", cam.device, "--list-ctrls"])
    if code1 != 0:
        return (
            jsonify({"ok": False, "stdout": out1, "stderr": err1, "code": code1}),
            500,
        )
    controls = parse_ctrls(out1)
    allowlist = {ctrl["name"] for ctrl in controls}
    control_map = {ctrl["name"]: ctrl for ctrl in controls}
    applied: Dict[str, int] = {}
    set_parts = []
    for key, value in data.items():
        if key not in allowlist:
            return jsonify({"error": f"Unknown control: {key}"}), 400
        if not isinstance(value, int):
            return jsonify({"error": f"Value for {key} must be integer"}), 400
        ctrl_def = control_map.get(key)
        if ctrl_def:
            min_val = ctrl_def.get("min")
            max_val = ctrl_def.get("max")
            if min_val is not None and max_val is not None:
                if not (min_val <= value <= max_val):
                    return (
                        jsonify(
                            {
                                "error": (
                                    f"{key}={value} out of range [{min_val}, {max_val}]"
                                )
                            }
                        ),
                        400,
                    )
        applied[key] = value
        set_parts.append(f"{key}={value}")
    if not set_parts:
        return jsonify({"error": "No controls provided"}), 400
    cmd = ["v4l2-ctl", "-d", cam.device, f"--set-ctrl={','.join(set_parts)}"]
    code2, out2, err2 = run_v4l2(cmd)
    ok = code2 == 0
    return (
        jsonify(
            {
                "ok": ok,
                "applied": applied,
                "stdout": out2,
                "stderr": err2,
                "code": code2,
            }
        ),
        (200 if ok else 500),
    )


@bp.route("/api/v4l2/info")
def api_info():
    cams = current_app.config["cams"]
    cam_index = request.args.get("cam")
    cam, error, code = get_cam_or_400(cam_index, cams)
    if error:
        return error, code
    code1, out1, err1 = run_v4l2(["v4l2-ctl", "-d", cam.device, "-D"])
    if code1 != 0:
        return jsonify({"error": err1 or out1 or "Failed to fetch device info"}), 500
    return jsonify({"info": out1})


@bp.route("/api/v4l2/debug")
def api_debug():
    """Debug endpoint to see raw v4l2-ctl output"""
    cams = current_app.config["cams"]
    cam_index = request.args.get("cam")
    cam, error, code = get_cam_or_400(cam_index, cams)
    if error:
        return error, code

    code1, out1, err1 = run_v4l2(["v4l2-ctl", "-d", cam.device, "--list-ctrls"])
    code2, out2, err2 = run_v4l2(
        ["v4l2-ctl", "-d", cam.device, "--list-ctrls-menus"]
    )

    menus = parse_ctrl_menus(out2) if code2 == 0 else {}

    return jsonify(
        {
            "device": cam.device,
            "list_ctrls": {"code": code1, "stdout": out1, "stderr": err1},
            "list_ctrls_menus": {"code": code2, "stdout": out2, "stderr": err2},
            "parsed_menus": menus,
        }
    )


def register_routes(app) -> None:
    app.register_blueprint(bp)
