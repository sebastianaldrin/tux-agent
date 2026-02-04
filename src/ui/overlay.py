"""
TuxAgent Overlay Window
Main GTK4/libadwaita floating popup interface
"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gdk, Gio
import dbus
import threading
import logging
from pathlib import Path

from .widgets import MessageBubble, ThinkingIndicator, ChatInput, ScreenshotPreview, FileAttachmentPreview
from .extensions_dialog import ExtensionsDialog
from .settings_dialog import SettingsDialog

# Add parent path for config import
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.config import TuxAgentConfig, APIMode

logger = logging.getLogger(__name__)

# D-Bus configuration
DBUS_SERVICE_NAME = "org.tuxagent.Assistant"
DBUS_OBJECT_PATH = "/org/tuxagent/Assistant"
DBUS_INTERFACE = "org.tuxagent.Assistant"
DBUS_TIMEOUT = 600  # 10 minutes for long-running operations


class TuxAgentOverlay(Adw.ApplicationWindow):
    """
    Main overlay window for TuxAgent
    Floating, centered popup with chat interface
    """

    def __init__(self, app: Adw.Application, **kwargs):
        super().__init__(application=app, **kwargs)

        self.set_title("TuxAgent")
        self.set_default_size(500, 600)
        self.set_resizable(True)

        # Make it a floating window
        self.set_decorated(True)

        # D-Bus connection
        self._dbus_proxy = None
        self._connect_dbus()

        # Screenshot data
        self._pending_screenshot = None

        # File contexts - accumulates throughout conversation
        self._conversation_file_contexts = []

        # Build UI
        self._build_ui()

        # Load CSS
        self._load_css()

        # Connect signals
        self._connect_signals()

    def _connect_dbus(self):
        """Connect to TuxAgent D-Bus service"""
        try:
            bus = dbus.SessionBus()
            proxy_obj = bus.get_object(DBUS_SERVICE_NAME, DBUS_OBJECT_PATH)
            self._dbus_proxy = dbus.Interface(proxy_obj, DBUS_INTERFACE)

            # Connect to signals for progress feedback
            proxy_obj.connect_to_signal(
                "ToolExecuting",
                self._on_tool_executing,
                dbus_interface=DBUS_INTERFACE
            )
            proxy_obj.connect_to_signal(
                "ResponseChunk",
                self._on_response_chunk,
                dbus_interface=DBUS_INTERFACE
            )

            logger.info("Connected to TuxAgent D-Bus service")
        except Exception as e:
            logger.error(f"Failed to connect to D-Bus: {e}")
            self._dbus_proxy = None

    def _on_tool_executing(self, tool_name):
        """Handle tool execution signal - update UI with progress"""
        GLib.idle_add(self._update_thinking_status, f"Running: {tool_name}")

    def _on_response_chunk(self, chunk):
        """Handle response chunk signal"""
        GLib.idle_add(self._update_thinking_status, chunk)

    def _update_thinking_status(self, status):
        """Update thinking indicator with current status"""
        if hasattr(self, 'thinking') and self.thinking:
            self.thinking.set_message(status)

    def _load_css(self):
        """Load custom CSS styles"""
        css_provider = Gtk.CssProvider()

        # Load from file
        css_path = Path(__file__).parent / "styles.css"
        if css_path.exists():
            css_provider.load_from_path(str(css_path))
        else:
            # Inline fallback CSS
            css_provider.load_from_data(b"""
                .message-bubble { padding: 12px 16px; border-radius: 12px; margin: 4px 0; }
                .user-message { background-color: @accent_bg_color; }
                .assistant-message { background-color: @card_bg_color; border: 1px solid @borders; }
                .chat-input { padding: 12px 16px; border-top: 1px solid @borders; }
            """)

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _build_ui(self):
        """Build the UI components"""
        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header bar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)

        # Title
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon = Gtk.Image.new_from_icon_name("dialog-question-symbolic")
        title_box.append(icon)
        title_label = Gtk.Label(label="TuxAgent")
        title_label.add_css_class("title")
        title_box.append(title_label)
        header.set_title_widget(title_box)

        # New chat button
        new_chat_btn = Gtk.Button()
        new_chat_btn.set_icon_name("list-add-symbolic")
        new_chat_btn.set_tooltip_text("New conversation")
        new_chat_btn.connect("clicked", self._on_new_chat)
        header.pack_start(new_chat_btn)

        # Settings button
        settings_btn = Gtk.Button()
        settings_btn.set_icon_name("emblem-system-symbolic")
        settings_btn.set_tooltip_text("Settings")
        settings_btn.connect("clicked", self._on_settings_clicked)
        header.pack_end(settings_btn)

        # Extensions button
        extensions_btn = Gtk.Button()
        extensions_btn.set_icon_name("application-x-addon-symbolic")
        extensions_btn.set_tooltip_text("Extensions")
        extensions_btn.connect("clicked", self._on_extensions_clicked)
        header.pack_end(extensions_btn)

        main_box.append(header)

        # Usage warning banner (hidden by default)
        self.warning_banner = self._create_warning_banner()
        main_box.append(self.warning_banner)

        # Chat area (scrollable)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add_css_class("chat-scroll")

        self.chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.chat_box.set_margin_start(16)
        self.chat_box.set_margin_end(16)
        self.chat_box.set_margin_top(16)
        self.chat_box.set_margin_bottom(16)

        # Welcome message
        self._add_welcome_message()

        scroll.set_child(self.chat_box)
        main_box.append(scroll)
        self.scroll = scroll

        # Thinking indicator (hidden by default)
        self.thinking = ThinkingIndicator()
        self.thinking.set_margin_start(16)
        self.thinking.set_visible(False)
        main_box.append(self.thinking)

        # Screenshot preview (hidden by default)
        self.screenshot_preview = ScreenshotPreview(on_remove=self._on_screenshot_removed)
        self.screenshot_preview.set_margin_start(16)
        self.screenshot_preview.set_margin_end(16)
        main_box.append(self.screenshot_preview)

        # File attachment preview (hidden by default)
        self.file_preview = FileAttachmentPreview(on_remove=self._on_file_removed)
        self.file_preview.set_margin_start(16)
        self.file_preview.set_margin_end(16)
        main_box.append(self.file_preview)

        # Input area
        self.chat_input = ChatInput(
            on_send=self._on_send_message,
            on_screenshot=self._on_take_screenshot
        )
        main_box.append(self.chat_input)

        # Status bar
        self.status_bar = Gtk.Label(label="Ready")
        self.status_bar.add_css_class("status-bar")
        self.status_bar.set_halign(Gtk.Align.START)
        main_box.append(self.status_bar)

        self.set_content(main_box)

        # Check if warning banner should be shown
        self._update_warning_banner()

    def _add_welcome_message(self):
        """Add welcome message to chat"""
        welcome_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        welcome_box.add_css_class("welcome-message")
        welcome_box.set_valign(Gtk.Align.CENTER)
        welcome_box.set_vexpand(True)

        # Icon
        icon = Gtk.Image.new_from_icon_name("dialog-question-symbolic")
        icon.set_pixel_size(48)
        welcome_box.append(icon)

        # Title
        title = Gtk.Label(label="Welcome to TuxAgent!")
        title.add_css_class("welcome-title")
        welcome_box.append(title)

        # Subtitle
        subtitle = Gtk.Label(label="Your friendly Linux desktop assistant.\nAsk me anything about your system!")
        subtitle.add_css_class("welcome-subtitle")
        subtitle.set_justify(Gtk.Justification.CENTER)
        welcome_box.append(subtitle)

        # Quick action buttons
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_box.add_css_class("quick-actions")
        actions_box.set_halign(Gtk.Align.CENTER)

        quick_actions = [
            ("What's using my RAM?", "process-working-symbolic"),
            ("Screenshot help", "camera-photo-symbolic"),
            ("System info", "computer-symbolic"),
        ]

        for label, icon_name in quick_actions:
            btn = Gtk.Button(label=label)
            btn.add_css_class("quick-action-btn")
            btn.connect("clicked", lambda b, q=label: self._quick_action(q))
            actions_box.append(btn)

        welcome_box.append(actions_box)

        self.welcome_box = welcome_box
        self.chat_box.append(welcome_box)

    def _connect_signals(self):
        """Connect keyboard shortcuts"""
        # Escape to close
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(controller)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle key press events"""
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True

        # Ctrl+Shift+S for screenshot
        if keyval == Gdk.KEY_S and state & Gdk.ModifierType.CONTROL_MASK and state & Gdk.ModifierType.SHIFT_MASK:
            self._on_take_screenshot()
            return True

        return False

    def _quick_action(self, question: str):
        """Handle quick action button click"""
        self._send_message(question)

    def _on_send_message(self, text: str):
        """Handle send message from input"""
        self._send_message(text)

    def _send_message(self, text: str):
        """Send a message to TuxAgent"""
        if not text.strip():
            # Show hint if they have attachment but no text
            if self._pending_screenshot or self.file_preview.get_file_path():
                self.status_bar.set_text("Please type a question about your attachment")
            return

        # Remove welcome message if present
        if hasattr(self, 'welcome_box') and self.welcome_box.get_parent():
            self.chat_box.remove(self.welcome_box)

        # Get screenshot if attached (before creating bubble)
        screenshot = self._pending_screenshot
        self._pending_screenshot = None
        self.screenshot_preview.clear()

        # Get file attachment info BEFORE clearing
        file_name = None
        file_path = None
        if self.file_preview.get_file_path():
            import os
            file_path = self.file_preview.get_file_path()
            file_name = os.path.basename(file_path)

        # Add file context if attached (accumulates in conversation)
        if self.file_preview.get_file_path():
            new_context = self.file_preview.get_context_string()
            self._conversation_file_contexts.append(new_context)
            self.file_preview.clear()  # Clear AFTER getting the name

        # Build the full message (include all file contexts from this conversation)
        if self._conversation_file_contexts:
            all_contexts = "\n---\n".join(self._conversation_file_contexts)
            full_message = all_contexts + "\n\nUser question: " + text
        else:
            full_message = text

        # Add user message bubble WITH screenshot/file visible
        user_bubble = MessageBubble(
            text,
            is_user=True,
            screenshot_data=screenshot,
            file_name=file_name,
            file_path=file_path
        )
        self.chat_box.append(user_bubble)

        # Show thinking indicator
        self.thinking.start("Thinking...")
        self.chat_input.set_sensitive(False)

        # Send to daemon in background thread
        def do_request():
            try:
                if self._dbus_proxy is None:
                    return "Error: TuxAgent daemon is not running. Start it with: tuxagent-daemon"

                if screenshot:
                    response = self._dbus_proxy.AskWithScreenshot(full_message, screenshot, timeout=DBUS_TIMEOUT)
                else:
                    response = self._dbus_proxy.Ask(full_message, timeout=DBUS_TIMEOUT)
                return response
            except Exception as e:
                logger.error(f"Request failed: {e}")
                return f"Error: {str(e)}"

        def on_response(response):
            # Add assistant message
            assistant_bubble = MessageBubble(response, is_user=False)
            self.chat_box.append(assistant_bubble)

            # Hide thinking, enable input
            self.thinking.stop()
            self.chat_input.set_sensitive(True)
            self.chat_input.focus()

            # Scroll to bottom
            GLib.idle_add(self._scroll_to_bottom)

            # Update status
            self.status_bar.set_text("Ready")

            # Update warning banner (usage may have changed)
            self._update_warning_banner()

        # Run in thread
        def thread_func():
            response = do_request()
            GLib.idle_add(on_response, response)

        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()

        # Scroll to bottom
        GLib.idle_add(self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        """Scroll chat to bottom"""
        adj = self.scroll.get_vadjustment()
        adj.set_value(adj.get_upper())

    def _on_take_screenshot(self):
        """Handle screenshot request"""
        self.status_bar.set_text("Select area to capture...")
        self.chat_input.set_sensitive(False)  # Disable input during capture

        def do_screenshot():
            try:
                # Import screenshot service
                import sys
                sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                from src.daemon.screenshot import take_screenshot
                return take_screenshot(interactive=True)
            except Exception as e:
                logger.error(f"Screenshot failed: {e}")
                return None

        def on_screenshot(data):
            self.chat_input.set_sensitive(True)  # Re-enable input
            self.chat_input.focus()

            if data:
                self._pending_screenshot = data
                self.screenshot_preview.set_screenshot(data)
                self.status_bar.set_text("Screenshot attached - type your question")
            else:
                self.status_bar.set_text("Screenshot cancelled")

        # Run in thread
        def thread_func():
            data = do_screenshot()
            GLib.idle_add(on_screenshot, data)

        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()

    def _on_screenshot_removed(self):
        """Handle screenshot removal"""
        self._pending_screenshot = None
        self.status_bar.set_text("Ready")

    def _on_file_removed(self):
        """Handle file attachment removal"""
        self.status_bar.set_text("Ready")

    def attach_file(self, file_path: str):
        """Attach a file to the conversation"""
        import os
        if os.path.exists(file_path):
            self.file_preview.set_file(file_path)
            self.status_bar.set_text(f"File attached: {os.path.basename(file_path)}")
            self.chat_input.focus()

    def _on_extensions_clicked(self, button):
        """Handle extensions button click"""
        dialog = ExtensionsDialog(parent=self)
        dialog.present()

    def _on_settings_clicked(self, button):
        """Handle settings button click"""
        try:
            dialog = SettingsDialog(
                parent=self,
                on_settings_changed=self._on_settings_changed
            )
            dialog.present()
        except Exception as e:
            logger.error(f"Failed to open settings dialog: {e}")
            import traceback
            traceback.print_exc()

    def _on_settings_changed(self):
        """Handle settings changes - refresh provider and UI"""
        # Notify daemon to refresh its provider
        if self._dbus_proxy:
            try:
                self._dbus_proxy.RefreshProvider(timeout=5)
            except:
                pass  # Method might not exist in older daemon versions

        # Update warning banner
        self._update_warning_banner()

    def _create_warning_banner(self) -> Gtk.Widget:
        """Create the usage warning banner"""
        banner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        banner.add_css_class("warning-banner")
        banner.set_margin_start(16)
        banner.set_margin_end(16)
        banner.set_margin_top(8)
        banner.set_margin_bottom(0)
        banner.set_visible(False)

        # Warning icon
        icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
        banner.append(icon)

        # Warning text
        self.warning_label = Gtk.Label()
        self.warning_label.set_hexpand(True)
        self.warning_label.set_xalign(0)
        self.warning_label.add_css_class("warning-text")
        banner.append(self.warning_label)

        # Upgrade button
        upgrade_btn = Gtk.Button(label="Upgrade")
        upgrade_btn.add_css_class("suggested-action")
        upgrade_btn.add_css_class("pill")
        upgrade_btn.connect("clicked", lambda b: self._on_settings_clicked(b))
        banner.append(upgrade_btn)

        return banner

    def _update_warning_banner(self):
        """Update the warning banner based on current usage"""
        if TuxAgentConfig.should_show_usage_warning():
            remaining = TuxAgentConfig.get_usage_remaining()
            mode = TuxAgentConfig.get_api_mode()

            if mode == APIMode.FREE.value:
                self.warning_label.set_text(f"{remaining} free queries left this month")
            else:
                self.warning_label.set_text(f"{remaining} queries remaining this month")

            self.warning_banner.set_visible(True)
        else:
            self.warning_banner.set_visible(False)

    def _on_new_chat(self, button):
        """Handle new chat button"""
        # Clear chat
        while True:
            child = self.chat_box.get_first_child()
            if child is None:
                break
            self.chat_box.remove(child)

        # Add welcome message back
        self._add_welcome_message()

        # Clear pending screenshot and file contexts
        self._pending_screenshot = None
        self.screenshot_preview.clear()
        self._conversation_file_contexts = []
        self.file_preview.clear()

        # Create new thread in daemon
        if self._dbus_proxy:
            try:
                self._dbus_proxy.CreateThread(timeout=DBUS_TIMEOUT)
            except:
                pass

        self.status_bar.set_text("New conversation started")


class TuxAgentApp(Adw.Application):
    """Main GTK Application for TuxAgent overlay"""

    def __init__(self, attach_file=None):
        super().__init__(
            application_id="org.tuxagent.Overlay",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE
        )
        self.window = None
        self.attach_file = attach_file

    def do_activate(self):
        """Activate the application"""
        if not self.window:
            self.window = TuxAgentOverlay(self)

        # Attach file if specified
        if self.attach_file:
            self.window.attach_file(self.attach_file)
            self.attach_file = None  # Clear after attaching

        self.window.present()

    def do_command_line(self, command_line):
        """Handle command line arguments (even when app is already running)"""
        args = command_line.get_arguments()

        # Parse --file argument
        for i, arg in enumerate(args):
            if arg in ("--file", "-f") and i + 1 < len(args):
                self.attach_file = args[i + 1]
                break
            elif arg.startswith("--file="):
                self.attach_file = arg.split("=", 1)[1]
                break

        self.activate()
        return 0


def main():
    """Entry point for GTK overlay"""
    import sys
    import dbus.mainloop.glib

    # Enable D-Bus GLib main loop integration for signal handling
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    # Pre-parse --file for initial launch (before GTK takes over)
    attach_file = None
    for i, arg in enumerate(sys.argv):
        if arg in ("--file", "-f") and i + 1 < len(sys.argv):
            attach_file = sys.argv[i + 1]
            break
        elif arg.startswith("--file="):
            attach_file = arg.split("=", 1)[1]
            break

    app = TuxAgentApp(attach_file=attach_file)
    return app.run(sys.argv)


if __name__ == "__main__":
    main()
