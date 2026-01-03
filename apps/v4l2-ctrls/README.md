# v4l2-ctrls

Touch-friendly V4L2 control UI that embeds existing streamer previews.

## Requirements

- Python 3
- Flask (`pip install flask`)
- `v4l2-ctl` available in `PATH`

## Usage

```sh
python3 apps/v4l2-ctrls/v4l2-ctrls.py --device /dev/video11
python3 apps/v4l2-ctrls/v4l2-ctrls.py --device /dev/video11 --device /dev/video12 --port 5001 --base-url http://127.0.0.1/
```

## Endpoints

- `/` UI page
- `/api/cams` camera list and streamer prefixes
- `/api/v4l2/ctrls` v4l2 control list for a camera
- `/api/v4l2/set` apply v4l2 control updates
- `/api/v4l2/info` v4l2 device info
```
