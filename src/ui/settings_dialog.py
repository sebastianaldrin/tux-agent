"""
TuxAgent Settings Dialog
GUI for configuring API tier, hotkeys, and general settings
"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio
import subprocess
import threading
import logging
from pathlib import Path

# Add parent path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.config import TuxAgentConfig, APIMode, BYOKProvider
from src.core.api_providers import PROVIDER_INFO, get_provider_for_mode

logger = logging.getLogger(__name__)


class SettingsDialog(Adw.Window):
    """Dialog for TuxAgent settings"""

    def __init__(self, parent=None, on_settings_changed=None, **kwargs):
        super().__init__(**kwargs)

        self.set_title("Settings")
        self.set_default_size(500, 650)
        self.set_modal(True)
        if parent:
            self.set_transient_for(parent)

        self.on_settings_changed = on_settings_changed
        self._build_ui()

    def _build_ui(self):
        """Build the dialog UI"""
        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header bar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)
        main_box.append(header)

        # Scrollable content
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_margin_top(24)
        content.set_margin_bottom(24)

        # API Configuration section
        content.append(self._build_api_section())

        # Keyboard Shortcuts section
        content.append(self._build_shortcuts_section())

        # General section
        content.append(self._build_general_section())

        scroll.set_child(content)
        main_box.append(scroll)

        self.set_content(main_box)

    def _build_api_section(self) -> Gtk.Widget:
        """Build the API Configuration section"""
        group = Adw.PreferencesGroup()
        group.set_title("API Configuration")

        current_mode = TuxAgentConfig.get_api_mode()
        monetization_enabled = TuxAgentConfig.MONETIZATION_ENABLED

        if monetization_enabled:
            group.set_description("Choose how TuxAgent connects to AI services")

            # Free Tier Row
            free_row = Adw.ActionRow()
            free_row.set_title("Free Tier")
            free_row.set_subtitle("20 queries/month - No setup required")

            self.free_radio = Gtk.CheckButton()
            self.free_radio.set_active(current_mode == APIMode.FREE.value)
            self.free_radio.connect("toggled", self._on_mode_changed, APIMode.FREE.value)
            free_row.add_prefix(self.free_radio)

            # Usage indicator for free tier
            usage_count = TuxAgentConfig.get_usage_count()
            usage_limit = TuxAgentConfig.FREE_TIER_LIMIT
            self.free_usage_label = Gtk.Label(label=f"{usage_count}/{usage_limit} used")
            self.free_usage_label.add_css_class("dim-label")
            self.free_usage_label.add_css_class("caption")
            free_row.add_suffix(self.free_usage_label)

            group.add(free_row)

            # TuxAgent Cloud Row
            cloud_row = Adw.ExpanderRow()
            cloud_row.set_title("TuxAgent Cloud (Recommended)")
            cloud_row.set_subtitle("500+ queries/month - Priority support")

            self.cloud_radio = Gtk.CheckButton()
            self.cloud_radio.set_group(self.free_radio)
            self.cloud_radio.set_active(current_mode == APIMode.CLOUD.value)
            self.cloud_radio.connect("toggled", self._on_mode_changed, APIMode.CLOUD.value)
            cloud_row.add_prefix(self.cloud_radio)

            # License key input (in expander)
            license_row = Adw.ActionRow()
            license_row.set_title("License Key")

            self.license_entry = Gtk.Entry()
            self.license_entry.set_hexpand(True)
            self.license_entry.set_placeholder_text("Enter your license key")
            self.license_entry.set_text(TuxAgentConfig.get_license_key())
            self.license_entry.set_visibility(False)  # Hide like password
            license_row.add_suffix(self.license_entry)

            self.license_activate_btn = Gtk.Button(label="Activate")
            self.license_activate_btn.add_css_class("suggested-action")
            self.license_activate_btn.connect("clicked", self._on_activate_license)
            license_row.add_suffix(self.license_activate_btn)

            cloud_row.add_row(license_row)

            # Get license link
            get_license_row = Adw.ActionRow()
            get_license_row.set_title("Don't have a license?")
            get_license_btn = Gtk.LinkButton.new_with_label(
                "https://tuxagent.dev/pricing",
                "Get one here"
            )
            get_license_row.add_suffix(get_license_btn)
            cloud_row.add_row(get_license_row)

            group.add(cloud_row)

            # BYOK Row (with radio button when monetization enabled)
            byok_row = Adw.ExpanderRow()
            byok_row.set_title("Use Your Own API Key")
            byok_row.set_subtitle("Unlimited queries - You pay the provider directly")

            self.byok_radio = Gtk.CheckButton()
            self.byok_radio.set_group(self.free_radio)
            self.byok_radio.set_active(current_mode == APIMode.BYOK.value)
            self.byok_radio.connect("toggled", self._on_mode_changed, APIMode.BYOK.value)
            byok_row.add_prefix(self.byok_radio)
        else:
            # BYOK only mode - simpler UI
            group.set_description("Connect TuxAgent to an AI provider using your API key")

            byok_row = Adw.ExpanderRow()
            byok_row.set_title("API Key")
            byok_row.set_subtitle("Get a key from Together.ai or OpenAI")
            byok_row.set_expanded(True)  # Start expanded since it's the only option

        # Provider dropdown
        provider_row = Adw.ActionRow()
        provider_row.set_title("Provider")

        self.provider_dropdown = Gtk.DropDown.new_from_strings(["Together.ai (Kimi K2.5)", "OpenAI (GPT-5.2)"])
        current_provider = TuxAgentConfig.get_byok_provider()
        self.provider_dropdown.set_selected(0 if current_provider == BYOKProvider.TOGETHER.value else 1)
        self.provider_dropdown.connect("notify::selected", self._on_provider_changed)
        provider_row.add_suffix(self.provider_dropdown)

        byok_row.add_row(provider_row)

        # API Key input
        api_key_row = Adw.ActionRow()
        api_key_row.set_title("API Key")

        self.api_key_entry = Gtk.Entry()
        self.api_key_entry.set_hexpand(True)
        self.api_key_entry.set_placeholder_text("Enter your API key")
        self.api_key_entry.set_text(TuxAgentConfig.get_byok_api_key())
        self.api_key_entry.set_visibility(False)
        api_key_row.add_suffix(self.api_key_entry)

        byok_row.add_row(api_key_row)

        # Test connection button
        test_row = Adw.ActionRow()
        test_row.set_title("Verify your key works")

        self.test_spinner = Gtk.Spinner()
        self.test_spinner.set_visible(False)
        test_row.add_suffix(self.test_spinner)

        self.test_btn = Gtk.Button(label="Test Connection")
        self.test_btn.connect("clicked", self._on_test_connection)
        test_row.add_suffix(self.test_btn)

        byok_row.add_row(test_row)

        # Get API key links
        for provider_id, info in PROVIDER_INFO.items():
            link_row = Adw.ActionRow()
            link_row.set_title(f"Get {info['name']} API key")
            link_btn = Gtk.LinkButton.new_with_label(info['signup_url'], "Sign up")
            link_row.add_suffix(link_btn)
            byok_row.add_row(link_row)

        group.add(byok_row)

        return group

    def _build_shortcuts_section(self) -> Gtk.Widget:
        """Build the Keyboard Shortcuts section"""
        group = Adw.PreferencesGroup()
        group.set_title("Keyboard Shortcuts")
        group.set_description("Global hotkeys to activate TuxAgent")

        # Open TuxAgent hotkey
        hotkey_row = Adw.ActionRow()
        hotkey_row.set_title("Open TuxAgent")

        self.hotkey_entry = Gtk.Entry()
        self.hotkey_entry.set_text(TuxAgentConfig.get_hotkey())
        self.hotkey_entry.set_width_chars(20)
        self.hotkey_entry.set_editable(False)
        hotkey_row.add_suffix(self.hotkey_entry)

        hotkey_change_btn = Gtk.Button(label="Change")
        hotkey_change_btn.connect("clicked", self._on_change_hotkey, "hotkey")
        hotkey_row.add_suffix(hotkey_change_btn)

        group.add(hotkey_row)

        # Screenshot hotkey
        screenshot_row = Adw.ActionRow()
        screenshot_row.set_title("Take Screenshot")

        self.screenshot_hotkey_entry = Gtk.Entry()
        self.screenshot_hotkey_entry.set_text(TuxAgentConfig.get_screenshot_hotkey())
        self.screenshot_hotkey_entry.set_width_chars(20)
        self.screenshot_hotkey_entry.set_editable(False)
        screenshot_row.add_suffix(self.screenshot_hotkey_entry)

        screenshot_change_btn = Gtk.Button(label="Change")
        screenshot_change_btn.connect("clicked", self._on_change_hotkey, "screenshot")
        screenshot_row.add_suffix(screenshot_change_btn)

        group.add(screenshot_row)

        # Info about hotkey registration
        info_row = Adw.ActionRow()
        info_row.set_title("Note")
        info_row.set_subtitle("Global hotkeys require the TuxAgent daemon to be running")
        info_row.add_css_class("dim-label")
        group.add(info_row)

        return group

    def _build_general_section(self) -> Gtk.Widget:
        """Build the General settings section"""
        group = Adw.PreferencesGroup()
        group.set_title("General")

        # Autostart
        autostart_row = Adw.ActionRow()
        autostart_row.set_title("Start on login")
        autostart_row.set_subtitle("Launch TuxAgent daemon when you log in")

        self.autostart_switch = Gtk.Switch()
        self.autostart_switch.set_active(TuxAgentConfig.is_autostart_enabled())
        self.autostart_switch.set_valign(Gtk.Align.CENTER)
        self.autostart_switch.connect("notify::active", self._on_autostart_changed)
        autostart_row.add_suffix(self.autostart_switch)

        group.add(autostart_row)

        # Theme
        theme_row = Adw.ActionRow()
        theme_row.set_title("Theme")
        theme_row.set_subtitle("Appearance of TuxAgent windows")

        self.theme_dropdown = Gtk.DropDown.new_from_strings(["System", "Light", "Dark"])
        current_theme = TuxAgentConfig.get_theme()
        theme_map = {"system": 0, "light": 1, "dark": 2}
        self.theme_dropdown.set_selected(theme_map.get(current_theme, 0))
        self.theme_dropdown.connect("notify::selected", self._on_theme_changed)
        theme_row.add_suffix(self.theme_dropdown)

        group.add(theme_row)

        return group

    # ========== Event Handlers ==========

    def _on_mode_changed(self, button, mode: str):
        """Handle API mode radio button change"""
        if button.get_active():
            TuxAgentConfig.set_api_mode(mode)
            self._notify_settings_changed()
            logger.info(f"API mode changed to: {mode}")

    def _on_provider_changed(self, dropdown, param):
        """Handle BYOK provider dropdown change"""
        selected = dropdown.get_selected()
        provider = BYOKProvider.TOGETHER.value if selected == 0 else BYOKProvider.OPENAI.value
        TuxAgentConfig.set_byok_provider(provider)

        # Clear API key entry since provider changed
        self.api_key_entry.set_text(TuxAgentConfig.get_byok_api_key())

        self._notify_settings_changed()
        logger.info(f"BYOK provider changed to: {provider}")

    def _on_activate_license(self, button):
        """Handle license activation"""
        license_key = self.license_entry.get_text().strip()
        if not license_key:
            self._show_message("Error", "Please enter a license key")
            return

        # Save the license key
        TuxAgentConfig.set_license_key(license_key)

        # Also save to the legacy license.json format for compatibility
        self._save_legacy_license(license_key)

        # Switch to cloud mode
        TuxAgentConfig.set_api_mode(APIMode.CLOUD.value)
        self.cloud_radio.set_active(True)

        self._show_message("Success", "License key activated! You're now using TuxAgent Cloud.")
        self._notify_settings_changed()

    def _save_legacy_license(self, license_key: str):
        """Save license in legacy format for backwards compatibility"""
        import json
        license_file = Path.home() / '.config' / 'tuxagent' / 'license.json'
        try:
            license_file.parent.mkdir(parents=True, exist_ok=True)
            with open(license_file, 'w') as f:
                json.dump({
                    "license_key": license_key,
                    "status": "active"
                }, f)
            license_file.chmod(0o600)
        except Exception as e:
            logger.error(f"Failed to save legacy license: {e}")

    def _on_test_connection(self, button):
        """Test BYOK API connection"""
        api_key = self.api_key_entry.get_text().strip()
        if not api_key:
            self._show_message("Error", "Please enter an API key first")
            return

        # Save the API key first
        TuxAgentConfig.set_byok_api_key(api_key)

        # Show spinner
        self.test_btn.set_sensitive(False)
        self.test_spinner.set_visible(True)
        self.test_spinner.start()

        def do_test():
            provider = get_provider_for_mode(
                api_mode=APIMode.BYOK.value,
                byok_provider=TuxAgentConfig.get_byok_provider(),
                api_key=api_key,
                openai_model=TuxAgentConfig.get_openai_model()
            )
            result = provider.test_connection()
            GLib.idle_add(self._on_test_complete, result)

        thread = threading.Thread(target=do_test, daemon=True)
        thread.start()

    def _on_test_complete(self, result):
        """Handle test connection result"""
        self.test_btn.set_sensitive(True)
        self.test_spinner.stop()
        self.test_spinner.set_visible(False)

        if result["success"]:
            self._show_message("Success", "API connection successful!")
            # Switch to BYOK mode
            TuxAgentConfig.set_api_mode(APIMode.BYOK.value)
            # Only update radio button if monetization is enabled
            if hasattr(self, 'byok_radio'):
                self.byok_radio.set_active(True)
            self._notify_settings_changed()
        else:
            self._show_message("Connection Failed", f"Could not connect: {result['message']}")

    def _on_change_hotkey(self, button, hotkey_type: str):
        """Open hotkey capture dialog"""
        dialog = HotkeyCaptureDialog(
            parent=self,
            hotkey_type=hotkey_type,
            on_captured=self._on_hotkey_captured
        )
        dialog.present()

    def _on_hotkey_captured(self, hotkey_type: str, hotkey: str):
        """Handle captured hotkey"""
        if hotkey_type == "hotkey":
            TuxAgentConfig.set_hotkey(hotkey)
            self.hotkey_entry.set_text(hotkey)
        else:
            TuxAgentConfig.set_screenshot_hotkey(hotkey)
            self.screenshot_hotkey_entry.set_text(hotkey)

        self._notify_settings_changed()
        logger.info(f"Hotkey {hotkey_type} changed to: {hotkey}")

    def _on_autostart_changed(self, switch, param):
        """Handle autostart toggle"""
        enabled = switch.get_active()
        TuxAgentConfig.set_autostart_enabled(enabled)
        self._update_autostart_file(enabled)
        self._notify_settings_changed()

    def _update_autostart_file(self, enabled: bool):
        """Create or remove autostart desktop file"""
        autostart_dir = Path.home() / ".config" / "autostart"
        autostart_file = autostart_dir / "tuxagent-daemon.desktop"

        if enabled:
            autostart_dir.mkdir(parents=True, exist_ok=True)
            desktop_content = """[Desktop Entry]
