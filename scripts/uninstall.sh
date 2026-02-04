#!/bin/bash
# TuxAgent Uninstallation Script
# Removes daemon, CLI, overlay, and all related files

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${RED}╔═══════════════════════════════════════╗${NC}"
echo -e "${RED}║    TuxAgent Uninstallation Script     ║${NC}"
echo -e "${RED}╚═══════════════════════════════════════╝${NC}"
echo ""

# Confirm uninstall
read -p "Are you sure you want to uninstall TuxAgent? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstall cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}Stopping TuxAgent services...${NC}"
systemctl --user stop tuxagent.service 2>/dev/null || true
systemctl --user disable tuxagent.service 2>/dev/null || true

echo -e "${YELLOW}Removing installed files...${NC}"

# Remove binaries
sudo rm -f /usr/local/bin/tux
sudo rm -f /usr/local/bin/tuxagent-daemon
sudo rm -f /usr/local/bin/tuxagent-overlay

# Remove installation directory
sudo rm -rf /usr/lib/tuxagent

# Remove service files
rm -f "$HOME/.config/systemd/user/tuxagent.service"
rm -f "$HOME/.local/share/dbus-1/services/org.tuxagent.Assistant.service"

# Remove desktop entries
rm -f "$HOME/.local/share/applications/org.tuxagent.desktop"
rm -f "$HOME/.config/autostart/tuxagent-daemon.desktop"

# Remove Nautilus extension
rm -f "$HOME/.local/share/nautilus-python/extensions/tuxagent-extension.py"

# Reload systemd
systemctl --user daemon-reload

echo ""
echo -e "${YELLOW}Keeping user data (config, conversations)${NC}"
echo "  Config: ~/.config/tuxagent/"
echo "  Conversations: ~/.local/share/tuxagent/"
echo "  Cache: ~/.cache/tuxagent/"
echo ""
read -p "Delete user data too? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$HOME/.config/tuxagent"
    rm -rf "$HOME/.local/share/tuxagent"
    rm -rf "$HOME/.cache/tuxagent"
    echo -e "${GREEN}User data deleted.${NC}"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     TuxAgent Uninstalled!             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo "TuxAgent has been removed from your system."
echo ""
echo -e "${YELLOW}Note: Restart Nautilus to fully unload the extension:${NC}"
echo "  nautilus -q"
echo ""
