# Architecture

The v4l2-ctrls service is a small Flask application that separates backend V4L2 interactions from frontend UI logic.

## Backend

- `v4l2_ctrls/app.py` builds the Flask app and CLI.
- `v4l2_ctrls/routes.py` defines HTTP endpoints.
- `v4l2_ctrls/camera.py` wraps `v4l2-ctl` calls and parses control output.
- `v4l2_ctrls/utils.py` provides helper utilities for logging and stream formatting.

## Frontend

- `templates/index.html` provides the HTML shell and injects configuration.
- `static/css/style.css` contains the UI styling and theme variables.
- `static/js/controls.js` handles API communication and control rendering.
- `static/js/ui.js` wires up UI interactions and local state.
