"""
TuxAgent Extensions Dialog
GUI for managing TuxAgent extensions
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

from src.core.extension_manager import ExtensionManager, EXTENSIONS

logger = logging.getLogger(__name__)


class SimpleDialog(Adw.Window):
    """Simple dialog for messages and confirmations"""

    def __init__(self, parent, title, message, buttons=None, on_response=None, **kwargs):
        super().__init__(**kwargs)

        self.on_response = on_response
        self.response_value = None

        self.set_title(title)
        self.set_default_size(400, -1)
        self.set_modal(True)
        if parent:
            self.set_transient_for(parent)

        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        main_box.append(header)

        # Content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_margin_top(16)
        content.set_margin_bottom(24)

        # Message
        label = Gtk.Label(label=message)
        label.set_wrap(True)
        label.set_xalign(0)
        label.set_max_width_chars(50)
        content.append(label)

        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(8)

        if buttons is None:
            buttons = [("OK", "ok", True)]

        for label_text, response_id, is_suggested in buttons:
            btn = Gtk.Button(label=label_text)
            if is_suggested:
                btn.add_css_class("suggested-action")
            elif response_id == "cancel":
                pass  # Default style for cancel
            else:
                btn.add_css_class("destructive-action")
            btn.connect("clicked", self._on_button_clicked, response_id)
            button_box.append(btn)

        content.append(button_box)
        main_box.append(content)

        self.set_content(main_box)

    def _on_button_clicked(self, button, response_id):
        self.response_value = response_id
        if self.on_response:
            self.on_response(response_id)
        self.close()


class ExtensionRow(Adw.ActionRow):
    """A row representing an extension in the list"""

    def __init__(self, ext_id: str, ext_info: dict, manager: ExtensionManager,
                 parent_window=None, on_status_change=None, **kwargs):
        super().__init__(**kwargs)

        self.ext_id = ext_id
        self.ext_info = ext_info
        self.manager = manager
        self.parent_window = parent_window
        self.on_status_change = on_status_change

        # Set row content
        self.set_title(ext_info["name"])
        self.set_subtitle(ext_info["description"])

        # Add desktop badge
        desktop_label = Gtk.Label(label=ext_info["desktop"])
        desktop_label.add_css_class("dim-label")
        desktop_label.add_css_class("caption")
        self.add_prefix(desktop_label)

        # Install/Remove button
        self.action_button = Gtk.Button()
        self.action_button.set_valign(Gtk.Align.CENTER)
        self.action_button.connect("clicked", self._on_action_clicked)
        self.add_suffix(self.action_button)

        # Spinner for loading state
        self.spinner = Gtk.Spinner()
        self.spinner.set_visible(False)
        self.add_suffix(self.spinner)

        # Update button state
        self._update_button_state()

    def _update_button_state(self):
        """Update button based on installation status"""
        is_installed = self.manager.is_installed(self.ext_id)
        is_available = self.manager._is_available(self.ext_id)

        if is_installed:
            self.action_button.set_label("Remove")
            self.action_button.remove_css_class("suggested-action")
            self.action_button.add_css_class("destructive-action")
            self.action_button.set_sensitive(True)
        elif is_available:
            self.action_button.set_label("Install")
            self.action_button.remove_css_class("destructive-action")
            self.action_button.add_css_class("suggested-action")
            self.action_button.set_sensitive(True)
        else:
            self.action_button.set_label("Unavailable")
            self.action_button.set_sensitive(False)

    def _on_action_clicked(self, button):
        """Handle install/remove button click"""
        is_installed = self.manager.is_installed(self.ext_id)

        if is_installed:
            self._do_remove()
        else:
            self._do_install()

    def _set_loading(self, loading: bool):
        """Show/hide loading state"""
        self.action_button.set_visible(not loading)
        self.spinner.set_visible(loading)
        if loading:
            self.spinner.start()
        else:
            self.spinner.stop()

    def _do_install(self):
        """Install the extension"""
        # First check dependencies
        dep_check = self.manager.check_dependencies(self.ext_id)

        if not dep_check["satisfied"]:
            # Show dependency dialog
            self._show_dependency_dialog(dep_check)
            return

        # Dependencies satisfied, proceed with install
        self._perform_install()

    def _show_dependency_dialog(self, dep_check):
        """Show dialog asking to install dependencies"""
        missing = dep_check["missing"]

        message = (
            f"The '{self.ext_info['name']}' extension requires:\n\n" +
            "\n".join(f"  • {dep}" for dep in missing) +
            "\n\nInstall these packages now?"
        )

        def on_response(response_id):
            if response_id == "install":
                self._install_dependencies(dep_check)

        dialog = SimpleDialog(
            parent=self.parent_window,
            title="Required Packages",
            message=message,
            buttons=[
                ("Cancel", "cancel", False),
                ("Install", "install", True),
            ],
            on_response=on_response
        )
        dialog.present()

    def _install_dependencies(self, dep_check):
        """Install dependencies using pkexec (graphical sudo)"""
        self._set_loading(True)

        def do_install():
            success = True
            error_msg = ""

            for dep in dep_check["missing"]:
                try:
                    # Use pkexec for graphical sudo prompt
                    result = subprocess.run(
                        ["pkexec", "apt", "install", "-y", dep],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        success = False
                        error_msg = result.stderr or f"Failed to install {dep}"
                        break
                except FileNotFoundError:
                    success = False
                    error_msg = "Could not find pkexec. Please install packages manually."
                    break
                except Exception as e:
                    success = False
                    error_msg = str(e)
                    break

            GLib.idle_add(self._on_deps_installed, success, error_msg)

        thread = threading.Thread(target=do_install, daemon=True)
        thread.start()

    def _on_deps_installed(self, success: bool, error_msg: str):
        """Called after dependency installation attempt"""
        self._set_loading(False)

        if success:
            # Now install the extension
            self._perform_install()
        else:
            # Show error dialog
            deps = EXTENSIONS[self.ext_id].get('dependencies', [])
            message = (
                f"Could not install packages:\n\n{error_msg}\n\n"
                f"Install manually with:\n  sudo apt install {' '.join(deps)}"
            )
            dialog = SimpleDialog(
                parent=self.parent_window,
                title="Installation Failed",
                message=message
            )
            dialog.present()

    def _perform_install(self):
        """Actually install the extension (deps already satisfied)"""
        self._set_loading(True)

        def do_install():
            result = self.manager.install(self.ext_id, auto_deps=True)
            GLib.idle_add(self._on_install_complete, result)

        thread = threading.Thread(target=do_install, daemon=True)
        thread.start()

    def _on_install_complete(self, result):
        """Called after installation attempt"""
        self._set_loading(False)
        self._update_button_state()

        if result["success"]:
            # Show success with hints
            hints = result.get("hints", [])
            message = "Extension installed successfully!"
            if hints:
                message += "\n\n" + "\n".join(f"• {hint}" for hint in hints)

            dialog = SimpleDialog(
                parent=self.parent_window,
                title="Installed!",
                message=message
            )
            dialog.present()

            if self.on_status_change:
                self.on_status_change()
        else:
            dialog = SimpleDialog(
                parent=self.parent_window,
                title="Installation Failed",
                message=result.get("message", "Unknown error")
            )
            dialog.present()

    def _do_remove(self):
        """Remove the extension"""
        self._set_loading(True)

        def do_remove():
            result = self.manager.remove(self.ext_id)
            GLib.idle_add(self._on_remove_complete, result)

        thread = threading.Thread(target=do_remove, daemon=True)
        thread.start()

    def _on_remove_complete(self, result):
        """Called after removal attempt"""
        self._set_loading(False)
        self._update_button_state()

        if not result["success"]:
            dialog = SimpleDialog(
                parent=self.parent_window,
                title="Removal Failed",
                message=result.get("message", "Unknown error")
            )
            dialog.present()

        if self.on_status_change:
            self.on_status_change()


class ExtensionsDialog(Adw.Window):
    """Dialog for managing TuxAgent extensions"""

    def __init__(self, parent=None, **kwargs):
        super().__init__(**kwargs)

        self.set_title("Extensions")
        self.set_default_size(450, 500)
        self.set_modal(True)
        if parent:
            self.set_transient_for(parent)

        self.manager = ExtensionManager()

        self._build_ui()

    def _build_ui(self):
        """Build the dialog UI"""
        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header bar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)
        main_box.append(header)

        # Content
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_margin_top(24)
        content.set_margin_bottom(24)

        # Description
        desc = Gtk.Label(
            label="Extend TuxAgent with integrations for your desktop environment."
        )
        desc.set_wrap(True)
        desc.set_xalign(0)
        desc.add_css_class("dim-label")
        content.append(desc)

        # Detected desktop
        desktop = self.manager.detect_desktop()
        desktop_label = Gtk.Label(label=f"Detected desktop: {desktop}")
        desktop_label.set_xalign(0)
        desktop_label.add_css_class("caption")
        content.append(desktop_label)

        # Track all rows for refresh
        self.extension_rows = []

        # Recommended section
        recommended = self.manager.get_recommended()
        if recommended:
            rec_group = Adw.PreferencesGroup()
            rec_group.set_title("Recommended for You")
            rec_group.set_description("Extensions that work with your desktop")

            for ext_id in recommended:
                if ext_id in EXTENSIONS:
                    row = ExtensionRow(
                        ext_id=ext_id,
                        ext_info=EXTENSIONS[ext_id],
                        manager=self.manager,
                        parent_window=self,
                        on_status_change=self._refresh_all
                    )
                    rec_group.add(row)
                    self.extension_rows.append(row)

            content.append(rec_group)

        # All extensions section
        all_group = Adw.PreferencesGroup()
        all_group.set_title("All Extensions")

        for ext_id, ext_info in EXTENSIONS.items():
            if ext_id not in recommended:  # Don't duplicate recommended ones
                row = ExtensionRow(
                    ext_id=ext_id,
                    ext_info=ext_info,
                    manager=self.manager,
                    parent_window=self,
                    on_status_change=self._refresh_all
                )
                all_group.add(row)
                self.extension_rows.append(row)

        content.append(all_group)

        scroll.set_child(content)
        main_box.append(scroll)

        self.set_content(main_box)

    def _refresh_all(self):
        """Refresh all extension rows"""
        for row in self.extension_rows:
            row._update_button_state()
