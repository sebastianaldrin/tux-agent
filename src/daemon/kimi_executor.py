"""
Kimi K2.5 Executor for TuxAgent
Multimodal LLM client with vision, text, and tool calling support
"""
import json
import logging
import time
import base64
from typing import Dict, List, Any, Optional, Callable, Generator
from pathlib import Path

import httpx

# Add parent paths for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.config import TuxAgentConfig, APIMode
from config.models import TuxAgentModels
from src.core.tool_executor import ToolExecutor
from src.core.simple_conversation import SimpleConversation, ToolExecution
from src.core.openai_schemas import get_tool_schemas_for_request
from src.core.api_providers import get_provider_for_mode, APIProvider

logger = logging.getLogger(__name__)


class KimiExecutor:
    """
    Executes queries using Kimi K2.5 via Together.ai API
    Supports vision (screenshots), text, and tool calling
    """

    def __init__(self, tool_executor: Optional[ToolExecutor] = None):
        """Initialize Kimi executor"""
        self.config = TuxAgentConfig
        self.model_config = self.config.get_primary_model()

        # Initialize API provider based on current settings
        self._init_provider()

        # Tool executor
        self.tool_executor = tool_executor or ToolExecutor()

        # Conversation state
        self.conversation: Optional[SimpleConversation] = None

        # Stats
        self.total_requests = 0
        self.total_tool_calls = 0

        logger.info(f"KimiExecutor initialized with provider: {self.provider.name}, model: {self.provider.model}")

    def _init_provider(self):
        """Initialize or reinitialize the API provider based on current config"""
        api_mode = self.config.get_api_mode()
        byok_provider = self.config.get_byok_provider()
        openai_model = self.config.get_openai_model()

        # Get credentials based on mode
        if api_mode == APIMode.BYOK.value:
            # BYOK mode - use user's API key, ignore license key
            api_key = self.config.get_byok_api_key()
            license_key = ""
            if not api_key:
                logger.warning("BYOK mode enabled but no API key configured")
        else:
            # Free/Cloud mode - use license key
            api_key = ""
            license_key = self._load_license_key()

        self.provider = get_provider_for_mode(
            api_mode=api_mode,
            byok_provider=byok_provider,
            api_key=api_key,
            license_key=license_key,
            openai_model=openai_model
        )

        # Keep these for backwards compatibility
        self.model_id = self.provider.model
        self.api_url = self.provider.endpoint
        self.license_key = license_key
        self.timeout = 120.0

    def refresh_provider(self):
        """Refresh provider configuration (call after settings change)"""
        self._init_provider()
        logger.info(f"Provider refreshed: {self.provider.name}")

    def _load_license_key(self) -> Optional[str]:
        """Load license key from config files or environment"""
        import os

        # Check environment variable
        env_key = os.getenv('TUXAGENT_LICENSE_KEY')
        if env_key:
            logger.info("Using license key from environment")
            return env_key

        # Check TuxAgent license file
        license_file = Path.home() / '.config' / 'tuxagent' / 'license.json'
        if license_file.exists():
            try:
                with open(license_file, 'r') as f:
                    data = json.load(f)
                if data.get('status') == 'active' and data.get('license_key'):
                    logger.info("Using TuxAgent license key")
                    return data['license_key']
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Error reading license file: {e}")

        return None

    def set_conversation(self, conversation: SimpleConversation):
        """Set the active conversation"""
        self.conversation = conversation

    def _build_system_prompt(self) -> str:
        """Build the system prompt for TuxAgent"""
        return """You are TuxAgent, a friendly Linux desktop assistant powered by Kimi K2.5.

Your role is to help users who are new to Linux (especially those migrating from Windows) accomplish tasks on their Linux desktop.

Key behaviors:
1. **Be friendly and patient** - Many users are learning Linux for the first time
2. **Explain what you're doing** - Don't just execute commands, explain why
3. **Prefer GUI solutions when available** - But offer terminal alternatives
4. **Be proactive about screenshots** - When the user includes a screenshot, analyze it carefully
5. **Use tools effectively** - You have access to many system tools, use them to help

When analyzing screenshots:
- Identify the application or desktop environment visible
- Point out specific UI elements you can see
- Provide context-aware help based on what's on screen

When executing commands:
- Always explain what a command does before running it
- Warn about potentially destructive operations
- Suggest safer alternatives when appropriate

Available capabilities:
- File operations (read, write, search, find)
- System monitoring (CPU, memory, disk, processes)
- Network diagnostics (connectivity, DNS, WiFi)
- Shell command execution
- Web search for solutions

Remember: You're helping someone who knows what they want to accomplish but may not know how to do it on Linux. Bridge that gap with clear, helpful guidance."""

    def _build_messages(self, user_message: str, images: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Build messages array for API request"""
        messages = []

        # System message
        messages.append({
            "role": "system",
            "content": self._build_system_prompt()
        })

        # Add conversation history if available
        if self.conversation:
            for msg in self.conversation.messages[-10:]:  # Last 10 messages for context
                if msg.images:
                    # Multimodal message
                    content = [{"type": "text", "text": msg.content}]
                    for img in msg.images:
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img}"}
                        })
                    messages.append({"role": msg.role, "content": content})
                else:
                    messages.append({"role": msg.role, "content": msg.content})

        # Current user message
        if images:
            # Multimodal message with images
            content = [{"type": "text", "text": user_message}]
            for img_base64 in images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                })
            messages.append({"role": "user", "content": content})
        else:
            # Text-only message
            messages.append({"role": "user", "content": user_message})

        return messages

    def _make_api_request(self, messages: List[Dict[str, Any]],
                         tools: Optional[List[Dict]] = None,
                         stream: bool = False) -> Dict[str, Any]:
        """Make API request using the configured provider"""
        return self.provider.make_request(
            messages=messages,
            tools=tools,
            temperature=self.model_config.temperature,
            max_tokens=self.model_config.max_tokens,
            stream=stream
        )

    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]],
                           progress_callback: Optional[Callable[[str, str], None]] = None) -> List[Dict[str, Any]]:
        """Execute tool calls and return results"""
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name", "unknown")
            tool_args_str = tool_call.get("function", {}).get("arguments", "{}")
            tool_id = tool_call.get("id", "")

            try:
                tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
            except json.JSONDecodeError:
                tool_args = {}

            logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

            if progress_callback:
                progress_callback("tool_executing", tool_name)

            # Execute the tool
            start_time = time.time()
            result = self.tool_executor.execute_tool(tool_name, **tool_args)
            execution_time = time.time() - start_time

            self.total_tool_calls += 1

            # Record tool execution in conversation
            if self.conversation:
                self.conversation.add_tool_execution(
                    tool_name=tool_name,
                    input_args=tool_args,
                    result=result,
                    success=result.get("success", False),
                    execution_time=execution_time
                )

            # Format result for API
            result_content = result.get("output", str(result))
            if len(result_content) > 10000:
                result_content = result_content[:10000] + "\n... (truncated)"

            results.append({
                "tool_call_id": tool_id,
                "role": "tool",
                "content": result_content
            })

            logger.info(f"Tool {tool_name} completed in {execution_time:.2f}s")

        return results

    def _check_usage_limits(self) -> Optional[str]:
        """
        Check if usage limits are exceeded or API key is missing

        Returns:
            Error message if limit exceeded or config issue, None otherwise
        """
        # Check for missing API key in BYOK mode
        mode = self.config.get_api_mode()
        if mode == APIMode.BYOK.value:
            api_key = self.config.get_byok_api_key()
            if not api_key:
                provider = self.config.get_byok_provider()
                provider_name = "Together.ai" if provider == "together" else "OpenAI"
                return (
                    f"No API key configured.\n\n"
                    f"To use TuxAgent, you need a {provider_name} API key:\n"
                    f"1. Click the gear icon (Settings)\n"
                    f"2. Enter your API key\n"
                    f"3. Click 'Test Connection' to verify"
                )

        # Check usage limits for paid tiers
        if self.config.is_usage_exceeded():
            if mode == APIMode.FREE.value:
                return (
                    "You've reached the free tier limit (20 queries/month). "
                    "Upgrade to TuxAgent Cloud for more queries, or use your own API key (BYOK).\n\n"
                    "Open Settings to configure your API access."
                )
            elif mode == APIMode.CLOUD.value:
                return (
                    "You've reached your monthly query limit. "
                    "Please contact support or upgrade your plan.\n\n"
                    "Alternatively, you can switch to BYOK (Bring Your Own Key) for unlimited queries."
                )
        return None

    def execute(self, user_message: str, images: Optional[List[str]] = None,
               progress_callback: Optional[Callable[[str, str], None]] = None,
               max_tool_iterations: int = 10) -> str:
        """
        Execute a query with optional images (screenshots)

        Args:
            user_message: The user's question or request
            images: Optional list of base64-encoded images
            progress_callback: Optional callback for progress updates (type, detail)
            max_tool_iterations: Maximum number of tool call iterations

        Returns:
            The assistant's response
        """
        # Check usage limits before proceeding
        limit_error = self._check_usage_limits()
        if limit_error:
            return limit_error

        self.total_requests += 1

        # Increment usage counter (for free/cloud tiers)
        if self.config.get_api_mode() != APIMode.BYOK.value:
            self.config.increment_usage()

        # Build initial messages (before adding to conversation to avoid duplication)
        messages = self._build_messages(user_message, images)

        # Add user message to conversation after building messages
        if self.conversation:
            self.conversation.add_user_message(user_message, images=images)

        # Get tool schemas
        tools = get_tool_schemas_for_request()

        # Tool call loop
        iteration = 0
        while iteration < max_tool_iterations:
            iteration += 1

            if progress_callback:
                progress_callback("thinking", f"Iteration {iteration}")

            # Make API request
            response = self._make_api_request(messages, tools)

            if response.get("error"):
                error_msg = response.get("message", "Unknown error")
                if self.conversation:
                    self.conversation.add_assistant_message(f"Error: {error_msg}")
                return f"I encountered an error: {error_msg}"

            # Extract response
            choices = response.get("choices", [])
            if not choices:
                return "I didn't receive a response. Please try again."

            assistant_message = choices[0].get("message", {})
            content = assistant_message.get("content", "")
            tool_calls = assistant_message.get("tool_calls", [])

            # If no tool calls, we're done
            if not tool_calls:
                if self.conversation:
                    self.conversation.add_assistant_message(content)
                return content

            # Execute tool calls
            logger.info(f"Processing {len(tool_calls)} tool calls")

            # Add assistant message with tool calls to messages
            messages.append(assistant_message)

            # Execute tools and get results
            tool_results = self._execute_tool_calls(tool_calls, progress_callback)

            # Add tool results to messages
            messages.extend(tool_results)

        # Max iterations reached
        final_response = "I've completed the maximum number of tool operations. Here's what I found so far."
        if self.conversation:
            self.conversation.add_assistant_message(final_response)
        return final_response

    def execute_stream(self, user_message: str, images: Optional[List[str]] = None,
                      progress_callback: Optional[Callable[[str, str], None]] = None) -> Generator[str, None, None]:
        """
        Execute a query with streaming response

        Yields chunks of the response as they arrive
        """
        # Currently yields complete response; streaming can be added later
        response = self.execute(user_message, images, progress_callback)
        yield response

    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics"""
        return {
            "model": self.model_id,
            "provider": self.provider.name,
            "api_mode": self.config.get_api_mode(),
            "total_requests": self.total_requests,
            "total_tool_calls": self.total_tool_calls,
            "available_tools": self.tool_executor.get_tool_count(),
            "usage_count": self.config.get_usage_count(),
            "usage_limit": self.config.get_usage_limit(),
            "usage_remaining": self.config.get_usage_remaining(),
        }
