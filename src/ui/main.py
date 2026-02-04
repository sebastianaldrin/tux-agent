#!/usr/bin/env python3
"""
TuxAgent UI Entry Point
Launches the GTK4 overlay window
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.overlay import main

if __name__ == "__main__":
    sys.exit(main())
