#!/usr/bin/env python3
"""Example of using v4l2-ctrls programmatically."""

from v4l2_ctrls.app import create_app
from v4l2_ctrls.camera import build_cams, detect_devices
from v4l2_ctrls.utils import parse_stream_prefixes


if __name__ == "__main__":
    devices = detect_devices()
    prefixes = parse_stream_prefixes([])
    streams = {
        "webrtc": "{prefix}webrtc",
        "mjpg": "{prefix}stream.mjpg",
        "snapshot": "{prefix}snapshot.jpg",
    }
    cams = build_cams(devices, prefixes, streams, True)
    app = create_app({"camera_url": "http://127.0.0.1/", "cams": cams, "port": 5000})
    app.run(host="0.0.0.0", port=5000)
