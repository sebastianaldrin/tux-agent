"""
Custom Widgets for TuxAgent UI
Chat bubbles, input field, and other UI components
"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Pango, Gdk
import logging

logger = logging.getLogger(__name__)


class MessageBubble(Gtk.Box):
    """A chat message bubble widget with optional image/file attachments"""

    def __init__(self, message: str, is_user: bool = False,
                 screenshot_data: str = None, file_name: str = None,
                 file_path: str = None, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)

        self.is_user = is_user
        self._screenshot_data = screenshot_data

        # Create the bubble frame
        frame = Gtk.Frame()
        frame.add_css_class("message-bubble")
        frame.add_css_class("user-message" if is_user else "assistant-message")

        # Content box inside frame (vertical layout for attachments + text)
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        # Add screenshot thumbnail if present
        if screenshot_data:
            self._add_screenshot_thumbnail(content_box, screenshot_data)

        # Add file attachment indicator if present
        if file_name:
            self._add_file_indicator(content_box, file_name, file_path)

        # Create label with markdown-like formatting
        self.label = Gtk.Label()
        self.label.set_markup(self._format_message(message))
        self.label.set_wrap(True)
        self.label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.label.set_xalign(0)
        self.label.set_selectable(True)
        # Only constrain width if no screenshot (screenshot provides min width)
        if not screenshot_data:
            self.label.set_max_width_chars(60)
        content_box.append(self.label)

        frame.set_child(content_box)

        # Alignment - don't constrain width too much when there's a screenshot
        if is_user:
            self.set_halign(Gtk.Align.END)
            if not screenshot_data:
                frame.set_margin_start(50)
        else:
            self.set_halign(Gtk.Align.START)
            if not screenshot_data:
                frame.set_margin_end(50)

        self.append(frame)

    def _add_screenshot_thumbnail(self, container: Gtk.Box, base64_data: str):
        """Add a clickable screenshot thumbnail to the message"""
        import base64
        from gi.repository import GdkPixbuf

        try:
            image_bytes = base64.b64decode(base64_data)
            loader = GdkPixbuf.PixbufLoader()
            loader.write(image_bytes)
            loader.close()
            pixbuf = loader.get_pixbuf()

            # Scale to thumbnail (max 250px wide, maintain aspect ratio)
            width = pixbuf.get_width()
            height = pixbuf.get_height()
            max_width = 250
            max_height = 180

            # Scale by width first
            if width > max_width:
                scale = max_width / width
                width = int(width * scale)
                height = int(height * scale)

            # Then check height
            if height > max_height:
                scale = max_height / height
                width = int(width * scale)
                height = int(height * scale)

            pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)

            # Create picture widget with fixed size
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            picture = Gtk.Picture()
            picture.set_paintable(texture)
            picture.set_size_request(width, height)
            picture.add_css_class("message-screenshot")

            # Wrap in a button for click-to-expand
            btn = Gtk.Button()
            btn.set_child(picture)
            btn.add_css_class("flat")
            btn.add_css_class("screenshot-button")
            btn.set_tooltip_text("Click to view full size")
            btn.connect("clicked", self._on_screenshot_clicked)

            container.append(btn)

        except Exception as e:
            # Fallback: show icon if thumbnail fails
            logger.error(f"Failed to create screenshot thumbnail: {e}")
            fallback = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            icon = Gtk.Image.new_from_icon_name("camera-photo-symbolic")
            fallback.append(icon)
            label = Gtk.Label(label="Screenshot attached")
            label.add_css_class("dim-label")
            fallback.append(label)
            container.append(fallback)

    def _add_file_indicator(self, container: Gtk.Box, file_name: str, file_path: str = None):
        """Add a clickable file attachment indicator"""
        # Store file path for click handler
        self._attached_file_path = file_path

        # Wrap in button for click-to-open
        btn = Gtk.Button()
        btn.add_css_class("flat")
        btn.add_css_class("file-button")
        btn.set_tooltip_text(f"Click to open: {file_path or file_name}")
        btn.connect("clicked", self._on_file_clicked)

        file_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        file_box.add_css_class("file-indicator")

        # Choose icon based on file type
        icon_name = self._get_file_icon(file_name)
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(16)
        file_box.append(icon)

        label = Gtk.Label(label=file_name)
        label.add_css_class("caption")
        label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        label.set_max_width_chars(30)
        file_box.append(label)

        # Add open icon hint
        open_icon = Gtk.Image.new_from_icon_name("external-link-symbolic")
        open_icon.set_pixel_size(12)
        open_icon.add_css_class("dim-label")
        file_box.append(open_icon)

        btn.set_child(file_box)
        container.append(btn)

    def _get_file_icon(self, file_name: str) -> str:
        """Get appropriate icon for file type"""
        import os
        _, ext = os.path.splitext(file_name.lower())

        icon_map = {
            '.py': 'text-x-script-symbolic',
            '.js': 'text-x-script-symbolic',
            '.ts': 'text-x-script-symbolic',
            '.sh': 'text-x-script-symbolic',
            '.pdf': 'x-office-document-symbolic',
            '.doc': 'x-office-document-symbolic',
            '.docx': 'x-office-document-symbolic',
            '.txt': 'text-x-generic-symbolic',
            '.md': 'text-x-generic-symbolic',
            '.json': 'text-x-generic-symbolic',
            '.xml': 'text-x-generic-symbolic',
            '.html': 'text-html-symbolic',
            '.png': 'image-x-generic-symbolic',
            '.jpg': 'image-x-generic-symbolic',
            '.jpeg': 'image-x-generic-symbolic',
            '.gif': 'image-x-generic-symbolic',
            '.svg': 'image-x-generic-symbolic',
            '.mp3': 'audio-x-generic-symbolic',
            '.wav': 'audio-x-generic-symbolic',
            '.mp4': 'video-x-generic-symbolic',
            '.mkv': 'video-x-generic-symbolic',
            '.zip': 'package-x-generic-symbolic',
            '.tar': 'package-x-generic-symbolic',
            '.gz': 'package-x-generic-symbolic',
        }
        return icon_map.get(ext, 'text-x-generic-symbolic')

    def _on_file_clicked(self, button):
        """Open the attached file with default application"""
        if not hasattr(self, '_attached_file_path') or not self._attached_file_path:
            return

        import subprocess
        import os

        file_path = self._attached_file_path

        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return

        try:
            # Use xdg-open to open with default application
            subprocess.Popen(['xdg-open', file_path], start_new_session=True)
        except Exception as e:
            logger.error(f"Failed to open file: {e}")

    def _on_screenshot_clicked(self, button):
        """Show full-size screenshot in a dialog"""
        if not self._screenshot_data:
            return

        import base64
        from gi.repository import GdkPixbuf

        try:
            # Create dialog
            dialog = Adw.Window()
            dialog.set_title("Screenshot")
            dialog.set_default_size(800, 600)
            dialog.set_modal(True)

            # Find parent window
            parent = self.get_root()
            if parent:
                dialog.set_transient_for(parent)

            # Main box
            main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

            # Header
            header = Adw.HeaderBar()
            header.set_show_end_title_buttons(True)
            main_box.append(header)

            # Scrollable image
            scroll = Gtk.ScrolledWindow()
            scroll.set_vexpand(True)
            scroll.set_hexpand(True)

            # Load full-size image
            image_bytes = base64.b64decode(self._screenshot_data)
            loader = GdkPixbuf.PixbufLoader()
            loader.write(image_bytes)
            loader.close()
            pixbuf = loader.get_pixbuf()

            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            picture = Gtk.Picture()
            picture.set_paintable(texture)
            picture.set_can_shrink(True)

            scroll.set_child(picture)
            main_box.append(scroll)

            dialog.set_content(main_box)
            dialog.present()

        except Exception as e:
            logger.error(f"Failed to show screenshot: {e}")

    def _format_message(self, message: str) -> str:
        """Format message with markdown support for Pango markup"""
        import re

        # Escape existing markup first
        message = GLib.markup_escape_text(message)

        # Handle fenced code blocks FIRST (before line processing)
        # ```language\ncode\n``` → monospace with visual separator
        # Use a placeholder to protect code content from further formatting
        code_blocks = []

        def save_code_block(match):
            lang = match.group(1) or ''
            code = match.group(2)
            # Store the formatted block and return a placeholder
            if lang:
                formatted = f'\n<span foreground="#888888">─── {lang} ───</span>\n<tt>{code}</tt>\n<span foreground="#888888">───────────</span>\n'
            else:
                formatted = f'\n<tt>{code}</tt>\n'
            code_blocks.append(formatted)
            return f'\x00CODEBLOCK{len(code_blocks) - 1}\x00'

        message = re.sub(r'```(\w*)\n(.*?)```', save_code_block, message, flags=re.DOTALL)

        # Process line by line for headers and lists
        lines = message.split('\n')
        formatted_lines = []

        for line in lines:
            # Headers: ## text → large bold, ### text → bold
            if line.startswith('### '):
                line = f'<b>{line[4:]}</b>'
            elif line.startswith('## '):
                line = f'<span size="large"><b>{line[3:]}</b></span>'
            elif line.startswith('# '):
                line = f'<span size="x-large"><b>{line[2:]}</b></span>'
            # List items: - item or * item → bullet
            elif re.match(r'^[\-\*] ', line):
                line = f'  • {line[2:]}'
            # Numbered lists: 1. item
            elif re.match(r'^\d+\. ', line):
                line = f'  {line}'
            # Horizontal rule: ---
            elif line.strip() == '---':
                line = '─' * 40

            formatted_lines.append(line)

        message = '\n'.join(formatted_lines)

        # Inline formatting (order matters - do bold before italic)
        # Bold: **text** or __text__
        message = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', message)
        message = re.sub(r'__(.+?)__', r'<b>\1</b>', message)

        # Italic: *text* or _text_ (but not inside words)
        message = re.sub(r'(?<!\w)\*([^*]+?)\*(?!\w)', r'<i>\1</i>', message)
        message = re.sub(r'(?<!\w)_([^_]+?)_(?!\w)', r'<i>\1</i>', message)

        # Inline code: `text` → monospace
        message = re.sub(r'`([^`]+?)`', r'<tt>\1</tt>', message)

        # Restore code blocks (protected from formatting above)
        for i, block in enumerate(code_blocks):
            message = message.replace(f'\x00CODEBLOCK{i}\x00', block)

        return message

    def update_message(self, message: str):
        """Update the message content"""
        self.label.set_markup(self._format_message(message))


class ThinkingIndicator(Gtk.Box):
    """Animated thinking indicator"""

    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, **kwargs)

        self.add_css_class("thinking-indicator")
        self.set_halign(Gtk.Align.START)

        # Spinner
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(16, 16)
        self.append(self.spinner)

        # Label
        self.label = Gtk.Label(label="Thinking...")
        self.label.add_css_class("dim-label")
        self.append(self.label)

    def start(self, message: str = "Thinking..."):
        """Start the indicator"""
        self.label.set_text(message)
        self.spinner.start()
        self.set_visible(True)

    def stop(self):
        """Stop the indicator"""
        self.spinner.stop()
        self.set_visible(False)

    def set_message(self, message: str):
        """Update the status message"""
        self.label.set_text(message)


class ToolExecutionCard(Gtk.Box):
    """Card showing tool execution status"""

    def __init__(self, tool_name: str, **kwargs):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, **kwargs)

        self.add_css_class("tool-card")
        self.set_halign(Gtk.Align.START)

        # Icon
        icon = Gtk.Image.new_from_icon_name("system-run-symbolic")
        self.append(icon)

        # Tool name
        label = Gtk.Label(label=f"Running: {tool_name}")
        label.add_css_class("caption")
        self.append(label)

        # Spinner
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(12, 12)
        self.spinner.start()
        self.append(self.spinner)

    def mark_complete(self, success: bool = True):
        """Mark tool as complete"""
        self.spinner.stop()
        self.remove(self.spinner)

        # Add status icon
        icon_name = "emblem-ok-symbolic" if success else "dialog-error-symbolic"
        icon = Gtk.Image.new_from_icon_name(icon_name)
        self.append(icon)


class ChatInput(Gtk.Box):
    """Chat input widget with send button and screenshot option"""

    def __init__(self, on_send=None, on_screenshot=None, **kwargs):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, **kwargs)

        self.add_css_class("chat-input")
        self.on_send = on_send
        self.on_screenshot = on_screenshot

        # Screenshot button
        screenshot_btn = Gtk.Button()
        screenshot_btn.set_icon_name("camera-photo-symbolic")
        screenshot_btn.set_tooltip_text("Attach screenshot")
        screenshot_btn.add_css_class("flat")
        screenshot_btn.connect("clicked", self._on_screenshot_clicked)
        self.append(screenshot_btn)

        # Text entry
        self.entry = Gtk.Entry()
        self.entry.set_hexpand(True)
        self.entry.set_placeholder_text("Ask anything...")
        self.entry.connect("activate", self._on_entry_activate)
        self.append(self.entry)

        # Send button
        send_btn = Gtk.Button()
        send_btn.set_icon_name("paper-plane-symbolic")
        send_btn.set_tooltip_text("Send (Enter)")
        send_btn.add_css_class("suggested-action")
        send_btn.connect("clicked", self._on_send_clicked)
        self.append(send_btn)

    def _on_entry_activate(self, entry):
        """Handle Enter key in entry"""
        self._send_message()

    def _on_send_clicked(self, button):
        """Handle send button click"""
        self._send_message()

    def _send_message(self):
        """Send the message"""
        text = self.entry.get_text().strip()
        if text and self.on_send:
            self.on_send(text)
            self.entry.set_text("")

    def _on_screenshot_clicked(self, button):
        """Handle screenshot button click"""
        if self.on_screenshot:
            self.on_screenshot()

    def get_text(self) -> str:
        """Get current input text"""
        return self.entry.get_text().strip()

    def set_text(self, text: str):
        """Set input text"""
        self.entry.set_text(text)

    def focus(self):
        """Focus the input"""
        self.entry.grab_focus()

    def set_sensitive(self, sensitive: bool):
        """Enable/disable input"""
        self.entry.set_sensitive(sensitive)


class ScreenshotPreview(Gtk.Box):
    """Widget to preview attached screenshot"""

    def __init__(self, on_remove=None, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4, **kwargs)

        self.add_css_class("screenshot-preview")
        self.on_remove = on_remove
        self._screenshot_data = None

        # Header with remove button
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        label = Gtk.Label(label="Screenshot attached")
        label.add_css_class("caption")
        header.append(label)

        remove_btn = Gtk.Button()
        remove_btn.set_icon_name("window-close-symbolic")
        remove_btn.add_css_class("flat")
        remove_btn.add_css_class("circular")
        remove_btn.connect("clicked", self._on_remove_clicked)
        header.append(remove_btn)

        self.append(header)

        # Thumbnail
        self.thumbnail = Gtk.Picture()
        self.thumbnail.set_size_request(100, 75)
        self.thumbnail.add_css_class("screenshot-thumbnail")
        self.append(self.thumbnail)

        self.set_visible(False)

    def set_screenshot(self, base64_data: str):
        """Set screenshot from base64 data"""
        import base64
        from gi.repository import GdkPixbuf, Gdk

        self._screenshot_data = base64_data

        # Create thumbnail from base64 data
        try:
            image_bytes = base64.b64decode(base64_data)
            loader = GdkPixbuf.PixbufLoader()
            loader.write(image_bytes)
            loader.close()
            pixbuf = loader.get_pixbuf()

            # Scale to thumbnail size (max 150px wide, maintain aspect ratio)
            width = pixbuf.get_width()
            height = pixbuf.get_height()
            max_width = 150
            if width > max_width:
                scale = max_width / width
                new_width = int(width * scale)
                new_height = int(height * scale)
                pixbuf = pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)

            # Convert to texture and set on picture
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            self.thumbnail.set_paintable(texture)
            self.thumbnail.set_size_request(-1, -1)  # Reset to natural size
        except Exception as e:
            logger.error(f"Failed to create screenshot thumbnail: {e}")

        self.set_visible(True)

    def get_screenshot(self) -> str:
        """Get screenshot base64 data"""
        return self._screenshot_data

    def clear(self):
        """Clear screenshot"""
        self._screenshot_data = None
        self.thumbnail.set_paintable(None)
        self.set_visible(False)

    def _on_remove_clicked(self, button):
        """Handle remove button click"""
        self.clear()
        if self.on_remove:
            self.on_remove()


class FileAttachmentPreview(Gtk.Box):
    """Widget to preview attached file"""

    def __init__(self, on_remove=None, **kwargs):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, **kwargs)

        self.add_css_class("file-attachment")
        self.on_remove = on_remove
        self._file_path = None
        self._file_content = None

        # File icon
        self.icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic")
        self.icon.set_pixel_size(24)
        self.append(self.icon)

        # File info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)

        self.filename_label = Gtk.Label(label="No file")
        self.filename_label.set_xalign(0)
        self.filename_label.add_css_class("caption")
        self.filename_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        info_box.append(self.filename_label)

        self.size_label = Gtk.Label(label="")
        self.size_label.set_xalign(0)
        self.size_label.add_css_class("dim-label")
        self.size_label.add_css_class("caption")
        info_box.append(self.size_label)

        self.append(info_box)

        # Remove button
        remove_btn = Gtk.Button()
        remove_btn.set_icon_name("window-close-symbolic")
        remove_btn.add_css_class("flat")
        remove_btn.add_css_class("circular")
        remove_btn.connect("clicked", self._on_remove_clicked)
        self.append(remove_btn)

        self.set_visible(False)

    def set_file(self, file_path: str):
        """Attach a file"""
        import os

        self._file_path = file_path
        filename = os.path.basename(file_path)
        self.filename_label.set_text(filename)

        # Get file size
        try:
            size = os.path.getsize(file_path)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    self.size_label.set_text(f"{size:.1f} {unit}")
                    break
                size /= 1024
        except:
            self.size_label.set_text("")

        # Set appropriate icon based on file type
        _, ext = os.path.splitext(file_path.lower())
        if ext in ['.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.rs', '.go', '.rb', '.php', '.sh']:
            self.icon.set_from_icon_name("text-x-script-symbolic")
        elif ext in ['.txt', '.md', '.rst', '.log']:
            self.icon.set_from_icon_name("text-x-generic-symbolic")
        elif ext in ['.pdf']:
            self.icon.set_from_icon_name("x-office-document-symbolic")
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']:
            self.icon.set_from_icon_name("image-x-generic-symbolic")
        elif ext in ['.mp3', '.wav', '.flac', '.ogg']:
            self.icon.set_from_icon_name("audio-x-generic-symbolic")
        elif ext in ['.mp4', '.mkv', '.avi', '.mov', '.webm']:
            self.icon.set_from_icon_name("video-x-generic-symbolic")
        elif ext in ['.zip', '.tar', '.gz', '.7z', '.rar']:
            self.icon.set_from_icon_name("package-x-generic-symbolic")
        elif ext in ['.json', '.yaml', '.yml', '.toml', '.ini', '.conf']:
            self.icon.set_from_icon_name("text-x-generic-symbolic")
        else:
            self.icon.set_from_icon_name("text-x-generic-symbolic")

        # Read file content for text files
        self._file_content = None
        if ext in ['.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.rs', '.go', '.rb', '.php',
                   '.sh', '.bash', '.txt', '.md', '.rst', '.log', '.json', '.yaml', '.yml',
                   '.toml', '.ini', '.conf', '.cfg', '.xml', '.html', '.css']:
            try:
                with open(file_path, 'r', errors='ignore') as f:
                    self._file_content = f.read(50000)  # Limit to 50KB
                    if len(self._file_content) >= 50000:
                        self._file_content += "\n\n... (truncated - use read_file tool for full content)"
            except:
                pass

        self.set_visible(True)

    def get_file_path(self) -> str:
        """Get attached file path"""
        return self._file_path

    def get_file_content(self) -> str:
        """Get file content (for text files)"""
        return self._file_content

    def get_context_string(self) -> str:
        """Get context string to prepend to user's question"""
        if not self._file_path:
            return ""

        import os
        filename = os.path.basename(self._file_path)

        context = f"[Attached file: {filename}]\n"
        context += f"Path: {self._file_path}\n"

        if self._file_content:
            context += f"\nFile content:\n```\n{self._file_content}\n```\n\n"
        else:
            context += f"\n(Use your read_file tool to read this file's contents)\n\n"

        return context

    def clear(self):
        """Clear attached file"""
        self._file_path = None
        self._file_content = None
        self.set_visible(False)

    def _on_remove_clicked(self, button):
        """Handle remove button click"""
        self.clear()
        if self.on_remove:
            self.on_remove()
