"""
API Providers for TuxAgent
Multi-provider support for LLM API requests
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for an API provider"""
    name: str
    endpoint: str
    model: str
    supports_vision: bool = True
    supports_tools: bool = True


class APIProvider(ABC):
    """Base class for API providers"""

    def __init__(self, config: ProviderConfig, api_key: str = ""):
        self.config = config
        self.api_key = api_key
        self.timeout = 120.0  # 2 minutes

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def model(self) -> str:
        return self.config.model

    @property
    def endpoint(self) -> str:
        return self.config.endpoint

    def supports_vision(self) -> bool:
        return self.config.supports_vision

    def supports_tools(self) -> bool:
        return self.config.supports_tools

    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """Get headers for API request"""
        pass

    def make_request(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        stream: bool = False,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Make API request with retry logic"""
        import time

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        if tools and self.supports_tools():
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = self.get_headers()
        last_error = None

        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        self.endpoint,
                        json=payload,
                        headers=headers
                    )

                    if response.status_code != 200:
                        logger.error(f"API error: {response.status_code} - {response.text}")
                        # Retry on server errors
                        if response.status_code >= 500 and attempt < max_retries - 1:
                            wait_time = 2 ** attempt  # 1, 2, 4 seconds
                            logger.info(f"Server error, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                            continue
                        return {
                            "error": True,
                            "message": f"API error: {response.status_code}"
                        }

                    return self._parse_response(response.json())

            except httpx.TimeoutException:
                last_error = "timeout"
                logger.error(f"API request timed out (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
            except httpx.ConnectError as e:
                last_error = "connection"
                logger.error(f"Connection error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error: {e}")
                # Don't retry auth errors
                if e.response.status_code == 401:
                    return {"error": True, "message": "Invalid API key. Please check your API key in Settings."}
                elif e.response.status_code == 403:
                    return {"error": True, "message": "Access denied. Your API key may not have the required permissions."}
                elif e.response.status_code == 429:
                    # Rate limit - wait longer
                    if attempt < max_retries - 1:
                        wait_time = 5 * (attempt + 1)
                        logger.info(f"Rate limited, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    return {"error": True, "message": "Rate limit exceeded. Please wait a moment and try again."}
                elif e.response.status_code >= 500:
                    last_error = "server"
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"Server error, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                return {"error": True, "message": f"API error: {e.response.status_code}"}
            except Exception as e:
                last_error = str(e)
                logger.error(f"API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue

        # All retries failed
        if last_error == "timeout":
            return {
                "error": True,
                "message": "Request timed out after multiple attempts. Please try again."
            }
        elif last_error == "connection":
            return {
                "error": True,
                "message": "Cannot connect to AI service after multiple attempts. Please check your internet connection."
            }
        elif last_error == "server":
            return {
                "error": True,
                "message": "AI service is temporarily unavailable. Please try again later."
            }
        else:
            error_str = str(last_error).lower()
            if "connection" in error_str or "network" in error_str:
                return {"error": True, "message": "Network error. Please check your internet connection."}
            elif "dns" in error_str or "resolve" in error_str:
                return {"error": True, "message": "Cannot reach AI service. Please check your internet connection."}
            return {"error": True, "message": f"Error: {last_error}"}

    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse API response (override for custom formats)"""
        return response

    def test_connection(self) -> Dict[str, Any]:
        """Test API connection with a simple request"""
        test_messages = [{"role": "user", "content": "Say 'OK' if you can hear me."}]
        try:
            result = self.make_request(test_messages, max_tokens=10)
            if result.get("error"):
                return {"success": False, "message": result.get("message", "Unknown error")}

            # Check if we got a valid response
            choices = result.get("choices", [])
            if choices and choices[0].get("message", {}).get("content"):
                return {"success": True, "message": "Connection successful"}
            return {"success": False, "message": "No response received"}
        except Exception as e:
            return {"success": False, "message": str(e)}


class TuxAgentCloudProvider(APIProvider):
    """TuxAgent Cloud provider - our API proxy with license key authentication"""

    def __init__(self, license_key: str = ""):
        config = ProviderConfig(
            name="TuxAgent Cloud",
            endpoint="https://byteagent-api-proxy.vercel.app/api/llama",
            model="moonshotai/kimi-k2.5",
            supports_vision=True,
            supports_tools=True
        )
        super().__init__(config, license_key)

    def get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-License-Key": self.api_key
        }

    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse TuxAgent Cloud wrapped response"""
        # API proxy wraps response in {"success": true, "data": {...}}
        if response.get("success") and "data" in response:
            return response["data"]
        elif response.get("error"):
            error_msg = response.get("error")
            if isinstance(error_msg, str):
                return {"error": True, "message": error_msg}
            return {"error": True, "message": str(error_msg) if error_msg else "Unknown error"}
        return response


class TogetherProvider(APIProvider):
    """Together.ai provider - BYOK option for Kimi K2.5"""

    def __init__(self, api_key: str = ""):
        config = ProviderConfig(
            name="Together.ai",
            endpoint="https://api.together.xyz/v1/chat/completions",
            model="moonshotai/kimi-k2.5",
            supports_vision=True,
            supports_tools=True
        )
        super().__init__(config, api_key)

    def get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }


class OpenAIProvider(APIProvider):
    """OpenAI provider - BYOK option"""

    def __init__(self, api_key: str = "", model: str = "gpt-5.2"):
        config = ProviderConfig(
            name="OpenAI",
            endpoint="https://api.openai.com/v1/chat/completions",
            model=model,
            supports_vision=True,
            supports_tools=True
        )
        super().__init__(config, api_key)

    def get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }


def get_provider_for_mode(api_mode: str, byok_provider: str = "", api_key: str = "", license_key: str = "", openai_model: str = "gpt-5.2") -> APIProvider:
    """
    Factory function to get the appropriate provider for the current mode

    Args:
        api_mode: "free", "cloud", or "byok"
        byok_provider: "together" or "openai" (only used if api_mode is "byok")
        api_key: API key for BYOK providers
        license_key: License key for cloud/free tiers
        openai_model: OpenAI model to use (only used if byok_provider is "openai")

    Returns:
        Configured APIProvider instance
    """
    if api_mode in ("free", "cloud"):
        return TuxAgentCloudProvider(license_key)
    elif api_mode == "byok":
        if byok_provider == "openai":
            return OpenAIProvider(api_key, model=openai_model)
        else:
            return TogetherProvider(api_key)
    else:
        # Default to cloud
        return TuxAgentCloudProvider(license_key)


# Provider info for UI display
PROVIDER_INFO = {
    "together": {
        "name": "Together.ai",
        "model": "Kimi K2.5",
        "description": "Fast inference with Kimi K2.5 model",
        "signup_url": "https://api.together.xyz/signin"
    },
    "openai": {
        "name": "OpenAI",
        "model": "GPT-5.2",
        "description": "Best vision + tool calling (98.7% accuracy)",
        "signup_url": "https://platform.openai.com/api-keys"
    }
}
