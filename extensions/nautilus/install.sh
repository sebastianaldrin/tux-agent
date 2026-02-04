#!/bin/bash
# Install TuxAgent Nautilus Extension

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXTENSION_FILE="$SCRIPT_DIR/tuxagent-extension.py"

# Nautilus extension directories
NAUTILUS_EXTENSIONS_DIR="$HOME/.local/share/nautilus-python/extensions"

echo "Installing TuxAgent Nautilus extension..."

# Create directory if it doesn't exist
mkdir -p "$NAUTILUS_EXTENSIONS_DIR"

# Copy extension
cp "$EXTENSION_FILE" "$NAUTILUS_EXTENSIONS_DIR/"

echo "Extension installed to: $NAUTILUS_EXTENSIONS_DIR"
echo ""
echo "Please restart Nautilus to load the extension:"
echo "  nautilus -q && nautilus &"
echo ""
echo "Or log out and log back in."
