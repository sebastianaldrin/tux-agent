"""
Thread Manager - JSON-based conversation thread management for TuxAgent
Provides ChatGPT-style isolated conversations
"""
import json
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from .simple_conversation import SimpleConversation

logger = logging.getLogger(__name__)


class ThreadMetadata:
    """Metadata for a conversation thread"""

    def __init__(self, thread_id: str, title: str = "New Chat",
                 created_at: datetime = None, last_message_at: datetime = None,
                 message_count: int = 0, last_preview: str = "",
                 pinned: bool = False, thread_type: str = "chat"):
        self.thread_id = thread_id
        self.title = title
        self.created_at = created_at or datetime.now()
        self.last_message_at = last_message_at or datetime.now()
        self.message_count = message_count
        self.last_preview = last_preview
        self.pinned = pinned
        self.thread_type = thread_type

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "thread_id": self.thread_id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "last_message_at": self.last_message_at.isoformat(),
            "message_count": self.message_count,
            "last_preview": self.last_preview,
            "pinned": self.pinned,
            "thread_type": self.thread_type
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThreadMetadata':
        """Create from dictionary"""
        return cls(
            thread_id=data.get("thread_id", ""),
            title=data.get("title", "New Chat"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            last_message_at=datetime.fromisoformat(data.get("last_message_at", datetime.now().isoformat())),
            message_count=data.get("message_count", 0),
            last_preview=data.get("last_preview", ""),
            pinned=data.get("pinned", False),
            thread_type=data.get("thread_type", "chat")
        )


class ThreadManager:
    """
    JSON-based thread management system for TuxAgent
    Provides ChatGPT-style isolated conversations using SimpleConversation
    """

    def __init__(self, workspace_path: str = None):
        """Initialize thread manager with secure app data directory"""
        # Store threads in TuxAgent data directory
        self.threads_dir = Path.home() / ".local" / "share" / "tuxagent" / "conversations"

        # Ensure threads directory exists
        self.threads_dir.mkdir(parents=True, exist_ok=True)

        self.metadata_file = self.threads_dir / "metadata.json"

        # In-memory state
        self.thread_metadata: Dict[str, ThreadMetadata] = {}
        self.current_thread_id: Optional[str] = None
        self.current_conversation: Optional[SimpleConversation] = None

        # Load existing threads
        self._load_metadata()

        logger.info(f"ThreadManager initialized with {len(self.thread_metadata)} threads")

    def _load_metadata(self):
        """Load thread metadata from JSON file"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for thread_data in data.get("threads", []):
                    metadata = ThreadMetadata.from_dict(thread_data)
                    self.thread_metadata[metadata.thread_id] = metadata

                self.current_thread_id = data.get("current_thread_id")

                logger.info(f"Loaded {len(self.thread_metadata)} thread metadata entries")
            else:
                logger.info("No existing thread metadata found")

        except Exception as e:
            logger.error(f"Failed to load thread metadata: {e}")
            self.thread_metadata = {}

    def _save_metadata(self):
        """Save thread metadata to JSON file"""
        try:
            data = {
                "current_thread_id": self.current_thread_id,
                "threads": [metadata.to_dict() for metadata in self.thread_metadata.values()]
            }

            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug("Thread metadata saved successfully")

        except Exception as e:
            logger.error(f"Failed to save thread metadata: {e}")

    def create_thread(self, title: str = "New Chat") -> str:
        """Create a new thread and return its ID"""
        thread_id = f"thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Create new conversation and set as current
        self.current_conversation = SimpleConversation(session_id=thread_id)

        # Create metadata
        metadata = ThreadMetadata(
            thread_id=thread_id,
            title=title,
            created_at=datetime.now(),
            last_message_at=datetime.now()
        )
        self.thread_metadata[thread_id] = metadata

        # Switch to new thread
        self.current_thread_id = thread_id

        # Save metadata
        self._save_metadata()

        logger.info(f"Created new thread: {thread_id} - '{title}'")
        return thread_id

    def switch_thread(self, thread_id: str) -> bool:
        """Switch to a specific thread"""
        if thread_id not in self.thread_metadata:
            logger.warning(f"Thread {thread_id} not found")
            return False

        self.current_thread_id = thread_id

        # Load conversation
        self.current_conversation = self._load_thread_conversation(thread_id)

        # Update metadata
        self._save_metadata()

        logger.info(f"Switched to thread: {thread_id}")
        return True

    def _load_thread_conversation(self, thread_id: str) -> SimpleConversation:
        """Load conversation for a specific thread and return it"""
        thread_file = self.threads_dir / f"{thread_id}.json"

        try:
            if thread_file.exists():
                conversation = SimpleConversation.load_from_file(str(thread_file))
                logger.debug(f"Loaded conversation for thread {thread_id}")
                return conversation
            else:
                conversation = SimpleConversation(session_id=thread_id)
                logger.debug(f"Created new conversation for thread {thread_id}")
                return conversation

        except Exception as e:
            logger.error(f"Failed to load thread conversation {thread_id}: {e}")
            conversation = SimpleConversation(session_id=thread_id)
            return conversation

    def get_current_conversation(self) -> Optional[SimpleConversation]:
        """Get the current active conversation"""
        return self.current_conversation

    def get_current_thread_id(self) -> Optional[str]:
        """Get current thread ID"""
        return self.current_thread_id

    def get_current_thread_title(self) -> str:
        """Get current thread title"""
        if self.current_thread_id and self.current_thread_id in self.thread_metadata:
            return self.thread_metadata[self.current_thread_id].title
        return "New Chat"

    def update_thread_after_message(self, user_message: str = "", assistant_message: str = ""):
        """Update thread metadata after a message exchange"""
        if not self.current_thread_id:
            return

        metadata = self.thread_metadata.get(self.current_thread_id)
        if not metadata:
            return

        # Update metadata
        metadata.last_message_at = datetime.now()
        metadata.message_count += 1 if user_message else 0
        metadata.message_count += 1 if assistant_message else 0

        # Update preview with last user message (truncated)
        if user_message:
            metadata.last_preview = user_message[:100] + "..." if len(user_message) > 100 else user_message

        # Auto-generate title after 4th message for better context
        if metadata.title == "New Chat" and assistant_message and metadata.message_count >= 4:
            metadata.title = self._generate_thread_title(user_message or "Chat")

        # Save conversation to file
        self._save_thread_conversation()

        # Save metadata
        self._save_metadata()

    def _generate_thread_title(self, first_message: str) -> str:
        """Generate a contextual thread title from first message"""
        try:
            message = first_message.lower().strip()

            # Common Linux/Desktop task patterns
            if any(word in message for word in ['install', 'setup', 'configure']):
                return "Installation Help"
            elif any(word in message for word in ['file', 'folder', 'directory', 'find']):
                return "File Operations"
            elif any(word in message for word in ['network', 'wifi', 'internet', 'connection']):
                return "Network Help"
            elif any(word in message for word in ['permission', 'sudo', 'root', 'access']):
                return "Permissions Help"
            elif any(word in message for word in ['what', 'how', 'why', 'explain']):
                return "Question & Answer"
            elif any(word in message for word in ['error', 'problem', 'fix', 'broken']):
                return "Troubleshooting"
            elif any(word in message for word in ['screenshot', 'screen', 'window']):
                return "Screen Analysis"
            else:
                # Fallback: extract meaningful words
                skip_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
                             'for', 'of', 'with', 'by', 'can', 'you', 'i', 'me', 'my', 'please', 'help'}
                words = [word.capitalize() for word in first_message.split()[:4]
                        if word.lower() not in skip_words and len(word) > 2]

                if len(words) >= 2:
                    return " ".join(words[:3])
                elif len(words) == 1:
                    return f"{words[0]} Help"
                else:
                    return "General Help"

        except Exception as e:
            logger.warning(f"Failed to generate title: {e}")
            return "New Chat"

    def _save_thread_conversation(self):
        """Save current thread conversation to file"""
        if not self.current_thread_id or not self.current_conversation:
            return

        thread_file = self.threads_dir / f"{self.current_thread_id}.json"

        try:
            self.current_conversation.save_to_file(str(thread_file))
            logger.debug(f"Saved conversation for thread {self.current_thread_id}")
        except Exception as e:
            logger.error(f"Failed to save thread conversation {self.current_thread_id}: {e}")

    def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread and its conversation file"""
        if thread_id not in self.thread_metadata:
            return False

        try:
            # Remove metadata
            del self.thread_metadata[thread_id]

            # Delete conversation file
            thread_file = self.threads_dir / f"{thread_id}.json"
            if thread_file.exists():
                thread_file.unlink()

            # If this was the current thread, switch to another
            if self.current_thread_id == thread_id:
                if self.thread_metadata:
                    latest_thread = max(self.thread_metadata.values(),
                                      key=lambda m: m.last_message_at)
                    self.current_thread_id = latest_thread.thread_id
                    self.current_conversation = self._load_thread_conversation(self.current_thread_id)
                else:
                    self.current_thread_id = None
                    self.current_conversation = None

            # Save metadata
            self._save_metadata()

            logger.info(f"Deleted thread: {thread_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete thread {thread_id}: {e}")
            return False

    def get_thread_list(self) -> List[ThreadMetadata]:
        """Get list of all threads sorted by pinned status first, then by last message time"""
        threads = list(self.thread_metadata.values())
        threads.sort(key=lambda t: (not t.pinned, -t.last_message_at.timestamp()))
        return threads

    def rename_thread(self, thread_id: str, new_title: str) -> bool:
        """Rename a thread"""
        if thread_id not in self.thread_metadata:
            return False

        self.thread_metadata[thread_id].title = new_title
        self._save_metadata()

        logger.info(f"Renamed thread {thread_id} to '{new_title}'")
        return True

    def get_thread_stats(self) -> Dict[str, Any]:
        """Get thread manager statistics"""
        return {
            "total_threads": len(self.thread_metadata),
            "current_thread": self.current_thread_id,
            "threads_directory": str(self.threads_dir)
        }
