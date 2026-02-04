#!/usr/bin/env python3
"""
TuxAgent CLI Client
Command-line interface for interacting with TuxAgent daemon
"""
import sys
import argparse
import dbus
from typing import Optional

# D-Bus configuration
DBUS_SERVICE_NAME = "org.tuxagent.Assistant"
DBUS_OBJECT_PATH = "/org/tuxagent/Assistant"
DBUS_INTERFACE = "org.tuxagent.Assistant"


def get_tuxagent_proxy():
    """Get D-Bus proxy for TuxAgent service"""
    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object(DBUS_SERVICE_NAME, DBUS_OBJECT_PATH)
        iface = dbus.Interface(proxy, DBUS_INTERFACE)
        return iface
    except dbus.exceptions.DBusException as e:
        if "ServiceUnknown" in str(e) or "NameHasNoOwner" in str(e):
            print("Error: TuxAgent daemon is not running.")
            print("Start it with: tuxagent-daemon")
            sys.exit(1)
        raise


# D-Bus timeout for long-running operations (10 minutes)
DBUS_TIMEOUT = 600


def take_screenshot() -> Optional[str]:
    """Take a screenshot and return base64 data"""
    try:
        # Import screenshot service
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))
        from src.daemon.screenshot import take_screenshot as capture
        return capture(interactive=True)
    except (ImportError, Exception):
        # Fallback: try using gnome-screenshot
        import subprocess
        import tempfile
        import base64
        import os

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name

        try:
            result = subprocess.run(
                ["gnome-screenshot", "-f", temp_path],
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0 and os.path.exists(temp_path):
                with open(temp_path, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")
                os.unlink(temp_path)
                return data
        except:
            pass

        return None


def cmd_ask(args):
    """Handle 'ask' command"""
    question = " ".join(args.question) if isinstance(args.question, list) else args.question

    if not question:
        print("Error: Please provide a question")
        sys.exit(1)

    tuxagent = get_tuxagent_proxy()

    if args.screenshot:
        print("Taking screenshot...")
        screenshot = take_screenshot()
        if not screenshot:
            print("Error: Failed to capture screenshot")
            sys.exit(1)
        print("Analyzing screenshot...")
        response = tuxagent.AskWithScreenshot(question, screenshot, timeout=DBUS_TIMEOUT)
    else:
        print("Thinking...")
        response = tuxagent.Ask(question, timeout=DBUS_TIMEOUT)

    print()
    print(response)


def cmd_status(args):
    """Handle 'status' command"""
    tuxagent = get_tuxagent_proxy()
    status = tuxagent.GetStatus()

    print("TuxAgent Status")
    print("=" * 40)
    print(f"Running:        {status.get('running', False)}")
    print(f"Model:          {status.get('model', 'unknown')}")
    print(f"Total Requests: {status.get('total_requests', 0)}")
    print(f"Tool Calls:     {status.get('total_tool_calls', 0)}")
    print(f"Available Tools: {status.get('available_tools', 0)}")
    print(f"Threads:        {status.get('total_threads', 0)}")
    print(f"Current Thread: {status.get('current_thread', 'none')}")


def cmd_new(args):
    """Handle 'new' command - create new conversation"""
    tuxagent = get_tuxagent_proxy()
    thread_id = tuxagent.CreateThread()
    print(f"Created new conversation: {thread_id}")


def cmd_clear(args):
    """Handle 'clear' command - clear current conversation"""
    tuxagent = get_tuxagent_proxy()
    tuxagent.ClearConversation()
    print("Conversation cleared")


def cmd_threads(args):
    """Handle 'threads' command - list conversation threads"""
    tuxagent = get_tuxagent_proxy()
    threads = tuxagent.ListThreads()

    if not threads:
        print("No conversation threads")
        return

    print("Conversation Threads")
    print("=" * 40)
    for i, thread_id in enumerate(threads, 1):
        print(f"{i}. {thread_id}")


def cmd_switch(args):
    """Handle 'switch' command - switch conversation thread"""
    tuxagent = get_tuxagent_proxy()
    success = tuxagent.SwitchThread(args.thread_id)

    if success:
        print(f"Switched to thread: {args.thread_id}")
    else:
        print(f"Error: Thread not found: {args.thread_id}")
        sys.exit(1)


def cmd_extensions(args):
    """Handle 'extensions' command"""
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    from src.core.extension_manager import ExtensionManager

    manager = ExtensionManager()

    if args.ext_command == "list":
        extensions = manager.list_extensions()
        desktop = manager.detect_desktop()
        recommended = manager.get_recommended()

        print(f"TuxAgent Extensions (Desktop: {desktop})")
        print("=" * 50)
        print()

        for ext in extensions:
            status = "✓ installed" if ext.installed else "  available"
            rec = " (recommended)" if ext.name in recommended else ""
            avail = "" if ext.available else " [files missing]"

            print(f"  {status}  {ext.name}{rec}{avail}")
            print(f"           {ext.description}")
            print()

        print("Commands:")
        print("  tux extensions install <name>   Install an extension")
        print("  tux extensions remove <name>    Remove an extension")
        print("  tux extensions recommend        Show recommended for your desktop")

    elif args.ext_command == "install":
        if not args.name:
            print("Error: Please specify an extension name")
            print("Use 'tux extensions list' to see available extensions")
            sys.exit(1)

        print(f"Installing extension: {args.name}...")

        # First try without auto-installing deps
        result = manager.install(args.name, force=args.force, auto_deps=False)

        # Handle missing dependencies
        if result.get("needs_deps"):
            print()
            print("This extension requires system packages that are not installed:")
            print()
            for dep in result.get("missing_deps", []):
                cmd = result.get("install_commands", {}).get(dep, f"install {dep}")
                print(f"  • {dep}")
                print(f"    Install with: {cmd}")
            print()

            # Ask user if they want to install
            try:
                response = input("Install these dependencies now? [y/N]: ").strip().lower()
                if response in ('y', 'yes'):
                    print()
                    print("Installing dependencies (may require sudo password)...")
                    result = manager.install(args.name, force=args.force, auto_deps=True)
                else:
                    print()
                    print("Please install the dependencies manually, then run:")
                    print(f"  tux extensions install {args.name}")
                    sys.exit(0)
            except (EOFError, KeyboardInterrupt):
                print("\nCancelled.")
                sys.exit(0)

        if result["success"]:
            print(f"✓ {result['message']}")
            if result.get("warnings"):
                for warning in result["warnings"]:
                    print(f"  Warning: {warning}")
            if result.get("hints"):
                print()
                for hint in result["hints"]:
                    print(f"  → {hint}")
        else:
            print(f"✗ {result['message']}")
            sys.exit(1)

    elif args.ext_command == "remove":
        if not args.name:
            print("Error: Please specify an extension name")
            sys.exit(1)

        print(f"Removing extension: {args.name}...")
        result = manager.remove(args.name)

        if result["success"]:
            print(f"✓ {result['message']}")
        else:
            print(f"✗ {result['message']}")
            sys.exit(1)

    elif args.ext_command == "recommend":
        desktop = manager.detect_desktop()
        recommended = manager.get_recommended()

        print(f"Recommended extensions for {desktop}:")
        print()

        if recommended:
            for ext_name in recommended:
                installed = "✓" if manager.is_installed(ext_name) else " "
                extensions = manager.list_extensions()
                ext = next((e for e in extensions if e.name == ext_name), None)
                if ext:
                    print(f"  {installed} {ext_name} - {ext.description}")
            print()
            print("Install with: tux extensions install <name>")
        else:
            print("  No specific extensions recommended for your desktop.")
            print("  Use 'tux extensions list' to see all available.")

    else:
        print("Unknown extension command. Use: list, install, remove, recommend")
        sys.exit(1)


def cmd_interactive(args):
    """Handle interactive mode"""
    tuxagent = get_tuxagent_proxy()

    print("TuxAgent Interactive Mode")
    print("Type 'quit' or 'exit' to leave, '/screenshot' to include a screenshot")
    print("=" * 50)
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "/quit", "/exit"):
            print("Goodbye!")
            break

        if user_input.lower() in ("/screenshot", "/ss"):
            print("Taking screenshot... (follow the prompt)")
            screenshot = take_screenshot()
            if screenshot:
                question = input("Question about screenshot: ").strip()
                if question:
                    print("Analyzing...")
                    response = tuxagent.AskWithScreenshot(question, screenshot, timeout=DBUS_TIMEOUT)
                    print(f"\nTuxAgent: {response}\n")
            else:
                print("Screenshot failed or cancelled")
            continue

        if user_input.startswith("/screenshot ") or user_input.startswith("/ss "):
            parts = user_input.split(" ", 1)
            question = parts[1] if len(parts) > 1 else "What is on my screen?"
            print("Taking screenshot...")
            screenshot = take_screenshot()
            if screenshot:
                print("Analyzing...")
                response = tuxagent.AskWithScreenshot(question, screenshot, timeout=DBUS_TIMEOUT)
                print(f"\nTuxAgent: {response}\n")
            else:
                print("Screenshot failed or cancelled")
            continue

        if user_input.startswith("/new"):
            thread_id = tuxagent.CreateThread(timeout=DBUS_TIMEOUT)
            print(f"Created new conversation: {thread_id}\n")
            continue

        if user_input.startswith("/clear"):
            tuxagent.ClearConversation(timeout=DBUS_TIMEOUT)
            print("Conversation cleared\n")
            continue

        print("Thinking...")
        response = tuxagent.Ask(user_input, timeout=DBUS_TIMEOUT)
        print(f"\nTuxAgent: {response}\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="TuxAgent - Linux AI Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  tux ask "How do I install Chrome?"
  tux ask --screenshot "What application is this?"
  tux status
  tux interactive

Extensions:
  tux extensions list              List available extensions
  tux extensions install nautilus  Install Nautilus integration
  tux extensions remove nautilus   Remove an extension
  tux extensions recommend         Show recommended for your desktop

For more help: tux <command> --help
"""
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ask command
    ask_parser = subparsers.add_parser("ask", help="Ask TuxAgent a question")
    ask_parser.add_argument("question", nargs="+", help="The question to ask")
    ask_parser.add_argument(
        "-s", "--screenshot",
        action="store_true",
        help="Include a screenshot with your question"
    )
    ask_parser.set_defaults(func=cmd_ask)

    # status command
    status_parser = subparsers.add_parser("status", help="Show TuxAgent status")
    status_parser.set_defaults(func=cmd_status)

    # new command
    new_parser = subparsers.add_parser("new", help="Create new conversation")
    new_parser.set_defaults(func=cmd_new)

    # clear command
    clear_parser = subparsers.add_parser("clear", help="Clear current conversation")
    clear_parser.set_defaults(func=cmd_clear)

    # threads command
    threads_parser = subparsers.add_parser("threads", help="List conversation threads")
    threads_parser.set_defaults(func=cmd_threads)

    # switch command
    switch_parser = subparsers.add_parser("switch", help="Switch conversation thread")
    switch_parser.add_argument("thread_id", help="Thread ID to switch to")
    switch_parser.set_defaults(func=cmd_switch)

    # interactive command
    interactive_parser = subparsers.add_parser(
        "interactive", aliases=["i", "chat"],
        help="Start interactive mode"
    )
    interactive_parser.set_defaults(func=cmd_interactive)

    # extensions command
    ext_parser = subparsers.add_parser(
        "extensions", aliases=["ext"],
        help="Manage TuxAgent extensions"
    )
    ext_parser.add_argument(
        "ext_command",
        choices=["list", "install", "remove", "recommend"],
        help="Extension command"
    )
    ext_parser.add_argument(
        "name",
        nargs="?",
        help="Extension name (for install/remove)"
    )
    ext_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Force reinstall if already installed"
    )
    ext_parser.set_defaults(func=cmd_extensions)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    # Execute command
    args.func(args)


if __name__ == "__main__":
    main()
