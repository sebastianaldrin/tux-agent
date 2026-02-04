"""
Global Hotkey Service for TuxAgent
Registers system-wide hotkeys using XDG Portal (Wayland-safe) or X11 fallback
"""
import logging
import subprocess
import threading
from typing import Callable, Dict, Optional
from pathlib import Path

# Add parent path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.config import TuxAgentConfig

logger = logging.getLogger(__name__)


class HotkeyService:
    """
    Global hotkey registration service

    Uses XDG Portal GlobalShortcuts on Wayland (GNOME 45+, KDE 5.27+)
    Falls back to keybinder on X11
    """

    def __init__(self, on_activate: Optional[Callable[[], None]] = None,
                 on_screenshot: Optional[Callable[[], None]] = None):
        """
        Initialize hotkey service

        Args:
            on_activate: Callback when main hotkey is pressed
            on_screenshot: Callback when screenshot hotkey is pressed
        """
        self.on_activate = on_activate
        self.on_screenshot = on_screenshot

        self._portal_proxy = None
        self._session = None
        self._registered_shortcuts = {}
        self._running = False

        # Detect display server
        self._is_wayland = self._detect_wayland()
        logger.info(f"Display server: {'Wayland' if self._is_wayland else 'X11'}")

    def _detect_wayland(self) -> bool:
        """Detect if running on Wayland"""
        import os
        return os.environ.get('XDG_SESSION_TYPE') == 'wayland' or \
               os.environ.get('WAYLAND_DISPLAY') is not None

    def start(self):
        """Start the hotkey service"""
        if self._running:
            return

        self._running = True

        if self._is_wayland:
            self._start_portal()
        else:
            self._start_x11()

    def stop(self):
        """Stop the hotkey service"""
        self._running = False

        if self._session:
            try:
                self._session.Close()
            except:
                pass
            self._session = None

    def _start_portal(self):
        """Start XDG Portal GlobalShortcuts"""
        try:
            from gi.repository import Gio, GLib

            # Connect to the portal
            self._portal_proxy = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SESSION,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.freedesktop.portal.Desktop",
                "/org/freedesktop/portal/desktop",
                "org.freedesktop.portal.GlobalShortcuts",
                None
            )

            if not self._portal_proxy:
                logger.warning("GlobalShortcuts portal not available, falling back to desktop shortcuts")
                self._setup_desktop_shortcuts()
                return

            # Create a session
            self._create_portal_session()

        except Exception as e:
            logger.warning(f"Portal setup failed: {e}, falling back to desktop shortcuts")
            self._setup_desktop_shortcuts()

    def _create_portal_session(self):
        """Create a GlobalShortcuts session"""
        try:
            from gi.repository import Gio, GLib

            # Generate unique tokens
            import random
            import string
            handle_token = ''.join(random.choices(string.ascii_lowercase, k=8))
            session_token = ''.join(random.choices(string.ascii_lowercase, k=8))

            # CreateSession
            options = GLib.Variant('a{sv}', {
                'handle_token': GLib.Variant('s', handle_token),
                'session_handle_token': GLib.Variant('s', session_token)
            })

            result = self._portal_proxy.call_sync(
                "CreateSession",
                GLib.Variant('(a{sv})', (options,)),
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )

            if result:
                request_path = result.unpack()[0]
                logger.info(f"Portal session created: {request_path}")

                # The session path follows a pattern based on our tokens
                # We need to wait for the Response signal, but for simplicity,
                # let's use desktop shortcuts which are more reliable
                self._setup_desktop_shortcuts()
            else:
                self._setup_desktop_shortcuts()

        except Exception as e:
            logger.warning(f"Failed to create portal session: {e}")
            self._setup_desktop_shortcuts()

    def _setup_desktop_shortcuts(self):
        """Set up shortcuts using desktop environment settings (most reliable)"""
        logger.info("Setting up shortcuts via desktop settings")

        # Get configured hotkeys
        main_hotkey = TuxAgentConfig.get_hotkey()
        screenshot_hotkey = TuxAgentConfig.get_screenshot_hotkey()

        # Try GNOME settings
        if self._setup_gnome_shortcuts(main_hotkey, screenshot_hotkey):
            return

        # Try KDE settings
        if self._setup_kde_shortcuts(main_hotkey, screenshot_hotkey):
            return

        # Log that manual setup is needed
        logger.info(
            f"Automatic hotkey setup not available. "
            f"Please set up shortcuts manually:\n"
            f"  Main: {main_hotkey} -> tuxagent-overlay\n"
            f"  Screenshot: {screenshot_hotkey} -> tuxagent-overlay --screenshot"
        )

    def _setup_gnome_shortcuts(self, main_hotkey: str, screenshot_hotkey: str) -> bool:
        """Set up shortcuts using GNOME custom keybindings"""
        try:
            # Check if gsettings is available and GNOME is running
            result = subprocess.run(
                ['gsettings', 'list-schemas'],
                capture_output=True,
                text=True
            )
            if 'org.gnome.settings-daemon.plugins.media-keys' not in result.stdout:
                return False

            # Convert hotkey format: Super+Shift+A -> <Super><Shift>a
            def convert_hotkey(hotkey: str) -> str:
                parts = hotkey.split('+')
                result = ''
                for part in parts[:-1]:  # Modifiers
                    result += f'<{part}>'
                result += parts[-1].lower()  # Key
                return result

            gnome_main = convert_hotkey(main_hotkey)
            gnome_screenshot = convert_hotkey(screenshot_hotkey)

            # Set up custom keybindings
            base_path = '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings'

            # Get existing custom keybindings
            result = subprocess.run(
                ['gsettings', 'get', 'org.gnome.settings-daemon.plugins.media-keys', 'custom-keybindings'],
                capture_output=True,
                text=True
            )

            existing = result.stdout.strip()
            if existing == '@as []':
                existing_list = []
            else:
                # Parse the list
                existing_list = [x.strip().strip("'") for x in existing.strip('[]').split(',') if x.strip()]

            # Add our keybindings if not present
            tux_main = f'{base_path}/tuxagent-main/'
            tux_screenshot = f'{base_path}/tuxagent-screenshot/'

            updated = False
            if tux_main not in existing_list:
                existing_list.append(tux_main)
                updated = True
            if tux_screenshot not in existing_list:
                existing_list.append(tux_screenshot)
                updated = True

            if updated:
                new_list = str(existing_list).replace('"', "'")
                subprocess.run([
                    'gsettings', 'set',
                    'org.gnome.settings-daemon.plugins.media-keys',
                    'custom-keybindings', new_list
                ], check=True)

            # Set up the main keybinding
            schema = 'org.gnome.settings-daemon.plugins.media-keys.custom-keybinding'
            path = f'{base_path}/tuxagent-main/'

            subprocess.run(['gsettings', 'set', f'{schema}:{path}', 'name', 'TuxAgent'], check=True)
            subprocess.run(['gsettings', 'set', f'{schema}:{path}', 'command', 'tuxagent-overlay'], check=True)
            subprocess.run(['gsettings', 'set', f'{schema}:{path}', 'binding', gnome_main], check=True)

            # Set up the screenshot keybinding
            path = f'{base_path}/tuxagent-screenshot/'
            subprocess.run(['gsettings', 'set', f'{schema}:{path}', 'name', 'TuxAgent Screenshot'], check=True)
            subprocess.run(['gsettings', 'set', f'{schema}:{path}', 'command', 'tuxagent-overlay --screenshot'], check=True)
            subprocess.run(['gsettings', 'set', f'{schema}:{path}', 'binding', gnome_screenshot], check=True)

            logger.info(f"GNOME shortcuts configured: {gnome_main}, {gnome_screenshot}")
            return True

        except Exception as e:
            logger.debug(f"GNOME shortcut setup failed: {e}")
            return False

    def _setup_kde_shortcuts(self, main_hotkey: str, screenshot_hotkey: str) -> bool:
        """Set up shortcuts using KDE global shortcuts"""
        try:
            # Check if kwriteconfig5 is available
            result = subprocess.run(['which', 'kwriteconfig5'], capture_output=True)
            if result.returncode != 0:
                return False

            # Convert hotkey format for KDE
            # Super+Shift+A -> Meta+Shift+A
            def convert_hotkey(hotkey: str) -> str:
                return hotkey.replace('Super', 'Meta')

            kde_main = convert_hotkey(main_hotkey)
            kde_screenshot = convert_hotkey(screenshot_hotkey)

            # Create/update kglobalshortcutsrc
            config_dir = Path.home() / '.config'
            shortcuts_file = config_dir / 'kglobalshortcutsrc'

            # Use kwriteconfig5 to set shortcuts
            subprocess.run([
                'kwriteconfig5', '--file', 'kglobalshortcutsrc',
                '--group', 'tuxagent.desktop',
                '--key', '_k_friendly_name', 'TuxAgent'
            ], check=True)

            subprocess.run([
                'kwriteconfig5', '--file', 'kglobalshortcutsrc',
                '--group', 'tuxagent.desktop',
                '--key', 'open', f'{kde_main},none,Open TuxAgent'
            ], check=True)

            subprocess.run([
                'kwriteconfig5', '--file', 'kglobalshortcutsrc',
                '--group', 'tuxagent.desktop',
                '--key', 'screenshot', f'{kde_screenshot},none,TuxAgent Screenshot'
            ], check=True)

            # Reload shortcuts
            subprocess.run(['qdbus', 'org.kde.kglobalaccel', '/kglobalaccel',
                          'org.kde.KGlobalAccel.reloadConfig'], check=False)

            logger.info(f"KDE shortcuts configured: {kde_main}, {kde_screenshot}")
            return True

        except Exception as e:
            logger.debug(f"KDE shortcut setup failed: {e}")
            return False

    def _start_x11(self):
        """Start X11 keybinding using keybinder or xbindkeys"""
        try:
            # Try keybinder-0.0
            import gi
            gi.require_version('Keybinder', '3.0')
            from gi.repository import Keybinder

            Keybinder.init()

            main_hotkey = TuxAgentConfig.get_hotkey()
            screenshot_hotkey = TuxAgentConfig.get_screenshot_hotkey()

            # Convert format: Super+Shift+A -> <Super><Shift>a
            def convert_hotkey(hotkey: str) -> str:
                parts = hotkey.split('+')
                result = ''
                for part in parts[:-1]:
                    result += f'<{part}>'
                result += parts[-1]
                return result

            x11_main = convert_hotkey(main_hotkey)
            x11_screenshot = convert_hotkey(screenshot_hotkey)

            if self.on_activate:
                Keybinder.bind(x11_main, lambda k: self.on_activate())
                self._registered_shortcuts['main'] = x11_main
                logger.info(f"X11 main hotkey bound: {x11_main}")

            if self.on_screenshot:
                Keybinder.bind(x11_screenshot, lambda k: self.on_screenshot())
                self._registered_shortcuts['screenshot'] = x11_screenshot
                logger.info(f"X11 screenshot hotkey bound: {x11_screenshot}")

        except ImportError:
            logger.info("Keybinder not available, using desktop shortcut fallback")
            self._setup_desktop_shortcuts()
        except Exception as e:
            logger.warning(f"X11 keybinding failed: {e}")
            self._setup_desktop_shortcuts()

    def update_hotkeys(self):
        """Update hotkeys after settings change"""
        logger.info("Updating hotkeys...")
        self.stop()
        self.start()

    def get_status(self) -> Dict:
        """Get hotkey service status"""
        return {
            "running": self._running,
            "display_server": "Wayland" if self._is_wayland else "X11",
            "main_hotkey": TuxAgentConfig.get_hotkey(),
            "screenshot_hotkey": TuxAgentConfig.get_screenshot_hotkey(),
            "registered": list(self._registered_shortcuts.keys())
        }


def setup_hotkeys():
    """Convenience function to set up hotkeys for the daemon"""
    import dbus

    def on_activate():
        """Launch overlay via D-Bus or direct command"""
        try:
            bus = dbus.SessionBus()
            proxy = bus.get_object('org.tuxagent.Overlay', '/org/tuxagent/Overlay')
            interface = dbus.Interface(proxy, 'org.gtk.Actions')
            interface.Activate('activate', [], {})
        except:
            # Fallback to direct launch
            subprocess.Popen(['tuxagent-overlay'], start_new_session=True)

    def on_screenshot():
        """Launch overlay with screenshot"""
        subprocess.Popen(['tuxagent-overlay', '--screenshot'], start_new_session=True)

    service = HotkeyService(on_activate=on_activate, on_screenshot=on_screenshot)
    service.start()
    return service
