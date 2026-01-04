#!/bin/bash
# V4L2 Controls Installer for Klipper Printers
# Usage: curl -sSL https://raw.githubusercontent.com/justinh-rahb/v4l2-mpp/refs/heads/installer/apps/v4l2-ctrls/install.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/home/pi/v4l2-ctrls"
SCRIPT_URL="https://raw.githubusercontent.com/justinh-rahb/v4l2-mpp/refs/heads/main/apps/v4l2-ctrls/v4l2-ctrls.py"
SERVICE_NAME="v4l2-ctrls"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}V4L2 Controls Installer${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Please run: sudo bash install.sh"
    exit 1
fi

# Detect the actual user (in case of sudo)
ACTUAL_USER="${SUDO_USER:-pi}"
ACTUAL_HOME=$(getent passwd "$ACTUAL_USER" | cut -d: -f6)
INSTALL_DIR="${ACTUAL_HOME}/v4l2-ctrls"

echo -e "${YELLOW}Installing for user: ${ACTUAL_USER}${NC}"
echo -e "${YELLOW}Install directory: ${INSTALL_DIR}${NC}"
echo ""

# Check for v4l2-ctl
echo -e "${GREEN}[1/7]${NC} Checking for v4l2-ctl..."
if ! command -v v4l2-ctl &> /dev/null; then
    echo -e "${YELLOW}v4l2-ctl not found. Installing v4l-utils...${NC}"
    apt-get update
    apt-get install -y v4l-utils
else
    echo -e "${GREEN}✓ v4l2-ctl found${NC}"
fi

# Check for Python
echo -e "${GREEN}[2/7]${NC} Checking for Python 3..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 not found${NC}"
    echo "Please install Python 3 first"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ ${PYTHON_VERSION}${NC}"

# Check for pip
echo -e "${GREEN}[3/7]${NC} Checking for pip..."
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}pip3 not found. Installing python3-pip...${NC}"
    apt-get update
    apt-get install -y python3-pip python3-venv
else
    echo -e "${GREEN}✓ pip3 found${NC}"
fi

# Create installation directory
echo -e "${GREEN}[4/7]${NC} Creating installation directory..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Download v4l2-ctrls.py
echo -e "${GREEN}[5/7]${NC} Downloading v4l2-ctrls.py..."
curl -sSL "$SCRIPT_URL" -o v4l2-ctrls.py
chmod +x v4l2-ctrls.py
echo -e "${GREEN}✓ Downloaded to ${INSTALL_DIR}/v4l2-ctrls.py${NC}"

# Create virtual environment
echo -e "${GREEN}[6/7]${NC} Setting up Python virtual environment..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}Removing existing venv...${NC}"
    rm -rf venv
fi

python3 -m venv venv
source venv/bin/activate

# Install Flask
echo -e "${GREEN}Installing Flask...${NC}"
pip install --upgrade pip
pip install Flask

deactivate
echo -e "${GREEN}✓ Virtual environment created and Flask installed${NC}"

# Set ownership
chown -R "$ACTUAL_USER:$ACTUAL_USER" "$INSTALL_DIR"

# Create systemd service
echo -e "${GREEN}[7/7]${NC} Creating systemd service..."
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=V4L2 Controls
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
Environment="PATH=${INSTALL_DIR}/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=${INSTALL_DIR}/venv/bin/python3 ${INSTALL_DIR}/v4l2-ctrls.py \\
  --device /dev/video0 \\
  --camera-url "/webcam/" \\
  --stream-path-mjpg "?action=stream" \\
  --stream-path-snapshot "?action=snapshot" \\
  --host 0.0.0.0 \\
  --port 5000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload
echo -e "${GREEN}✓ Service file created${NC}"

# Enable and start service
echo ""
echo -e "${YELLOW}Do you want to enable and start the service now? (y/n)${NC}"
read -r response

if [ "$response" = "y" ] || [ "$response" = "Y" ] || [ "$response" = "yes" ] || [ "$response" = "YES" ]; then
    systemctl enable "$SERVICE_NAME"
    systemctl start "$SERVICE_NAME"
    
    # Wait a moment for service to start
    sleep 2
    
    # Check status
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}✓ Service started successfully!${NC}"
    else
        echo -e "${RED}⚠ Service failed to start. Check status with: systemctl status ${SERVICE_NAME}${NC}"
    fi
else
    echo -e "${YELLOW}Skipping service start. You can start it later with:${NC}"
    echo "  systemctl enable $SERVICE_NAME"
    echo "  systemctl start $SERVICE_NAME"
fi

# Detect IP address
IP_ADDR=$(hostname -I | awk '{print $1}')

# Installation complete
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Installation directory: ${YELLOW}${INSTALL_DIR}${NC}"
echo -e "Service name: ${YELLOW}${SERVICE_NAME}${NC}"
echo -e "Web UI port: ${YELLOW}5000${NC}"
echo ""
echo -e "${GREEN}Access the web interface at:${NC}"
echo -e "  http://${IP_ADDR}:5000"
echo -e "  http://localhost:5000"
echo ""
echo -e "${GREEN}Useful commands:${NC}"
echo -e "  ${YELLOW}systemctl status ${SERVICE_NAME}${NC}   - Check service status"
echo -e "  ${YELLOW}systemctl restart ${SERVICE_NAME}${NC}  - Restart service"
echo -e "  ${YELLOW}systemctl stop ${SERVICE_NAME}${NC}     - Stop service"
echo -e "  ${YELLOW}journalctl -u ${SERVICE_NAME} -f${NC}  - View logs"
echo ""
echo -e "${GREEN}To customize the service:${NC}"
echo -e "  1. Edit: ${YELLOW}/etc/systemd/system/${SERVICE_NAME}.service${NC}"
echo -e "  2. Run: ${YELLOW}systemctl daemon-reload${NC}"
echo -e "  3. Run: ${YELLOW}systemctl restart ${SERVICE_NAME}${NC}"
echo ""
echo -e "${GREEN}To uninstall:${NC}"
echo -e "  ${YELLOW}systemctl stop ${SERVICE_NAME}${NC}"
echo -e "  ${YELLOW}systemctl disable ${SERVICE_NAME}${NC}"
echo -e "  ${YELLOW}rm /etc/systemd/system/${SERVICE_NAME}.service${NC}"
echo -e "  ${YELLOW}rm -rf ${INSTALL_DIR}${NC}"
echo -e "  ${YELLOW}systemctl daemon-reload${NC}"
echo ""