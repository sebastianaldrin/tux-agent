"""
TuxAgent Nautilus Extension
Adds right-click context menu: "Ask TuxAgent about this file"
"""
import gi
gi.require_version('Nautilus', '3.0')
gi.require_version('Gtk', '3.0')

from gi.repository import Nautilus, GObject, Gio, GLib, Gtk
import os
import subprocess


class TuxAgentExtension(GObject.GObject, Nautilus.MenuProvider):
    """Nautilus extension for TuxAgent integration"""

    def _open_tuxagent_with_file(self, menu, files):
        """Open TuxAgent GUI with file attached"""
        if not files:
            return

        file_obj = files[0]
        file_path = file_obj.get_location().get_path()

        if not file_path:
            return

        # Open TuxAgent GUI with file attached
        try:
            subprocess.Popen(
                ["python3", "-m", "src.ui.main", "--file", file_path],
                cwd=os.path.expanduser("~/mina-projekt/tux-agent"),
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            # Show error notification
            subprocess.run([
                "notify-send",
                "--app-name=TuxAgent",
                "--icon=dialog-error",
                "TuxAgent Error",
                str(e)
            ], check=False)

    def get_file_items(self, window, files):
        """Get context menu items for files (Nautilus 3.0 API)"""
        if not files:
            return []

        # Only show for single file selection
        if len(files) != 1:
            return []

        file_obj = files[0]

        # Handle directories
        if file_obj.is_directory():
            item = Nautilus.MenuItem(
                name="TuxAgent::AskAboutDir",
                label="Ask TuxAgent about this folder",
                tip="Open TuxAgent with this folder attached",
                icon="dialog-question-symbolic"
            )
            item.connect("activate", self._open_tuxagent_with_file, files)
            return [item]

        # Handle files
        item = Nautilus.MenuItem(
            name="TuxAgent::AskAbout",
            label="Ask TuxAgent about this file",
            tip="Open TuxAgent with this file attached",
            icon="dialog-question-symbolic"
        )
        item.connect("activate", self._open_tuxagent_with_file, files)

        return [item]

    def get_background_items(self, window, current_folder):
        """Get context menu items for background clicks"""
        return []
