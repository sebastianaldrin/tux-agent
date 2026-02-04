#!/usr/bin/env python3
"""
TuxAgent Daemon Entry Point
Starts the background D-Bus service
"""
import sys
import os
import logging
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.config import TuxAgentConfig


def setup_logging(debug: bool = False):
    """Configure logging"""
    log_level = logging.DEBUG if debug else logging.INFO

    # Create log directory
    log_dir = TuxAgentConfig.get_cache_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "daemon.log")
        ]
    )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="TuxAgent Daemon")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--foreground", "-f",
        action="store_true",
        help="Run in foreground (don't daemonize)"
    )
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.debug)

    logger = logging.getLogger(__name__)
    logger.info("Starting TuxAgent daemon...")

    # Ensure directories exist
    TuxAgentConfig.ensure_directories()

    # Import and run the D-Bus service
    from src.daemon.dbus_service import TuxAgentDaemon

    daemon = TuxAgentDaemon()

    # Start hotkey service
    hotkey_service = None
    try:
        from src.daemon.hotkey import setup_hotkeys
        hotkey_service = setup_hotkeys()
        logger.info("Hotkey service started")
    except Exception as e:
        logger.warning(f"Could not start hotkey service: {e}")

    try:
        daemon.run()
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user")
    except Exception as e:
        logger.error(f"Daemon error: {e}")
        sys.exit(1)
    finally:
        if hotkey_service:
            hotkey_service.stop()


if __name__ == "__main__":
    main()
