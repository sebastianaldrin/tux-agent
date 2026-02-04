"""
D-Bus Service for TuxAgent
Provides IPC interface for the TuxAgent daemon
"""
import logging
import threading
from typing import Dict, Any, Optional
from pathlib import Path

# GLib/D-Bus imports
from gi.repository import GLib
import dbus
import dbus.service
import dbus.mainloop.glib

# Add parent paths for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.config import TuxAgentConfig
from src.daemon.kimi_executor import KimiExecutor
from src.core.thread_manager import ThreadManager
from src.core.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)

# D-Bus configuration
DBUS_SERVICE_NAME = TuxAgentConfig.DBUS_SERVICE_NAME
DBUS_OBJECT_PATH = TuxAgentConfig.DBUS_OBJECT_PATH
DBUS_INTERFACE = TuxAgentConfig.DBUS_INTERFACE


class TuxAgentDBusService(dbus.service.Object):
    """
    D-Bus service providing TuxAgent functionality

    Methods:
        Ask(text) -> response
        AskWithScreenshot(text) -> response
        GetStatus() -> status dict

    Signals:
        ResponseChunk(chunk) - Emitted during streaming responses
        ToolExecuting(tool_name) - Emitted when a tool starts executing
    """

    def __init__(self, bus_name: dbus.service.BusName):
        """Initialize the D-Bus service"""
        super().__init__(bus_name, DBUS_OBJECT_PATH)

        # Ensure directories exist
        TuxAgentConfig.ensure_directories()

        # Initialize components
        self.tool_executor = ToolExecutor()
        self.thread_manager = ThreadManager()
        self.kimi_executor = KimiExecutor(self.tool_executor)

        # Create or get current thread
        if not self.thread_manager.get_current_thread_id():
            self.thread_manager.create_thread("TuxAgent Session")

        # Set conversation in executor
        conversation = self.thread_manager.get_current_conversation()
        if conversation:
            self.kimi_executor.set_conversation(conversation)

        # Screenshot data (set externally before AskWithScreenshot)
        self._pending_screenshot: Optional[str] = None

        # Lock for thread safety
        self._lock = threading.Lock()

        logger.info(f"TuxAgent D-Bus service initialized at {DBUS_OBJECT_PATH}")

    def _progress_callback(self, progress_type: str, detail: str):
        """Callback for progress updates during execution"""
        if progress_type == "tool_executing":
            self.ToolExecuting(detail)
        elif progress_type == "thinking":
            self.ResponseChunk(f"[{detail}]")

    @dbus.service.method(DBUS_INTERFACE, in_signature='s', out_signature='s')
    def Ask(self, question: str) -> str:
        """
        Ask TuxAgent a question (text only)

        Args:
            question: The user's question

        Returns:
            The assistant's response
        """
        logger.info(f"Ask called with: {question[:100]}...")

        with self._lock:
            try:
                response = self.kimi_executor.execute(
                    question,
                    progress_callback=self._progress_callback
                )

                # Update thread after message
                self.thread_manager.update_thread_after_message(
                    user_message=question,
                    assistant_message=response
                )

                return response

            except Exception as e:
                logger.error(f"Error in Ask: {e}")
                return f"Error: {str(e)}"

    @dbus.service.method(DBUS_INTERFACE, in_signature='ss', out_signature='s')
    def AskWithScreenshot(self, question: str, screenshot_base64: str) -> str:
        """
        Ask TuxAgent a question with a screenshot

        Args:
            question: The user's question
            screenshot_base64: Base64-encoded PNG screenshot

        Returns:
            The assistant's response
        """
        logger.info(f"AskWithScreenshot called with: {question[:100]}...")

        with self._lock:
            try:
                response = self.kimi_executor.execute(
                    question,
                    images=[screenshot_base64],
                    progress_callback=self._progress_callback
                )

                # Update thread after message
                self.thread_manager.update_thread_after_message(
                    user_message=question,
                    assistant_message=response
                )

                return response

            except Exception as e:
                logger.error(f"Error in AskWithScreenshot: {e}")
                return f"Error: {str(e)}"

    @dbus.service.method(DBUS_INTERFACE, in_signature='', out_signature='a{sv}')
    def GetStatus(self) -> Dict[str, Any]:
        """
        Get TuxAgent daemon status

        Returns:
            Dictionary with status information
        """
        stats = self.kimi_executor.get_stats()
        thread_stats = self.thread_manager.get_thread_stats()

        return {
            "running": dbus.Boolean(True),
            "model": dbus.String(stats.get("model", "unknown")),
            "total_requests": dbus.Int32(stats.get("total_requests", 0)),
            "total_tool_calls": dbus.Int32(stats.get("total_tool_calls", 0)),
            "available_tools": dbus.Int32(stats.get("available_tools", 0)),
            "total_threads": dbus.Int32(thread_stats.get("total_threads", 0)),
            "current_thread": dbus.String(thread_stats.get("current_thread", "") or "")
        }

    @dbus.service.method(DBUS_INTERFACE, in_signature='', out_signature='s')
    def CreateThread(self) -> str:
        """Create a new conversation thread"""
        thread_id = self.thread_manager.create_thread()
        conversation = self.thread_manager.get_current_conversation()
        if conversation:
            self.kimi_executor.set_conversation(conversation)
        return thread_id

    @dbus.service.method(DBUS_INTERFACE, in_signature='s', out_signature='b')
    def SwitchThread(self, thread_id: str) -> bool:
        """Switch to a different conversation thread"""
        success = self.thread_manager.switch_thread(thread_id)
        if success:
            conversation = self.thread_manager.get_current_conversation()
            if conversation:
                self.kimi_executor.set_conversation(conversation)
        return success

    @dbus.service.method(DBUS_INTERFACE, in_signature='', out_signature='as')
    def ListThreads(self) -> list:
        """List all conversation threads"""
        threads = self.thread_manager.get_thread_list()
        return [t.thread_id for t in threads]

    @dbus.service.method(DBUS_INTERFACE, in_signature='', out_signature='')
    def ClearConversation(self):
        """Clear the current conversation"""
        conversation = self.thread_manager.get_current_conversation()
        if conversation:
            conversation.clear_conversation()

    @dbus.service.method(DBUS_INTERFACE, in_signature='', out_signature='')
    def RefreshProvider(self):
        """Refresh the API provider after settings change"""
        logger.info("Refreshing API provider...")
        self.kimi_executor.refresh_provider()

    @dbus.service.method(DBUS_INTERFACE, in_signature='', out_signature='a{sv}')
    def GetUsageStats(self) -> Dict[str, Any]:
        """
        Get usage statistics for the current tier

        Returns:
            Dictionary with usage information
        """
        return {
            "api_mode": dbus.String(TuxAgentConfig.get_api_mode()),
            "usage_count": dbus.Int32(TuxAgentConfig.get_usage_count()),
            "usage_limit": dbus.Int32(TuxAgentConfig.get_usage_limit()),
            "usage_remaining": dbus.Int32(TuxAgentConfig.get_usage_remaining()),
            "show_warning": dbus.Boolean(TuxAgentConfig.should_show_usage_warning()),
        }

    # Signals
    @dbus.service.signal(DBUS_INTERFACE, signature='s')
    def ResponseChunk(self, chunk: str):
        """Signal emitted when a response chunk is available"""
        pass

    @dbus.service.signal(DBUS_INTERFACE, signature='s')
    def ToolExecuting(self, tool_name: str):
        """Signal emitted when a tool starts executing"""
        pass


