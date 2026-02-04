#!/bin/bash
# TuxAgent Installation Script
# Installs daemon, CLI, overlay, and extensions

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     TuxAgent Installation Script       ║${NC}"
echo -e "${GREEN}║   Linux AI Desktop Assistant           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "Python version: ${GREEN}$PYTHON_VERSION${NC}"

# Detect package manager and distro
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    elif command -v lsb_release &> /dev/null; then
        DISTRO=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
    else
        DISTRO="unknown"
    fi
    echo "$DISTRO"
}

DISTRO=$(detect_distro)
echo -e "Detected distro: ${GREEN}$DISTRO${NC}"

# Install system dependencies based on distro
echo ""
echo -e "${YELLOW}Installing system dependencies...${NC}"

case "$DISTRO" in
    ubuntu|debian|linuxmint|pop|elementary|zorin)
        # Debian/Ubuntu based
        if ! command -v pip3 &> /dev/null; then
            echo -e "${YELLOW}Installing pip3...${NC}"
            sudo apt install -y python3-pip
        fi
        sudo apt update
        sudo apt install -y \
            python3-gi \
            python3-gi-cairo \
            gir1.2-gtk-4.0 \
            gir1.2-adw-1 \
            python3-dbus \
            libgirepository1.0-dev \
            xdg-desktop-portal \
            xdg-desktop-portal-gtk \
            python3-nautilus \
            2>/dev/null || echo -e "${YELLOW}Some packages may already be installed${NC}"
        ;;
    fedora|rhel|centos|rocky|alma)
        # Fedora/RHEL based
        if ! command -v pip3 &> /dev/null; then
            sudo dnf install -y python3-pip
        fi
        sudo dnf install -y \
            python3-gobject \
            gtk4 \
            libadwaita \
            python3-dbus \
            gobject-introspection-devel \
            xdg-desktop-portal \
            xdg-desktop-portal-gtk \
            nautilus-python \
            2>/dev/null || echo -e "${YELLOW}Some packages may already be installed${NC}"
        ;;
    arch|manjaro|endeavouros|garuda)
        # Arch based
        if ! command -v pip3 &> /dev/null; then
            sudo pacman -S --noconfirm python-pip
        fi
        sudo pacman -S --noconfirm --needed \
            python-gobject \
            gtk4 \
            libadwaita \
            python-dbus \
            gobject-introspection \
            xdg-desktop-portal \
            xdg-desktop-portal-gtk \
            python-nautilus \
            2>/dev/null || echo -e "${YELLOW}Some packages may already be installed${NC}"
        ;;
    opensuse*|suse*)
        # openSUSE
        if ! command -v pip3 &> /dev/null; then
            sudo zypper install -y python3-pip
        fi
        sudo zypper install -y \
            python3-gobject \
            gtk4 \
            libadwaita \
            python3-dbus \
            gobject-introspection \
            xdg-desktop-portal \
            xdg-desktop-portal-gtk \
            2>/dev/null || echo -e "${YELLOW}Some packages may already be installed${NC}"
        ;;
    *)
        echo -e "${YELLOW}Unknown distro: $DISTRO${NC}"
        echo -e "${YELLOW}Please install these dependencies manually:${NC}"
        echo "  - Python 3 GTK bindings (python3-gi/python-gobject)"
        echo "  - GTK 4"
        echo "  - libadwaita"
        echo "  - xdg-desktop-portal"
        echo ""
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        ;;
esac

# Install Python dependencies
echo ""
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip3 install --user -r "$PROJECT_DIR/requirements.txt" 2>/dev/null || \
pip3 install --user httpx Pillow markdown psutil python-dateutil requests beautifulsoup4

# Create installation directories
echo ""
echo -e "${YELLOW}Creating directories...${NC}"
INSTALL_DIR="/usr/lib/tuxagent"
BIN_DIR="/usr/local/bin"
SYSTEMD_DIR="$HOME/.config/systemd/user"
DBUS_SERVICES_DIR="$HOME/.local/share/dbus-1/services"
APPLICATIONS_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"

sudo mkdir -p "$INSTALL_DIR"
mkdir -p "$SYSTEMD_DIR"
mkdir -p "$DBUS_SERVICES_DIR"
mkdir -p "$APPLICATIONS_DIR"
mkdir -p "$AUTOSTART_DIR"
mkdir -p "$HOME/.config/tuxagent"
mkdir -p "$HOME/.local/share/tuxagent/conversations"
mkdir -p "$HOME/.cache/tuxagent"

