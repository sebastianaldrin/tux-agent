"""
Simple Conversation System for TuxAgent
Manages conversation history with embedded tool results
"""
import json
import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """Individual message in conversation"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    # Support for multimodal messages (images)
    images: Optional[List[str]] = None  # Base64-encoded images

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {}
        }
        if self.images:
            data["images"] = self.images
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """Create from dictionary"""
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            metadata=data.get("metadata", {}),
            images=data.get("images")
        )


@dataclass
class ToolExecution:
    """Tool execution embedded in conversation"""
    tool_name: str
    input_args: Dict[str, Any]
    result: Dict[str, Any]
    success: bool
    timestamp: datetime
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "tool_name": self.tool_name,
            "input_args": self.input_args,
            "result": self.result,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "execution_time": self.execution_time
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolExecution':
        """Create from dictionary"""
        return cls(
            tool_name=data.get("tool_name", "unknown"),
            input_args=data.get("input_args", {}),
            result=data.get("result", {}),
            success=data.get("success", False),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            execution_time=data.get("execution_time", 0.0)
        )


class SimpleConversation:
    """
    Conversation management for TuxAgent
    Full conversation history with embedded tool results and multimodal support
    """

    def __init__(self, session_id: Optional[str] = None):
        """Initialize conversation"""
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        self.messages: List[ConversationMessage] = []
        self.tool_executions: List[ToolExecution] = []
        self.created_at = datetime.now()

        logger.info(f"Created new conversation: {self.session_id}")

    def add_user_message(self, content: str, images: Optional[List[str]] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add user message to conversation, optionally with images"""
        message = ConversationMessage(
            role="user",
            content=content,
            timestamp=datetime.now(),
            metadata=metadata,
            images=images
        )

        self.messages.append(message)
        logger.debug(f"Added user message: {content[:100]}...")

    def add_assistant_message(self, content: str, tool_results: Optional[List[ToolExecution]] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add assistant message with optional tool results"""
        # Add tool executions first
        if tool_results:
            for tool_exec in tool_results:
                self.tool_executions.append(tool_exec)

        # Add assistant message
        message_metadata = metadata or {}
        if tool_results:
            message_metadata["tool_executions"] = [tool.to_dict() for tool in tool_results]
            message_metadata["tools_used"] = len(tool_results)

        message = ConversationMessage(
            role="assistant",
            content=content,
            timestamp=datetime.now(),
            metadata=message_metadata
        )

        self.messages.append(message)
        logger.debug(f"Added assistant message with {len(tool_results) if tool_results else 0} tools")

    def add_tool_execution(self, tool_name: str, input_args: Dict[str, Any],
                          result: Dict[str, Any], success: bool = True,
                          execution_time: float = 0.0) -> ToolExecution:
        """Add individual tool execution"""
        tool_exec = ToolExecution(
            tool_name=tool_name,
            input_args=input_args,
            result=result,
            success=success,
            timestamp=datetime.now(),
            execution_time=execution_time
        )

        self.tool_executions.append(tool_exec)
        logger.debug(f"Added tool execution: {tool_name}")
        return tool_exec

    def get_messages_for_api(self) -> List[Dict[str, Any]]:
        """Get messages formatted for OpenAI-compatible API"""
        api_messages = []

        for msg in self.messages:
            if msg.images:
                # Multimodal message with images
                content = [{"type": "text", "text": msg.content}]
                for img_base64 in msg.images:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_base64}"
                        }
                    })
                api_messages.append({"role": msg.role, "content": content})
            else:
                # Text-only message
                api_messages.append({"role": msg.role, "content": msg.content})

        return api_messages

    def get_recent_messages(self, limit: int = 10) -> List[ConversationMessage]:
        """Get recent messages"""
        return self.messages[-limit:] if self.messages else []

    def get_recent_tools(self, limit: int = 5) -> List[ToolExecution]:
        """Get recent tool executions"""
        return self.tool_executions[-limit:] if self.tool_executions else []

    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "total_messages": len(self.messages),
            "user_messages": len([m for m in self.messages if m.role == "user"]),
            "assistant_messages": len([m for m in self.messages if m.role == "assistant"]),
            "tool_executions": len(self.tool_executions),
            "successful_tools": len([t for t in self.tool_executions if t.success]),
            "failed_tools": len([t for t in self.tool_executions if not t.success]),
            "unique_tools": len(set(t.tool_name for t in self.tool_executions))
        }

    def clear_conversation(self) -> None:
        """Clear conversation history"""
        self.messages.clear()
        self.tool_executions.clear()
        logger.info(f"Cleared conversation: {self.session_id}")

    def save_to_file(self, filepath: str) -> bool:
        """Save conversation to JSON file"""
        try:
            conversation_data = {
                "session_id": self.session_id,
                "created_at": self.created_at.isoformat(),
                "messages": [msg.to_dict() for msg in self.messages],
                "tool_executions": [tool.to_dict() for tool in self.tool_executions]
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved conversation to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            return False

    @classmethod
    def load_from_file(cls, filepath: str) -> 'SimpleConversation':
        """Load conversation from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            conversation = cls(session_id=data.get("session_id"))
            conversation.created_at = datetime.fromisoformat(
                data.get("created_at", datetime.now().isoformat())
            )

            # Load messages
            for msg_data in data.get("messages", []):
                conversation.messages.append(ConversationMessage.from_dict(msg_data))

            # Load tool executions
            for tool_data in data.get("tool_executions", []):
                conversation.tool_executions.append(ToolExecution.from_dict(tool_data))

            logger.info(f"Loaded conversation from {filepath}")
            return conversation

        except Exception as e:
            logger.error(f"Failed to load conversation: {e}")
            return cls()  # Return empty conversation on error