class TuxAgentDaemon:
    """
    Main daemon class that manages the D-Bus service
    """

    def __init__(self):
        """Initialize the daemon"""
        self.mainloop = None
        self.service = None

    def run(self):
        """Start the daemon"""
        # Initialize D-Bus main loop
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        # Get session bus
        bus = dbus.SessionBus()

        # Request service name
        try:
            bus_name = dbus.service.BusName(
                DBUS_SERVICE_NAME,
                bus=bus,
                do_not_queue=True
            )
        except dbus.exceptions.NameExistsException:
            logger.error(f"Service {DBUS_SERVICE_NAME} is already running")
            return False

        # Create service
        self.service = TuxAgentDBusService(bus_name)

        # Create main loop
        self.mainloop = GLib.MainLoop()

        logger.info(f"TuxAgent daemon started on {DBUS_SERVICE_NAME}")

        try:
            self.mainloop.run()
        except KeyboardInterrupt:
            logger.info("Daemon stopped by user")
        finally:
            self.stop()

        return True

    def stop(self):
        """Stop the daemon"""
        if self.mainloop:
            self.mainloop.quit()
        logger.info("TuxAgent daemon stopped")


def main():
    """Entry point for the daemon"""
    import argparse

    parser = argparse.ArgumentParser(description="TuxAgent D-Bus Daemon")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run daemon
    daemon = TuxAgentDaemon()
    daemon.run()


if __name__ == "__main__":
    main()
