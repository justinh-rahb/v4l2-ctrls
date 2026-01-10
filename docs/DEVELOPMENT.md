# Development

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run locally

```sh
python3 v4l2-ctrls.py
```

## Notes

- The app shells out to `v4l2-ctl`; ensure it is installed and available on your PATH.
- UI assets live in `static/` and `templates/`.
