#!/usr/bin/env python3
"""
Touch-friendly V4L2 controls UI with embedded streamer preview.

Usage examples:
  python3 apps/v4l2-ctrls/v4l2-ctrls.py --device /dev/video11
  python3 apps/v4l2-ctrls/v4l2-ctrls.py --device /dev/video11 --device /dev/video12 --port 5001 --base-url http://127.0.0.1/

Requires:
  - Flask (pip install flask)
  - v4l2-ctl in PATH
"""

import argparse
import glob
import json
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from flask import Flask, jsonify, request

APP = Flask(__name__)

CONTROL_ORDER = [
    "focus_auto",
    "focus_absolute",
    "exposure_auto",
    "exposure_absolute",
    "white_balance_temperature_auto",
    "white_balance_temperature",
    "brightness",
    "contrast",
    "saturation",
    "sharpness",
    "gain",
]

HTML_PAGE = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #0f1115;
      --panel: #1b1f2a;
      --panel-strong: #222838;
      --tile: #1c2230;
      --accent: #63b3ff;
      --accent-strong: #4ea1ff;
      --text: #e6e9ef;
      --muted: #9aa3b2;
      --border: #2b3040;
      --shadow: 0 12px 30px rgba(0, 0, 0, 0.35);
      --gradient: linear-gradient(145deg, rgba(78, 161, 255, 0.12), rgba(0, 0, 0, 0));
    }}
    [data-theme="light"] {{
      color-scheme: light;
      --bg: #f6f7fb;
      --panel: #ffffff;
      --panel-strong: #f0f2f7;
      --tile: #ffffff;
      --accent: #3d7bff;
      --accent-strong: #2f62d8;
      --text: #1a1f2b;
      --muted: #5c677d;
      --border: #e3e6ef;
      --shadow: 0 12px 30px rgba(30, 46, 90, 0.12);
      --gradient: linear-gradient(145deg, rgba(61, 123, 255, 0.1), rgba(255, 255, 255, 0));
    }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    header {{
      padding: 16px 20px;
      background: var(--panel);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }}
    header h1 {{
      margin: 0;
      font-size: 20px;
    }}
    main {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
      padding: 16px;
    }}
    .panel {{
      background: var(--panel);
      border-radius: 16px;
      padding: 16px;
      box-shadow: var(--shadow);
      border: 1px solid var(--border);
    }}
    .panel--preview {{
      background: var(--panel);
      background-image: var(--gradient);
    }}
    .panel h2 {{
      margin-top: 0;
      font-size: 16px;
    }}
    label {{
      display: block;
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 6px;
    }}
    select, input[type=\"text\"], input[type=\"number\"], input[type=\"range\"] {{
      width: 100%;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: var(--panel-strong);
      color: var(--text);
      font-size: 14px;
      box-sizing: border-box;
    }}
    .row {{
      display: flex;
      gap: 8px;
      align-items: center;
    }}
    .row input[type=\"range\"] {{
      flex: 1;
    }}
    button {{
      width: 100%;
      padding: 12px;
      border-radius: 10px;
      background: var(--accent);
      color: #0b1020;
      font-weight: 600;
      border: none;
      cursor: pointer;
      transition: transform 0.1s ease, box-shadow 0.2s ease;
    }}
    button:hover {{
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2);
    }}
    button:disabled {{
      opacity: 0.6;
      cursor: not-allowed;
    }}
    .note {{
      margin-top: 8px;
      font-size: 13px;
      color: #f5c56b;
    }}
    .preview {{
      width: 100%;
      aspect-ratio: 16/9;
      background: #0b0e14;
      border-radius: 14px;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 1px solid var(--border);
    }}
    .preview iframe, .preview img {{
      width: 100%;
      height: 100%;
      object-fit: contain;
      border: 0;
    }}
    .control {{
      background: var(--tile);
      padding: 14px;
      border-radius: 14px;
      border: 1px solid var(--border);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.02);
    }}
    .control-title {{
      font-size: 14px;
      margin-bottom: 6px;
    }}
    .control-grid {{
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }}
    .section-title {{
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin: 18px 0 10px;
    }}
    .slider-row {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: center;
    }}
    input[type=\"range\"] {{
      height: 36px;
      accent-color: var(--accent-strong);
    }}
    .control input[type=\"number\"] {{
      margin-top: 10px;
    }}
    .value-pill {{
      min-width: 62px;
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--panel-strong);
      border: 1px solid var(--border);
      text-align: center;
      font-weight: 600;
      font-size: 13px;
      color: var(--text);
    }}
    .status {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      font-size: 12px;
      background: var(--panel-strong);
      padding: 10px;
      border-radius: 12px;
      white-space: pre-wrap;
      min-height: 80px;
      border: 1px solid var(--border);
    }}
    .action-bar {{
      position: sticky;
      bottom: 0;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      padding-top: 14px;
      background: linear-gradient(180deg, rgba(0, 0, 0, 0), var(--panel) 60%);
    }}
    .ghost {{
      background: transparent;
      color: var(--text);
      border: 1px solid var(--border);
    }}
    .theme-select {{
      min-width: 140px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <div style=\"display:flex; gap:8px; align-items:center;\">
      <label for=\"theme-select\" style=\"margin-bottom:0;\">Theme</label>
      <select id=\"theme-select\" class=\"theme-select\">
        <option value=\"system\">System</option>
        <option value=\"dark\">Dark</option>
        <option value=\"light\">Light</option>
      </select>
    </div>
  </header>
  <main>
    <section class=\"panel panel--preview\">
      <h2>Preview</h2>
      <label for=\"base-url\">Streamer base URL</label>
      <input id=\"base-url\" type=\"text\" placeholder=\"http://127.0.0.1/\" />
      <div class=\"row\" style=\"margin-top:12px;\">
        <div style=\"flex:1;\">
          <label for=\"camera-select\">Camera</label>
          <select id=\"camera-select\"></select>
        </div>
        <div style=\"flex:1;\">
          <label for=\"preview-mode\">Preview mode</label>
          <select id=\"preview-mode\">
            <option value=\"webrtc\">WebRTC</option>
            <option value=\"mjpg\">MJPG</option>
            <option value=\"snapshot\">Snapshot</option>
          </select>
        </div>
      </div>
      <div class=\"preview\" id=\"preview\" style=\"margin-top:12px;\"></div>
      <div class=\"note\">Changes are not persisted; persistence is handled by the streamer/service.</div>
    </section>
    <section class=\"panel\">
      <h2>Controls</h2>
      <div id=\"controls\"></div>
      <div class=\"action-bar\">
        <button id=\"apply\">Apply changes</button>
        <button id=\"reset\" class=\"ghost\">Reset</button>
      </div>
    </section>
    <section class=\"panel\">
      <h2>Status</h2>
      <div class=\"status\" id=\"status\">Ready.</div>
    </section>
  </main>
  <script>
    const baseUrlInput = document.getElementById('base-url');
    const cameraSelect = document.getElementById('camera-select');
    const previewMode = document.getElementById('preview-mode');
    const preview = document.getElementById('preview');
    const controlsContainer = document.getElementById('controls');
    const applyButton = document.getElementById('apply');
    const resetButton = document.getElementById('reset');
    const statusBox = document.getElementById('status');
    const themeSelect = document.getElementById('theme-select');

    let cams = [];
    let currentControls = [];
    let lastControls = [];

    const GROUPS = [
      {{ key: 'focus', title: 'Focus', match: name => name.includes('focus') }},
      {{ key: 'exposure', title: 'Exposure', match: name => name.includes('exposure') }},
      {{ key: 'white_balance', title: 'White Balance', match: name => name.includes('white_balance') }},
      {{ key: 'color', title: 'Color', match: name => ['brightness', 'contrast', 'saturation', 'hue', 'gain', 'gamma'].some(t => name.includes(t)) }},
      {{ key: 'image', title: 'Image', match: name => ['sharpness', 'zoom', 'pan', 'tilt'].some(t => name.includes(t)) }},
    ];

    function logStatus(message) {{
      statusBox.textContent = message;
    }}

    function applyTheme(theme) {{
      if (theme === 'system') {{
        document.documentElement.removeAttribute('data-theme');
      }} else {{
        document.documentElement.setAttribute('data-theme', theme);
      }}
      localStorage.setItem('v4l2ctrls-theme', theme);
    }}

    function getBaseUrl() {{
      const url = baseUrlInput.value.trim();
      if (!url.endsWith('/')) {{
        return url + '/';
      }}
      return url;
    }}

    function updatePreview() {{
      const cam = Number(cameraSelect.value);
      const mode = previewMode.value;
      const camInfo = cams.find(c => c.cam === cam);
      if (!camInfo) {{
        preview.innerHTML = '<div>No camera selected.</div>';
        return;
      }}
      const base = getBaseUrl();
      let path = '';
      if (mode === 'webrtc') {{
        path = camInfo.prefix + 'webrtc';
        preview.innerHTML = `<iframe src="${{base}}${{path}}"></iframe>`;
      }} else if (mode === 'mjpg') {{
        path = camInfo.prefix + 'stream.mjpg';
        preview.innerHTML = `<img src="${{base}}${{path}}" alt="MJPG stream" />`;
      }} else {{
        const epoch = Date.now();
        path = camInfo.prefix + 'snapshot.jpg?t=' + epoch;
        preview.innerHTML = `<img src="${{base}}${{path}}" alt="Snapshot" />`;
      }}
      localStorage.setItem('v4l2ctrls-base-url', baseUrlInput.value);
      localStorage.setItem('v4l2ctrls-preview-mode', mode);
      localStorage.setItem('v4l2ctrls-cam', String(cam));
    }}

    function buildControl(control) {{
      const wrapper = document.createElement('div');
      wrapper.className = 'control';
      const title = document.createElement('div');
      title.className = 'control-title';
      title.textContent = control.name;
      wrapper.appendChild(title);

      if (control.type === 'int') {{
        const row = document.createElement('div');
        row.className = 'slider-row';
        const range = document.createElement('input');
        range.type = 'range';
        range.min = control.min;
        range.max = control.max;
        range.step = control.step || 1;
        range.value = control.value;
        range.dataset.control = control.name;
        range.dataset.role = 'value';
        const pill = document.createElement('div');
        pill.className = 'value-pill';
        pill.textContent = String(control.value);
        const number = document.createElement('input');
        number.type = 'number';
        number.min = control.min;
        number.max = control.max;
        number.step = control.step || 1;
        number.value = control.value;
        number.dataset.control = control.name;
        number.dataset.role = 'value';
        range.addEventListener('input', () => {{
          number.value = range.value;
          pill.textContent = range.value;
        }});
        number.addEventListener('input', () => {{
          range.value = number.value;
          pill.textContent = number.value;
        }});
        row.appendChild(range);
        row.appendChild(pill);
        wrapper.appendChild(row);
        wrapper.appendChild(number);
      }} else if (control.type === 'bool') {{
        const select = document.createElement('select');
        select.dataset.control = control.name;
        select.dataset.role = 'value';
        const off = new Option('Off', '0');
        const on = new Option('On', '1');
        select.add(off);
        select.add(on);
        select.value = String(control.value || 0);
        wrapper.appendChild(select);
      }} else if (control.type === 'menu') {{
        const select = document.createElement('select');
        select.dataset.control = control.name;
        select.dataset.role = 'value';
        (control.menu || []).forEach(item => {{
          const opt = new Option(item.label, String(item.value));
          select.add(opt);
        }});
        select.value = String(control.value || 0);
        wrapper.appendChild(select);
      }} else {{
        const span = document.createElement('div');
        span.textContent = `Unsupported control type: ${{control.type}}`;
        wrapper.appendChild(span);
      }}

      return wrapper;
    }}

    function groupFor(name) {{
      for (const group of GROUPS) {{
        if (group.match(name)) {{
          return group.key;
        }}
      }}
      return 'other';
    }}

    function renderControls(controls) {{
      controlsContainer.innerHTML = '';
      const buckets = {{}};
      controls.forEach(control => {{
        const key = groupFor(control.name);
        if (!buckets[key]) {{
          buckets[key] = [];
        }}
        buckets[key].push(control);
      }});
      const ordered = [...GROUPS.map(group => group.key), 'other'];
      ordered.forEach(key => {{
        const items = buckets[key] || [];
        if (!items.length) {{
          return;
        }}
        const title = document.createElement('div');
        const group = GROUPS.find(g => g.key === key);
        title.className = 'section-title';
        title.textContent = group ? group.title : 'Other';
        controlsContainer.appendChild(title);
        const grid = document.createElement('div');
        grid.className = 'control-grid';
        items.forEach(control => {{
          grid.appendChild(buildControl(control));
        }});
        controlsContainer.appendChild(grid);
      }});
    }}

    async function fetchControls(cam) {{
      logStatus('Loading controls...');
      try {{
        const response = await fetch(`/api/v4l2/ctrls?cam=${{cam}}`);
        const data = await response.json();
        if (!response.ok) {{
          throw new Error(data.error || 'Failed to load controls');
        }}
        currentControls = data.controls || data;
        lastControls = JSON.parse(JSON.stringify(currentControls));
        renderControls(currentControls);
        logStatus(`Loaded ${{currentControls.length}} controls.`);
      }} catch (err) {{
        renderControls([]);
        logStatus(`Error: ${{err.message}}`);
      }}
    }}

    async function fetchInfo(cam) {{
      try {{
        const response = await fetch(`/api/v4l2/info?cam=${{cam}}`);
        if (!response.ok) {{
          const data = await response.json();
          throw new Error(data.error || 'Failed to fetch info');
        }}
        const data = await response.json();
        logStatus(data.info || 'No info.');
      }} catch (err) {{
        logStatus(`Error: ${{err.message}}`);
      }}
    }}

    function controlMap(controls) {{
      const map = {{}};
      (controls || []).forEach(control => {{
        map[control.name] = control;
      }});
      return map;
    }}

    async function applyChanges() {{
      const cam = Number(cameraSelect.value);
      const payload = {{}};
      const previous = controlMap(lastControls);
      controlsContainer.querySelectorAll('[data-control][data-role=\"value\"]').forEach(el => {{
        const name = el.dataset.control;
        const parsed = parseInt(el.value, 10);
        if (Number.isNaN(parsed)) {{
          return;
        }}
        const before = previous[name];
        if (!before || before.value !== parsed) {{
          payload[name] = parsed;
        }}
      }});
      if (!Object.keys(payload).length) {{
        logStatus('No changes to apply.');
        return;
      }}
      applyButton.disabled = true;
      try {{
        const response = await fetch(`/api/v4l2/set?cam=${{cam}}`, {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify(payload),
        }});
        const data = await response.json();
        if (!response.ok || !data.ok) {{
          throw new Error(data.stderr || data.error || 'Failed to apply controls');
        }}
        logStatus(`Applied: ${{JSON.stringify(data.applied, null, 2)}}\n${{data.stdout || ''}}`.trim());
        const updated = controlMap(currentControls);
        Object.entries(data.applied || {{}}).forEach(([name, value]) => {{
          if (updated[name]) {{
            updated[name].value = value;
          }}
        }});
        lastControls = JSON.parse(JSON.stringify(currentControls));
        if (previewMode.value === 'snapshot') {{
          updatePreview();
        }} else {{
          const base = getBaseUrl();
          const camInfo = cams.find(c => c.cam === cam);
          if (camInfo) {{
            const snap = `${{base}}${{camInfo.prefix}}snapshot.jpg?t=${{Date.now()}}`;
            const img = new Image();
            img.src = snap;
          }}
        }}
      }} catch (err) {{
        logStatus(`Error: ${{err.message}}`);
      }} finally {{
        applyButton.disabled = false;
      }}
    }}

    async function init() {{
      const storedTheme = localStorage.getItem('v4l2ctrls-theme') || 'system';
      themeSelect.value = storedTheme;
      applyTheme(storedTheme);
      const storedBase = localStorage.getItem('v4l2ctrls-base-url');
      baseUrlInput.value = storedBase || '{base_url}';
      const camsResp = await fetch('/api/cams');
      cams = await camsResp.json();
      cameraSelect.innerHTML = '';
      cams.forEach(cam => {{
        const opt = new Option(`Cam ${{cam.cam}}`, String(cam.cam));
        cameraSelect.add(opt);
      }});
      const storedCam = Number(localStorage.getItem('v4l2ctrls-cam'));
      if (storedCam && cams.find(c => c.cam === storedCam)) {{
        cameraSelect.value = String(storedCam);
      }}
      const storedMode = localStorage.getItem('v4l2ctrls-preview-mode');
      if (storedMode) {{
        previewMode.value = storedMode;
      }}
      updatePreview();
      await fetchControls(Number(cameraSelect.value));
      await fetchInfo(Number(cameraSelect.value));
    }}

    baseUrlInput.addEventListener('change', updatePreview);
    previewMode.addEventListener('change', updatePreview);
    themeSelect.addEventListener('change', () => {{
      applyTheme(themeSelect.value);
    }});
    cameraSelect.addEventListener('change', async () => {{
      updatePreview();
      await fetchControls(Number(cameraSelect.value));
      await fetchInfo(Number(cameraSelect.value));
    }});
    applyButton.addEventListener('click', applyChanges);
    resetButton.addEventListener('click', () => {{
      if (!lastControls.length) {{
        logStatus('No controls to reset.');
        return;
      }}
      renderControls(lastControls);
      logStatus('Reset to last loaded values.');
    }});

    init().catch(err => {{
      logStatus(`Error: ${{err.message}}`);
    }});
  </script>
</body>
</html>
"""


@dataclass(frozen=True)
class Camera:
    cam: int
    device: str
    prefix: str


def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def detect_devices(limit: int = 8) -> List[str]:
    devices = sorted(glob.glob("/dev/video*"))
    return devices[:limit]


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


def normalize_type(ctrl_type: Optional[str]) -> str:
    if not ctrl_type:
        return "unknown"
    if ctrl_type == "bool":
        return "bool"
    if ctrl_type.startswith("int"):
        return "int"
    return ctrl_type


def get_int_from_parts(parts: List[str], field: str) -> Optional[int]:
    token = next((p for p in parts if p.startswith(f"{field}=")), None)
    if not token:
        return None
    try:
        return int(token.split("=", 1)[1])
    except ValueError:
        return None


def parse_ctrls(output: str) -> List[Dict[str, Optional[int]]]:
    controls = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("Error"):
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
            }
        )
    return controls


def parse_ctrl_menus(output: str) -> Dict[str, List[Dict[str, str]]]:
    menus: Dict[str, List[Dict[str, str]]] = {}
    current = None
    for line in output.splitlines():
        if not line.strip():
            continue
        if line and not line.startswith(" "):
            name = line.split()[0]
            current = name
            menus.setdefault(current, [])
            continue
        if current is None:
            continue
        menu_line = line.strip()
        if ":" in menu_line:
            value_str, label = menu_line.split(":", 1)
            try:
                value = int(value_str.strip())
            except ValueError:
                continue
            menus[current].append({"value": value, "label": label.strip()})
    return menus


def sort_controls(controls: List[Dict[str, Optional[int]]]) -> List[Dict[str, Optional[int]]]:
    order_map = {name: idx for idx, name in enumerate(CONTROL_ORDER)}
    indexed = list(enumerate(controls))
    def sort_key(item: Tuple[int, Dict[str, Optional[int]]]) -> Tuple[int, int]:
        original_idx, ctrl = item
        idx = order_map.get(ctrl["name"], len(CONTROL_ORDER))
        return (idx, original_idx)
    return [ctrl for _, ctrl in sorted(indexed, key=sort_key)]


def get_cam_or_400(cam_index: str, cams: List[Camera]):
    try:
        cam = int(cam_index)
    except (TypeError, ValueError) as exc:
        log(f"Invalid cam index {cam_index!r}: {exc}")
        return None, jsonify({"error": "Invalid camera index"}), 400
    if cam < 1 or cam > len(cams):
        return None, jsonify({"error": "Camera out of range"}), 400
    return cams[cam - 1], None, None


@APP.route("/")
def index():
    title = APP.config.get("title") or "V4L2 Controls"
    base_url = APP.config.get("base_url")
    return HTML_PAGE.format(title=title, base_url=base_url)


@APP.route("/api/cams")
def api_cams():
    cams = APP.config["cams"]
    return jsonify([{"cam": cam.cam, "device": cam.device, "prefix": cam.prefix} for cam in cams])


@APP.route("/api/v4l2/ctrls")
def api_ctrls():
    cams = APP.config["cams"]
    cam_index = request.args.get("cam")
    cam, error, code = get_cam_or_400(cam_index, cams)
    if error:
        return error, code
    code1, out1, err1 = run_v4l2(["v4l2-ctl", "-d", cam.device, "--list-ctrls"])
    if code1 != 0:
        return jsonify({"error": err1 or out1 or "Failed to list controls"}), 500
    controls = parse_ctrls(out1)
    code2, out2, err2 = run_v4l2(["v4l2-ctl", "-d", cam.device, "--list-ctrls-menus"])
    if code2 == 0:
        menus = parse_ctrl_menus(out2)
        for ctrl in controls:
            if ctrl["name"] in menus:
                ctrl["menu"] = menus[ctrl["name"]]
                ctrl["type"] = "menu"
    controls = sort_controls(controls)
    return jsonify({"controls": controls})


@APP.route("/api/v4l2/set", methods=["POST"])
def api_set():
    cams = APP.config["cams"]
    cam_index = request.args.get("cam")
    cam, error, code = get_cam_or_400(cam_index, cams)
    if error:
        return error, code
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400
    code1, out1, err1 = run_v4l2(["v4l2-ctl", "-d", cam.device, "--list-ctrls"])
    if code1 != 0:
        return jsonify({"ok": False, "stdout": out1, "stderr": err1, "code": code1}), 500
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
    return jsonify({"ok": ok, "applied": applied, "stdout": out2, "stderr": err2, "code": code2}), (200 if ok else 500)


@APP.route("/api/v4l2/info")
def api_info():
    cams = APP.config["cams"]
    cam_index = request.args.get("cam")
    cam, error, code = get_cam_or_400(cam_index, cams)
    if error:
        return error, code
    code1, out1, err1 = run_v4l2(["v4l2-ctl", "-d", cam.device, "-D"])
    if code1 != 0:
        return jsonify({"error": err1 or out1 or "Failed to fetch device info"}), 500
    return jsonify({"info": out1})


def build_cams(devices: List[str]) -> List[Camera]:
    cams = []
    for idx, device in enumerate(devices, start=1):
        if idx == 1:
            prefix = "/webcam/"
        else:
            prefix = f"/webcam{idx}/"
        cams.append(Camera(cam=idx, device=device, prefix=prefix))
    return cams


def main() -> None:
    parser = argparse.ArgumentParser(description="V4L2 control UI")
    parser.add_argument("--device", action="append", default=[], help="V4L2 device path")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind")
    parser.add_argument("--base-url", default="http://127.0.0.1/", help="Base URL for preview embeds")
    parser.add_argument("--title", default="", help="Optional page title")
    args = parser.parse_args()

    devices = args.device or detect_devices()
    if not devices:
        raise SystemExit("No devices found. Use --device to specify V4L2 devices.")

    cams = build_cams(devices)
    APP.config["cams"] = cams
    APP.config["base_url"] = args.base_url
    APP.config["title"] = args.title

    log(f"Starting v4l2-ctrls on {args.host}:{args.port} for {len(cams)} camera(s)")
    APP.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
