# API Reference

## Cameras

### `GET /api/cams`
Returns the detected camera list and stream metadata.

### `GET /api/v4l2/ctrls?cam=<cam_id>`
Returns the controls available on the selected camera.

### `POST /api/v4l2/set?cam=<cam_id>`
Applies control value changes. Body example:

```json
{
  "brightness": 120,
  "focus_auto": 0
}
```

### `GET /api/v4l2/info?cam=<cam_id>`
Returns device information from `v4l2-ctl -D`.

### `GET /api/v4l2/debug?cam=<cam_id>`
Returns raw `v4l2-ctl` output to help debug control parsing issues.
