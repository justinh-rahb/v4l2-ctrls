"""Flask routes for v4l2-ctrls."""

from __future__ import annotations

from typing import Dict, List, Tuple

from flask import Blueprint, current_app, jsonify, render_template, request

from .camera import (
    apply_controls,
    fetch_controls,
    run_v4l2,
    split_controls_by_precedence,
    validate_values,
)
from .state import load_state, save_state
from .utils import build_storage_prefix

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

    try:
        controls = fetch_controls(cam.device)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
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
    if not data:
        return jsonify({"error": "No controls provided"}), 400
    try:
        controls = fetch_controls(cam.device, include_menus=False)
        validated = validate_values(data, controls)
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    auto_first, remaining = split_controls_by_precedence(validated)
    ok, out, err, code = apply_controls(cam.device, auto_first)
    if not ok:
        return (
            jsonify(
                {
                    "ok": False,
                    "applied": validated,
                    "stdout": out,
                    "stderr": err,
                    "code": code,
                }
            ),
            500,
        )
    ok, out, err, code = apply_controls(cam.device, remaining)
    if ok:
        state_dir = current_app.config.get("state_dir")
        if state_dir:
            state_path = state_dir / f"{cam.cam}.json"
            persisted = load_state(state_path)
            persisted.update(validated)
            save_state(state_path, persisted)
    return (
        jsonify(
            {
                "ok": ok,
                "applied": validated,
                "stdout": out,
                "stderr": err,
                "code": code,
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

    menus = {}
    if code2 == 0:
        from .camera import parse_ctrl_menus

        menus = parse_ctrl_menus(out2)

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
