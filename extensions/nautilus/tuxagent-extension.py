"""
TuxAgent Nautilus Extension
Adds "Ask TuxAgent" to file context menu
"""
import os
import subprocess
from urllib.parse import unquote
from gi.repository import Nautilus, GObject, Gio


class TuxAgentExtension(GObject.GObject, Nautilus.MenuProvider):
    """Nautilus extension that adds TuxAgent context menu items"""

    def __init__(self):
        super().__init__()

    def _is_daemon_running(self) -> bool:
        """Check if TuxAgent daemon is running"""
        try:
            import dbus
            bus = dbus.SessionBus()
            bus.get_object("org.tuxagent.Assistant", "/org/tuxagent/Assistant")
            return True
        except:
            return False

    def _get_file_path(self, file_info: Nautilus.FileInfo) -> str:
        """Get the file path from a FileInfo object"""
        uri = file_info.get_uri()
        if uri.startswith("file://"):
            return unquote(uri[7:])
        return uri

    def _ask_about_file(self, menu, files):
        """Handle 'Ask TuxAgent about this file' action"""
        if not files:
            return

        file_path = self._get_file_path(files[0])
        file_name = os.path.basename(file_path)

        # Build question
        question = f"What is this file and what does it do? File: {file_path}"

        # Call TuxAgent via D-Bus
        try:
            import dbus
            bus = dbus.SessionBus()
            proxy = dbus.Interface(
                bus.get_object("org.tuxagent.Assistant", "/org/tuxagent/Assistant"),
                "org.tuxagent.Assistant"
            )

            # Show notification that we're processing
            subprocess.run([
                "notify-send",
                "TuxAgent",
                f"Analyzing {file_name}...",
                "--icon=dialog-question",
                "--expire-time=3000"
            ], capture_output=True)

            # Ask TuxAgent
            response = proxy.Ask(question)

            # Show response in a dialog or notification
            # For long responses, open the overlay
            if len(response) > 200:
                # Open overlay with the question pre-filled
                subprocess.Popen([
                    "python3", "-c",
                    f"import dbus; bus = dbus.SessionBus(); "
                    f"proxy = dbus.Interface(bus.get_object('org.tuxagent.Assistant', '/org/tuxagent/Assistant'), 'org.tuxagent.Assistant'); "
                    f"print(proxy.Ask('Tell me about this file: {file_path}'))"
                ])

                subprocess.run([
                    "notify-send",
                    "TuxAgent",
                    f"Analysis complete for {file_name}. Check the overlay for details.",
                    "--icon=dialog-information",
                    "--expire-time=5000"
                ], capture_output=True)
            else:
                # Short response, show in notification
                subprocess.run([
                    "notify-send",
                    f"TuxAgent: {file_name}",
                    response[:500],
                    "--icon=dialog-information",
                    "--expire-time=10000"
                ], capture_output=True)

        except Exception as e:
            subprocess.run([
                "notify-send",
                "TuxAgent Error",
                f"Failed to analyze file: {str(e)}",
                "--icon=dialog-error",
                "--expire-time=5000"
            ], capture_output=True)

    def _summarize_file(self, menu, files):
        """Handle 'Summarize with TuxAgent' action"""
        if not files:
            return

        file_path = self._get_file_path(files[0])
        file_name = os.path.basename(file_path)

        question = f"Please summarize the contents of this file: {file_path}"

        try:
            import dbus
            bus = dbus.SessionBus()
            proxy = dbus.Interface(
                bus.get_object("org.tuxagent.Assistant", "/org/tuxagent/Assistant"),
                "org.tuxagent.Assistant"
            )

            subprocess.run([
                "notify-send",
                "TuxAgent",
                f"Summarizing {file_name}...",
                "--icon=dialog-question",
                "--expire-time=3000"
            ], capture_output=True)

            response = proxy.Ask(question)

            subprocess.run([
                "notify-send",
                f"Summary: {file_name}",
                response[:500],
                "--icon=dialog-information",
                "--expire-time=15000"
            ], capture_output=True)

        except Exception as e:
            subprocess.run([
                "notify-send",
                "TuxAgent Error",
                str(e),
                "--icon=dialog-error"
            ], capture_output=True)

    def _explain_code(self, menu, files):
        """Handle 'Explain code with TuxAgent' action"""
        if not files:
            return

        file_path = self._get_file_path(files[0])
        file_name = os.path.basename(file_path)

        question = f"Please explain what this code does and how it works: {file_path}"

        try:
            import dbus
            bus = dbus.SessionBus()
            proxy = dbus.Interface(
                bus.get_object("org.tuxagent.Assistant", "/org/tuxagent/Assistant"),
                "org.tuxagent.Assistant"
            )

            subprocess.run([
                "notify-send",
                "TuxAgent",
                f"Analyzing code in {file_name}...",
                "--icon=dialog-question",
                "--expire-time=3000"
            ], capture_output=True)

            response = proxy.Ask(question)

            # Code explanations are usually long, show in overlay
            subprocess.run([
                "notify-send",
                f"Code Analysis: {file_name}",
                "Analysis complete. " + response[:200] + "...",
                "--icon=dialog-information",
                "--expire-time=10000"
            ], capture_output=True)

        except Exception as e:
            subprocess.run([
                "notify-send",
                "TuxAgent Error",
                str(e),
                "--icon=dialog-error"
            ], capture_output=True)

    def get_file_items(self, files):
        """Return context menu items for selected files"""
        # Only show for single file selection
        if len(files) != 1:
            return []

        file_info = files[0]

        # Skip directories
        if file_info.is_directory():
            return []

        # Check if daemon is running
        if not self._is_daemon_running():
            return []

        items = []

        # Main menu item
        main_item = Nautilus.MenuItem(
            name="TuxAgentExtension::AskAbout",
            label="Ask TuxAgent about this file",
            tip="Ask TuxAgent AI assistant about this file"
        )
        main_item.connect("activate", self._ask_about_file, files)
        items.append(main_item)

        # Check if it's a text/code file for additional options
        mime_type = file_info.get_mime_type()
        file_path = self._get_file_path(file_info)
        ext = os.path.splitext(file_path)[1].lower()

        # Text files - add summarize option
        if mime_type.startswith("text/") or ext in [".txt", ".md", ".rst", ".log", ".json", ".xml", ".yaml", ".yml"]:
            summarize_item = Nautilus.MenuItem(
                name="TuxAgentExtension::Summarize",
                label="Summarize with TuxAgent",
                tip="Get a summary of this file's contents"
            )
            summarize_item.connect("activate", self._summarize_file, files)
            items.append(summarize_item)

        # Code files - add explain option
        code_extensions = [
            ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h",
            ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
            ".sh", ".bash", ".zsh", ".ps1", ".sql", ".html", ".css", ".scss"
        ]
        if ext in code_extensions or mime_type.startswith("text/x-"):
            explain_item = Nautilus.MenuItem(
                name="TuxAgentExtension::ExplainCode",
                label="Explain code with TuxAgent",
                tip="Get an explanation of what this code does"
            )
            explain_item.connect("activate", self._explain_code, files)
            items.append(explain_item)

        return items

    def get_background_items(self, current_folder):
        """Return context menu items for folder background"""
        # Could add "Ask TuxAgent about this folder" here
        return []
