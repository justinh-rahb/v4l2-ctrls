"""Application factory and CLI entrypoint for v4l2-ctrls."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict

from flask import Flask

from .camera import build_cams, detect_devices
from .routes import register_routes
from .utils import log, parse_stream_prefixes


def create_app(config: Dict | None = None) -> Flask:
    base_dir = os.path.dirname(__file__)
    template_dir = os.path.abspath(os.path.join(base_dir, "..", "templates"))
    static_dir = os.path.abspath(os.path.join(base_dir, "..", "static"))
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    if config:
        app.config.update(config)
    register_routes(app)
    return app


def run_socket_server(app: Flask, sock_path: str) -> None:
    """Run Unix socket server that proxies API requests."""
    import socket

    if os.path.exists(sock_path):
        os.unlink(sock_path)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(sock_path)
    sock.listen(5)
    os.chmod(sock_path, 0o666)

    log(f"Socket server listening on {sock_path}")

    try:
        while True:
            conn, _ = sock.accept()
            try:
                data = b""
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if b"\n" in data:
                        break

                if data:
                    req = json.loads(data.decode().strip())

                    with app.test_client() as client:
                        method = req.get("method", "GET").upper()
                        path = req.get("path", "/")
                        query = req.get("query", {})
                        body = req.get("body", {})

                        if query:
                            from urllib.parse import urlencode

                            path = f"{path}?{urlencode(query)}"

                        if method == "POST":
                            response = client.post(path, json=body)
                        else:
                            response = client.get(path)

                        result = {
                            "status": response.status_code,
                            "headers": dict(response.headers),
                            "body": response.get_data(as_text=True),
                        }

                        if response.content_type and "application/json" in response.content_type:
                            try:
                                result["body"] = json.loads(result["body"])
                            except json.JSONDecodeError:
                                pass

                        conn.sendall((json.dumps(result) + "\n").encode())
            except Exception as exc:
                log(f"Socket request error: {exc}")
                error_response = {"status": 500, "body": {"error": str(exc)}}
                try:
                    conn.sendall((json.dumps(error_response) + "\n").encode())
                except Exception:
                    pass
            finally:
                conn.close()
    finally:
        sock.close()
        if os.path.exists(sock_path):
            os.unlink(sock_path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="V4L2 control UI")
    parser.add_argument("--device", action="append", default=[], help="V4L2 device path")
    parser.add_argument("--host", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, help="Port to bind (default: 5000)")
    parser.add_argument("--socket", help="Unix socket path (if set, runs socket server)")
    parser.add_argument(
        "--camera-url", default="http://127.0.0.1/", help="Camera stream base URL"
    )
    parser.add_argument("--base-url", dest="camera_url", help=argparse.SUPPRESS)
    parser.add_argument(
        "--app-base-url", default="", help="Base URL path for UI routing (optional)"
    )
    parser.add_argument("--title", default="", help="Optional page title")
    parser.add_argument(
        "--stream-prefix",
        action="append",
        default=[],
        help=(
            "Override stream prefix per camera (format: key=/path/ where key is device path, basename, or cam id)"
        ),
    )
    parser.add_argument(
        "--stream-path-webrtc",
        default="{prefix}webrtc",
        help="Template for WebRTC stream path (default: {prefix}webrtc)",
    )
    parser.add_argument(
        "--stream-path-mjpg",
        default="{prefix}stream.mjpg",
        help="Template for MJPG stream path (default: {prefix}stream.mjpg)",
    )
    parser.add_argument(
        "--stream-path-snapshot",
        default="{prefix}snapshot.jpg",
        help="Template for snapshot stream path (default: {prefix}snapshot.jpg)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    devices = args.device or detect_devices()
    if not devices:
        raise SystemExit("No devices found. Use --device to specify V4L2 devices.")

    if "--base-url" in sys.argv:
        log("Warning: --base-url is deprecated, use --camera-url instead.")

    app_base_url = args.app_base_url.strip()
    if app_base_url and not app_base_url.endswith("/"):
        app_base_url += "/"

    prefixes = parse_stream_prefixes(args.stream_prefix)
    stream_templates = {
        "webrtc": args.stream_path_webrtc,
        "mjpg": args.stream_path_mjpg,
        "snapshot": args.stream_path_snapshot,
    }
    use_default_mapping = args.camera_url == "http://127.0.0.1/"
    cams = build_cams(devices, prefixes, stream_templates, use_default_mapping)

    start_socket = bool(args.socket)
    start_tcp = args.host is not None or args.port is not None or not start_socket

    if not start_socket and not start_tcp:
        raise SystemExit("No listener configured. Provide --socket and/or --host/--port.")

    host = args.host if args.host is not None else "0.0.0.0"
    port = args.port if args.port is not None else 5000

    config = {
        "cams": cams,
        "camera_url": args.camera_url,
        "app_base_url": app_base_url,
        "title": args.title,
        "port": port,
        "socket_mode": start_socket and not start_tcp,
    }

    app = create_app(config)

    if start_socket and start_tcp:
        import threading

        socket_thread = threading.Thread(
            target=run_socket_server, args=(app, args.socket), daemon=True
        )
        socket_thread.start()
        log(f"Starting v4l2-ctrls socket server at {args.socket} for {len(cams)} camera(s)")
        log(f"Starting v4l2-ctrls HTTP server on {host}:{port} for {len(cams)} camera(s)")
        app.run(host=host, port=port, threaded=True)
    elif start_socket:
        log(f"Starting v4l2-ctrls socket server at {args.socket} for {len(cams)} camera(s)")
        run_socket_server(app, args.socket)
    else:
        log(f"Starting v4l2-ctrls HTTP server on {host}:{port} for {len(cams)} camera(s)")
        app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
