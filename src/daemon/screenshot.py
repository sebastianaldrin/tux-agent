"""
Screenshot Service for TuxAgent
Supports multiple backends: GNOME Shell D-Bus, XDG Portal, CLI fallback
"""
import logging
import base64
import os
import tempfile
from typing import Optional, Tuple
from pathlib import Path

from gi.repository import GLib, Gio

logger = logging.getLogger(__name__)

# GNOME Shell Screenshot D-Bus constants
GNOME_SHELL_BUS = "org.gnome.Shell.Screenshot"
GNOME_SHELL_PATH = "/org/gnome/Shell/Screenshot"
GNOME_SHELL_IFACE = "org.gnome.Shell.Screenshot"

# XDG Portal D-Bus constants
PORTAL_BUS_NAME = "org.freedesktop.portal.Desktop"
PORTAL_OBJECT_PATH = "/org/freedesktop/portal/desktop"
SCREENSHOT_INTERFACE = "org.freedesktop.portal.Screenshot"


class GnomeShellScreenshotService:
    """
    GNOME Shell native D-Bus screenshot service
    Clean, no subprocess spawning, works reliably on GNOME
    """

    def __init__(self):
        """Initialize GNOME Shell screenshot service"""
        self._bus = None

    def _get_bus(self) -> Gio.DBusConnection:
        """Get D-Bus session bus connection"""
        if self._bus is None:
            self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        return self._bus

    def capture(self, interactive: bool = True) -> Optional[str]:
        """
        Capture a screenshot using GNOME Shell D-Bus interface

        Args:
            interactive: If True, let user select area; otherwise full screen

        Returns:
            Base64-encoded PNG image, or None if failed/cancelled
        """
        try:
            bus = self._get_bus()

            # Create temp file for screenshot
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                temp_path = f.name

            if interactive:
                # Let user select area
                result = bus.call_sync(
                    GNOME_SHELL_BUS,
                    GNOME_SHELL_PATH,
                    GNOME_SHELL_IFACE,
                    "SelectArea",
                    None,
                    GLib.VariantType("(iiii)"),
                    Gio.DBusCallFlags.NONE,
                    60000,  # 60 second timeout for user selection
                    None
                )

                x, y, width, height = result.unpack()

                if width <= 0 or height <= 0:
                    logger.info("Screenshot cancelled - invalid selection")
                    return None

                # Capture the selected area
                result = bus.call_sync(
                    GNOME_SHELL_BUS,
                    GNOME_SHELL_PATH,
                    GNOME_SHELL_IFACE,
                    "ScreenshotArea",
                    GLib.Variant("(iiiibs)", (x, y, width, height, True, temp_path)),
                    GLib.VariantType("(bs)"),
                    Gio.DBusCallFlags.NONE,
                    10000,
                    None
                )
            else:
                # Full screen capture
                result = bus.call_sync(
                    GNOME_SHELL_BUS,
                    GNOME_SHELL_PATH,
                    GNOME_SHELL_IFACE,
                    "Screenshot",
                    GLib.Variant("(bbs)", (False, True, temp_path)),
                    GLib.VariantType("(bs)"),
                    Gio.DBusCallFlags.NONE,
                    10000,
                    None
                )

            success, filename_used = result.unpack()

            if success and os.path.exists(filename_used):
                with open(filename_used, "rb") as f:
                    image_data = f.read()

                # Clean up temp file
                try:
                    os.unlink(filename_used)
                except:
                    pass

                logger.info(f"Screenshot captured: {len(image_data)} bytes")
                return base64.b64encode(image_data).decode("utf-8")

            logger.warning("Screenshot capture returned failure")
            return None

        except GLib.Error as e:
            if "cancelled" in str(e).lower() or "Cancelled" in str(e):
                logger.info("Screenshot cancelled by user")
            else:
                logger.error(f"GNOME Shell screenshot failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None


class ScreenshotService:
    """
    XDG Portal-based screenshot service
    Works on both X11 and Wayland with user consent
    """

    def __init__(self):
        """Initialize screenshot service"""
        self._bus = None
        self._portal = None
        self._pending_screenshot = None
        self._screenshot_path = None
        self._loop = None

    def _get_bus(self) -> Gio.DBusConnection:
        """Get D-Bus session bus connection"""
        if self._bus is None:
            self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        return self._bus

    def _handle_response(self, connection, sender_name, object_path,
                        interface_name, signal_name, parameters, user_data):
        """Handle portal response signal"""
        response_code, results = parameters.unpack()

        if response_code == 0:  # Success
            uri = results.get("uri", "")
            if uri:
                # Convert file:// URI to path
                if uri.startswith("file://"):
                    self._screenshot_path = uri[7:]
                else:
                    self._screenshot_path = uri
                logger.info(f"Screenshot saved to: {self._screenshot_path}")
        elif response_code == 1:
            logger.info("Screenshot cancelled by user")
            self._screenshot_path = None
        else:
            logger.error(f"Screenshot failed with code: {response_code}")
            self._screenshot_path = None

        # Stop the loop
        if self._loop:
            self._loop.quit()

    def capture(self, interactive: bool = True) -> Optional[str]:
        """
        Capture a screenshot

        Args:
            interactive: If True, show user consent dialog

        Returns:
            Base64-encoded PNG image, or None if failed/cancelled
        """
        try:
            bus = self._get_bus()

            # Create unique token for this request
            import random
            token = f"tuxagent_{random.randint(100000, 999999)}"

            # Subscribe to Response signal
            handle_path = f"/org/freedesktop/portal/desktop/request/{os.environ.get('USER', 'user')}/{token}"

            subscription_id = bus.signal_subscribe(
                PORTAL_BUS_NAME,
                "org.freedesktop.portal.Request",
                "Response",
                handle_path,
                None,
                Gio.DBusSignalFlags.NONE,
                self._handle_response,
                None
            )

            # Build options
            options = GLib.Variant("a{sv}", {
                "handle_token": GLib.Variant("s", token),
                "modal": GLib.Variant("b", True),
                "interactive": GLib.Variant("b", interactive)
            })

            # Call Screenshot method
            result = bus.call_sync(
                PORTAL_BUS_NAME,
                PORTAL_OBJECT_PATH,
                SCREENSHOT_INTERFACE,
                "Screenshot",
                GLib.Variant("(sa{sv})", ("", options)),
                GLib.VariantType("(o)"),
                Gio.DBusCallFlags.NONE,
                30000,  # 30 second timeout
                None
            )

            # Run main loop to wait for response
            self._loop = GLib.MainLoop()
            self._screenshot_path = None

            # Add timeout to prevent hanging
            def timeout_callback():
                if self._loop.is_running():
                    self._loop.quit()
                return False

            GLib.timeout_add_seconds(60, timeout_callback)

            self._loop.run()

            # Unsubscribe from signal
            bus.signal_unsubscribe(subscription_id)

            # Read and encode screenshot
            if self._screenshot_path and os.path.exists(self._screenshot_path):
                with open(self._screenshot_path, "rb") as f:
                    image_data = f.read()

                # Clean up temporary file if in temp directory
                if self._screenshot_path.startswith("/tmp"):
                    try:
                        os.unlink(self._screenshot_path)
                    except:
                        pass

                return base64.b64encode(image_data).decode("utf-8")

            return None

        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None

    def capture_to_file(self, output_path: str, interactive: bool = True) -> bool:
        """
        Capture screenshot and save to file

        Args:
            output_path: Path to save the screenshot
            interactive: If True, show user consent dialog

        Returns:
            True if successful
        """
        try:
            screenshot_data = self.capture(interactive)
            if screenshot_data:
                image_bytes = base64.b64decode(screenshot_data)
                with open(output_path, "wb") as f:
                    f.write(image_bytes)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to save screenshot: {e}")
            return False


class FallbackScreenshotService:
    """
    Fallback screenshot service using gnome-screenshot or scrot
    Used when XDG Portal is not available
    """

    def __init__(self):
        """Initialize fallback service"""
        self._tool = self._find_screenshot_tool()
        if self._tool:
            logger.info(f"Using fallback screenshot tool: {self._tool}")
        else:
            logger.warning("No screenshot tool found")

    def _find_screenshot_tool(self) -> Optional[str]:
        """Find available screenshot tool"""
        import shutil
        tools = ["gnome-screenshot", "scrot", "spectacle", "maim"]
        for tool in tools:
            if shutil.which(tool):
                return tool
        return None

    def capture(self, interactive: bool = True) -> Optional[str]:
        """Capture screenshot using fallback tool"""
        if not self._tool:
            logger.error("No screenshot tool available")
            return None

        try:
            import subprocess

            # Create temp file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                temp_path = f.name

            # Build command based on tool
            if self._tool == "gnome-screenshot":
                cmd = ["gnome-screenshot", "-f", temp_path]
                if interactive:
                    cmd.append("-a")  # Area selection mode (user draws rectangle)
            elif self._tool == "scrot":
                cmd = ["scrot", temp_path]
                if interactive:
                    cmd.extend(["-s"])  # Select mode
            elif self._tool == "spectacle":
                if interactive:
                    # Interactive rectangular region selection, save to file
                    cmd = ["spectacle", "-r", "-b", "-o", temp_path]
                else:
                    # Full screen capture
                    cmd = ["spectacle", "-f", "-b", "-o", temp_path]
            elif self._tool == "maim":
                cmd = ["maim", temp_path]
                if interactive:
                    cmd.extend(["-s"])  # Select mode
            else:
                return None

            # Run screenshot command
            result = subprocess.run(cmd, capture_output=True, timeout=60)

            if result.returncode == 0 and os.path.exists(temp_path):
                with open(temp_path, "rb") as f:
                    image_data = f.read()

                # Clean up
                os.unlink(temp_path)

                return base64.b64encode(image_data).decode("utf-8")

            return None

        except Exception as e:
            logger.error(f"Fallback screenshot failed: {e}")
            return None


def get_screenshot_service():
    """
    Get the best available screenshot service

    Priority:
    1. XDG Portal (Wayland-safe, works with user consent)
    2. CLI fallback (gnome-screenshot -a for area selection)

    Note: GNOME Shell D-Bus Screenshot is blocked by security policy
    """
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

    # Try XDG Portal first
    try:
        bus.call_sync(
            PORTAL_BUS_NAME,
            PORTAL_OBJECT_PATH,
            "org.freedesktop.DBus.Properties",
            "Get",
            GLib.Variant("(ss)", (SCREENSHOT_INTERFACE, "version")),
            GLib.VariantType("(v)"),
            Gio.DBusCallFlags.NONE,
            1000,
            None
        )
        logger.info("Using XDG Portal Screenshot interface")
        return ScreenshotService()
    except Exception as e:
        logger.debug(f"XDG Portal Screenshot not available: {e}")

    # Fall back to CLI tools (gnome-screenshot -a works well)
    logger.info("Using gnome-screenshot for area selection")
    return FallbackScreenshotService()


# Convenience function
def take_screenshot(interactive: bool = True) -> Optional[str]:
    """
    Take a screenshot and return base64-encoded PNG

    Args:
        interactive: If True, show user consent dialog

    Returns:
        Base64-encoded PNG image, or None if failed
    """
    service = get_screenshot_service()
    return service.capture(interactive)
