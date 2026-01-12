# Installer

## One-line install

```bash
curl -sSL https://raw.githubusercontent.com/justinh-rahb/v4l2-ctrls/refs/heads/main/install.sh | sudo bash
```

To install a different branch, tag, or commit, set `INSTALL_REF`:

```bash
curl -sSL https://raw.githubusercontent.com/justinh-rahb/v4l2-ctrls/refs/heads/main/install.sh | sudo INSTALL_REF=feature-branch bash
```

## What the installer does

1. ✅ Ensures `v4l2-ctl` is available (installs `v4l-utils` if needed)
2. ✅ Verifies Python 3 and pip (installs `python3-pip` + `python3-venv` if missing)
3. ✅ Downloads the `INSTALL_REF` archive to `~/v4l2-ctrls` (backs up any existing install)
4. ✅ Creates a Python virtual environment and installs requirements
5. ✅ Creates a systemd service for the current sudo user
6. ✅ Prompts to enable/start the service

> The installer must be run as root. It uses the sudo user to determine the install path and service user.

## Defaults created by the installer

- **Install path**: `/home/<user>/v4l2-ctrls`
- **Service**: `/etc/systemd/system/v4l2-ctrls.service`
- **Bind address**: `0.0.0.0`
- **Port**: `5000`
- **Camera URL**: `http://127.0.0.1/` (app default)
- **Stream paths** (app defaults):
  - MJPG: `{prefix}stream.mjpg`
  - Snapshot: `{prefix}snapshot.jpg`
  - WebRTC: `{prefix}webrtc`

Access the UI after install:

```
http://<your-pi-ip>:5000
```

## Customize the service

Edit the service file:

```bash
sudo nano /etc/systemd/system/v4l2-ctrls.service
```

Example with custom device and stream URLs:

```ini
ExecStart=/home/pi/v4l2-ctrls/venv/bin/python3 /home/pi/v4l2-ctrls/v4l2-ctrls.py \
  --device /dev/video2 \
  --camera-url "http://10.0.3.229:8081/" \
  --stream-path-mjpg "{prefix}?action=stream" \
  --stream-path-snapshot "{prefix}?action=snapshot" \
  --host 0.0.0.0 \
  --port 5000
```

### Common MainsailOS/FluiddPi streamer defaults

If you're using the standard MainsailOS/FluiddPi webcam endpoints (often via crowsnest), these settings are typical:

```ini
ExecStart=/home/pi/v4l2-ctrls/venv/bin/python3 /home/pi/v4l2-ctrls/v4l2-ctrls.py \
  --camera-url "http://127.0.0.1/" \
  --stream-prefix /dev/video0=/webcam/ \
  --stream-path-mjpg "{prefix}?action=stream" \
  --stream-path-snapshot "{prefix}?action=snapshot" \
  --host 0.0.0.0 \
  --port 5000
```

Then reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart v4l2-ctrls
```

## Managing the service

```bash
# Check status
sudo systemctl status v4l2-ctrls

# View logs
sudo journalctl -u v4l2-ctrls -f

# Restart
sudo systemctl restart v4l2-ctrls

# Stop
sudo systemctl stop v4l2-ctrls

# Start
sudo systemctl start v4l2-ctrls

# Disable (stop auto-start on boot)
sudo systemctl disable v4l2-ctrls

# Enable (auto-start on boot)
sudo systemctl enable v4l2-ctrls
```

## Uninstall

```bash
sudo systemctl stop v4l2-ctrls
sudo systemctl disable v4l2-ctrls
sudo rm /etc/systemd/system/v4l2-ctrls.service
sudo rm -rf /home/<user>/v4l2-ctrls
sudo systemctl daemon-reload
```

## Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u v4l2-ctrls -n 50

# Check if device exists
ls -la /dev/video*

# Test manually
cd /home/<user>/v4l2-ctrls
source venv/bin/activate
python3 v4l2-ctrls.py --device /dev/video0 --camera-url "http://127.0.0.1/"
```

### Camera preview not working

1. Make sure your camera streamer is running.
2. Check the camera URL in the web UI matches your setup.
3. Test the URLs directly in a browser (use your configured base URL/prefix):
   - MJPG: `http://your-pi-ip/stream.mjpg`
   - Snapshot: `http://your-pi-ip/snapshot.jpg`

### Port 5000 already in use

Change the port in the service file to something else (e.g., 5001):

```bash
sudo nano /etc/systemd/system/v4l2-ctrls.service
# Change --port 5000 to --port 5001
sudo systemctl daemon-reload
sudo systemctl restart v4l2-ctrls
```