# Copy source files
echo ""
echo -e "${YELLOW}Installing TuxAgent files...${NC}"
sudo cp -r "$PROJECT_DIR/src" "$INSTALL_DIR/"
sudo cp -r "$PROJECT_DIR/config" "$INSTALL_DIR/"

# Create CLI wrapper
echo ""
echo -e "${YELLOW}Creating CLI wrapper...${NC}"
sudo tee "$BIN_DIR/tux" > /dev/null << 'EOF'
#!/bin/bash
export PYTHONPATH="/usr/lib/tuxagent:$PYTHONPATH"
python3 /usr/lib/tuxagent/src/cli/tux.py "$@"
EOF
sudo chmod +x "$BIN_DIR/tux"

# Create daemon wrapper
sudo tee "$BIN_DIR/tuxagent-daemon" > /dev/null << 'EOF'
#!/bin/bash
export PYTHONPATH="/usr/lib/tuxagent:$PYTHONPATH"
python3 /usr/lib/tuxagent/src/daemon/main.py "$@"
EOF
sudo chmod +x "$BIN_DIR/tuxagent-daemon"

# Create overlay wrapper
sudo tee "$BIN_DIR/tuxagent-overlay" > /dev/null << 'EOF'
#!/bin/bash
export PYTHONPATH="/usr/lib/tuxagent:$PYTHONPATH"
python3 /usr/lib/tuxagent/src/ui/main.py "$@"
EOF
sudo chmod +x "$BIN_DIR/tuxagent-overlay"

# Install D-Bus service file
echo ""
echo -e "${YELLOW}Installing D-Bus service...${NC}"
cat > "$DBUS_SERVICES_DIR/org.tuxagent.Assistant.service" << EOF
[D-BUS Service]
Name=org.tuxagent.Assistant
Exec=/usr/local/bin/tuxagent-daemon
EOF

# Install systemd service
echo ""
echo -e "${YELLOW}Installing systemd service...${NC}"
cat > "$SYSTEMD_DIR/tuxagent.service" << EOF
[Unit]
Description=TuxAgent - Linux AI Assistant
Documentation=https://github.com/yourusername/tux-agent
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=dbus
BusName=org.tuxagent.Assistant
ExecStart=/usr/local/bin/tuxagent-daemon
Restart=on-failure
RestartSec=5
Environment=PYTHONPATH=/usr/lib/tuxagent
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=graphical-session.target
EOF

# Reload systemd
systemctl --user daemon-reload

# Install desktop file
echo ""
echo -e "${YELLOW}Installing desktop entry...${NC}"
cat > "$APPLICATIONS_DIR/org.tuxagent.desktop" << EOF
[Desktop Entry]
Type=Application
Name=TuxAgent
Comment=Linux AI Assistant
Icon=dialog-question
Exec=/usr/local/bin/tuxagent-overlay
Terminal=false
Categories=Utility;System;
Keywords=AI;Assistant;Help;Linux;
StartupNotify=false
EOF

# Install autostart entry (optional)
cat > "$AUTOSTART_DIR/tuxagent-daemon.desktop" << EOF
[Desktop Entry]
Type=Application
Name=TuxAgent Daemon
Exec=/usr/local/bin/tuxagent-daemon
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
EOF

# Install Nautilus extension
echo ""
echo -e "${YELLOW}Installing Nautilus extension...${NC}"
NAUTILUS_EXT_DIR="$HOME/.local/share/nautilus-python/extensions"
mkdir -p "$NAUTILUS_EXT_DIR"
cp "$PROJECT_DIR/extensions/nautilus/tuxagent-extension.py" "$NAUTILUS_EXT_DIR/"

# Enable and start service
echo ""
echo -e "${YELLOW}Enabling TuxAgent service...${NC}"
systemctl --user enable tuxagent.service 2>/dev/null || true

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Installation Complete!             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo "Usage:"
echo "  tux ask \"How do I install Chrome?\""
echo "  tux ask --screenshot \"What application is this?\""
echo "  tux interactive"
echo "  tux status"
echo ""
echo "To start the daemon manually:"
echo "  tuxagent-daemon"
echo ""
echo "To open the overlay:"
echo "  tuxagent-overlay"
echo ""
echo "The daemon will start automatically on next login."
echo ""
echo -e "${YELLOW}Note: Please restart Nautilus to load the extension:${NC}"
echo "  nautilus -q"
echo ""
echo -e "${GREEN}Enjoy TuxAgent! 🐧${NC}"