Type=Application
Name=TuxAgent Daemon
Comment=TuxAgent AI Assistant Background Service
Exec=tuxagent-daemon
Icon=dialog-question
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
"""
            try:
                with open(autostart_file, 'w') as f:
                    f.write(desktop_content)
            except Exception as e:
                logger.error(f"Failed to create autostart file: {e}")
        else:
            try:
                if autostart_file.exists():
                    autostart_file.unlink()
            except Exception as e:
                logger.error(f"Failed to remove autostart file: {e}")

    def _on_theme_changed(self, dropdown, param):
        """Handle theme dropdown change"""
        selected = dropdown.get_selected()
        theme_map = {0: "system", 1: "light", 2: "dark"}
        theme = theme_map.get(selected, "system")
        TuxAgentConfig.set_theme(theme)

        # Apply theme immediately
        style_manager = Adw.StyleManager.get_default()
        if theme == "light":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif theme == "dark":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

        self._notify_settings_changed()

    def _notify_settings_changed(self):
        """Notify parent that settings have changed"""
        if self.on_settings_changed:
            self.on_settings_changed()

    def _show_message(self, title: str, message: str):
        """Show a simple message dialog"""
        dialog = Adw.MessageDialog.new(self, title, message)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present()


class HotkeyCaptureDialog(Adw.Window):
    """Dialog to capture a keyboard shortcut"""

    def __init__(self, parent=None, hotkey_type: str = "hotkey", on_captured=None, **kwargs):
        super().__init__(**kwargs)

        self.hotkey_type = hotkey_type
        self.on_captured = on_captured
        self.captured_keys = []
        self.captured_modifiers = []

        self.set_title("Set Shortcut")
        self.set_default_size(350, 200)
        self.set_modal(True)
        if parent:
            self.set_transient_for(parent)

        self._build_ui()

    def _build_ui(self):
        """Build the dialog UI"""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)

        main_box.append(header)

        # Content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_valign(Gtk.Align.CENTER)
        content.set_vexpand(True)

        # Instructions
        label = Gtk.Label(label="Press the key combination you want to use")
        label.add_css_class("title-3")
        content.append(label)

        # Hotkey display
        self.hotkey_label = Gtk.Label(label="...")
        self.hotkey_label.add_css_class("title-1")
        self.hotkey_label.add_css_class("monospace")
        content.append(self.hotkey_label)

        # Hint
        hint = Gtk.Label(label="Use modifiers like Super, Ctrl, Alt, Shift")
        hint.add_css_class("dim-label")
        hint.add_css_class("caption")
        content.append(hint)

        main_box.append(content)

        # Key capture
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(controller)

        self.set_content(main_box)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle key press for hotkey capture"""
        from gi.repository import Gdk

        # Get modifier names
        modifiers = []
        if state & Gdk.ModifierType.SUPER_MASK:
            modifiers.append("Super")
        if state & Gdk.ModifierType.CONTROL_MASK:
            modifiers.append("Ctrl")
        if state & Gdk.ModifierType.ALT_MASK:
            modifiers.append("Alt")
        if state & Gdk.ModifierType.SHIFT_MASK:
            modifiers.append("Shift")

        # Get key name
        key_name = Gdk.keyval_name(keyval)

        # Ignore standalone modifier keys
        if key_name in ("Super_L", "Super_R", "Control_L", "Control_R",
                       "Alt_L", "Alt_R", "Shift_L", "Shift_R", "Meta_L", "Meta_R"):
            return True

        # Build hotkey string
        if modifiers:
            hotkey = "+".join(modifiers) + "+" + key_name.upper()
        else:
            hotkey = key_name.upper()

        self.hotkey_label.set_text(hotkey)

        # Require at least one modifier for global hotkeys
        if not modifiers:
            self.hotkey_label.set_text(f"{hotkey} (needs modifier)")
            return True

        # Valid hotkey captured - save and close after brief delay
        GLib.timeout_add(500, self._save_and_close, hotkey)
        return True

    def _save_and_close(self, hotkey: str):
        """Save the hotkey and close dialog"""
        if self.on_captured:
            self.on_captured(self.hotkey_type, hotkey)
        self.close()
        return False
