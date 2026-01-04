# V4L2 Controls Quick Install

## One-Line Install

```bash
curl -sSL https://raw.githubusercontent.com/justinh-rahb/v4l2-mpp/refs/heads/installer/apps/v4l2-ctrls/install.sh | sudo bash
```

## What It Does

1. ✅ Checks for and installs v4l-utils (if needed)
2. ✅ Checks for Python 3 and pip
3. ✅ Downloads v4l2-ctrls.py to `/home/pi/v4l2-ctrls/`
4. ✅ Creates Python virtual environment
5. ✅ Installs Flask in the venv
6. ✅ Creates systemd service
7. ✅ Prompts to enable and start the service

## Access After Install

```
http://<your-pi-ip>:5000
```

## Default Configuration

- **Device**: `/dev/video0`
- **Camera URL**: `/webcam/`
- **MJPG Stream**: `?action=stream`
- **Snapshot**: `?action=snapshot`
- **Port**: `5000`

This works with most common Klipper camera setups like:
- crowsnest
- mjpg-streamer
- camera-streamer

## Customizing

Edit the service file:
```bash
sudo nano /etc/systemd/system/v4l2-ctrls.service
```

Change the ExecStart line to use your device/URLs:
```ini
ExecStart=/home/pi/v4l2-ctrls/venv/bin/python3 /home/pi/v4l2-ctrls/v4l2-ctrls.py \
  --device /dev/video2 \
  --camera-url "http://10.0.3.229:8081/" \
  --stream-path-mjpg "?action=stream" \
  --stream-path-snapshot "?action=snapshot" \
  --host 0.0.0.0 \
  --port 5000
```

Then reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart v4l2-ctrls
```

## Managing the Service

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
sudo rm -rf /home/pi/v4l2-ctrls
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
cd /home/pi/v4l2-ctrls
source venv/bin/activate
python3 v4l2-ctrls.py --device /dev/video0 --camera-url "/webcam/" --stream-path-mjpg "?action=stream" --stream-path-snapshot "?action=snapshot"
```

### Camera preview not working
1. Make sure your camera streamer is running
2. Check the camera URL in the web UI matches your setup
3. Test the URLs directly in a browser:
   - MJPG: `http://your-pi-ip/webcam/?action=stream`
   - Snapshot: `http://your-pi-ip/webcam/?action=snapshot`

### Port 5000 already in use
Change the port in the service file to something else (e.g., 5001):
```bash
sudo nano /etc/systemd/system/v4l2-ctrls.service
# Change --port 5000 to --port 5001
sudo systemctl daemon-reload
sudo systemctl restart v4l2-ctrls
```

## Manual Installation

If you prefer to install manually without the script:

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y v4l-utils python3 python3-pip python3-venv

# Create directory
mkdir -p /home/pi/v4l2-ctrls
cd /home/pi/v4l2-ctrls

# Download script
curl -sSL https://raw.githubusercontent.com/justinh-rahb/v4l2-mpp/refs/heads/main/apps/v4l2-ctrls/v4l2-ctrls.py -o v4l2-ctrls.py
chmod +x v4l2-ctrls.py

# Create venv and install Flask
python3 -m venv venv
source venv/bin/activate
pip install Flask
deactivate

# Create service file
sudo nano /etc/systemd/system/v4l2-ctrls.service
# (paste the service file contents from above)

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable v4l2-ctrls
sudo systemctl start v4l2-ctrls
```

## Requirements

- Debian/Ubuntu-based system (Raspberry Pi OS, MainsailOS, FluiddPi, etc.)
- Python 3.7+
- v4l-utils (automatically installed)
- systemd (standard on most Linux distros)

## Compatibility

Tested and working on:
- Raspberry Pi OS (Bullseye, Bookworm)
- MainsailOS
- FluiddPi
- Any Debian/Ubuntu-based Klipper distribution

## Support

For issues, feature requests, or questions:
https://github.com/justinh-rahb/v4l2-mpp/issues