"""
Unified Configuration for TuxAgent
Linux-integrated AI assistant configuration
"""
import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from datetime import datetime
from .models import TuxAgentModels


class ModelProvider(str, Enum):
    """Available model providers"""
    TOGETHER = "together"
    OPENAI = "openai"


class APIMode(str, Enum):
    """API usage tiers"""
    FREE = "free"        # 20 queries/month, no setup
    CLOUD = "cloud"      # TuxAgent Cloud with license key
    BYOK = "byok"        # Bring Your Own Key


class BYOKProvider(str, Enum):
    """BYOK provider options"""
    TOGETHER = "together"  # Together.ai - Kimi K2.5
    OPENAI = "openai"      # OpenAI


# Supported OpenAI models (must have vision + tool calling)
OPENAI_MODELS = {
    "gpt-5.2": "GPT-5.2 (Latest)",
}


@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    model_id: str
    provider: ModelProvider
    description: str
    temperature: float = 0.7
    max_tokens: int = 4000
    supports_tools: bool = False
    supports_vision: bool = False


class TuxAgentConfig:
    """Unified TuxAgent configuration"""

    # API Proxy (production system - all requests go through proxy)
    USE_API_PROXY = os.getenv('USE_API_PROXY', 'true').lower() == 'true'
    API_PROXY_URL = os.getenv('API_PROXY_URL', 'https://byteagent-api-proxy.vercel.app')

    # Desktop settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # D-Bus service configuration
    DBUS_SERVICE_NAME = "org.tuxagent.Assistant"
    DBUS_OBJECT_PATH = "/org/tuxagent/Assistant"
    DBUS_INTERFACE = "org.tuxagent.Assistant"

    # Default hotkeys
    DEFAULT_HOTKEY = "Super+Shift+A"
    DEFAULT_SCREENSHOT_HOTKEY = "Super+Shift+S"

    # Model configurations - Kimi K2.5 for multimodal capabilities
    MODELS = {
        "primary": ModelConfig(
            model_id=TuxAgentModels.get_primary_model(),
            provider=ModelProvider.TOGETHER,
            description="Kimi K2.5 for vision, text, and tool tasks",
            temperature=0.7,
            max_tokens=4000,
            supports_tools=True,
            supports_vision=True
        )
    }

    # Data directories
    _CONFIG_DIR = Path.home() / ".config" / "tuxagent"
    _DATA_DIR = Path.home() / ".local" / "share" / "tuxagent"
    _CACHE_DIR = Path.home() / ".cache" / "tuxagent"
    _PREFERENCES_FILE = _CONFIG_DIR / "preferences.json"
    _CREDENTIALS_FILE = _CONFIG_DIR / "credentials.json"

    # Feature flags
    MONETIZATION_ENABLED = False  # Set to True to enable Free/Cloud tiers

    # Usage limits (only applies when MONETIZATION_ENABLED = True)
    FREE_TIER_LIMIT = 20
    CLOUD_TIER_LIMIT = 500
    USAGE_WARNING_PERCENT_FREE = 0.25  # Warn at 25% remaining (5 queries)
    USAGE_WARNING_PERCENT_CLOUD = 0.10  # Warn at 10% remaining

    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        cls._CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        cls._DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls._CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (cls._DATA_DIR / "conversations").mkdir(parents=True, exist_ok=True)
        (cls._CACHE_DIR / "screenshots").mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_config_dir(cls) -> Path:
        """Get config directory path"""
        cls._CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        return cls._CONFIG_DIR

    @classmethod
    def get_data_dir(cls) -> Path:
        """Get data directory path"""
        cls._DATA_DIR.mkdir(parents=True, exist_ok=True)
        return cls._DATA_DIR

    @classmethod
    def get_cache_dir(cls) -> Path:
        """Get cache directory path"""
        cls._CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return cls._CACHE_DIR

    @classmethod
    def get_model(cls, model_key: str) -> Optional[ModelConfig]:
        """Get model configuration"""
        return cls.MODELS.get(model_key)

    @classmethod
    def get_primary_model(cls) -> ModelConfig:
        """Get primary model configuration"""
        return cls.MODELS["primary"]

    @classmethod
    def _load_preferences(cls) -> Dict[str, Any]:
        """Load preferences from JSON file"""
        try:
            if cls._PREFERENCES_FILE.exists():
                with open(cls._PREFERENCES_FILE, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
        return {}

    @classmethod
    def _save_preferences(cls, prefs: Dict[str, Any]):
        """Save preferences to JSON file"""
        try:
            cls._PREFERENCES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(cls._PREFERENCES_FILE, 'w') as f:
                json.dump(prefs, f, indent=2)
        except OSError:
            pass

    @classmethod
    def get_hotkey(cls) -> str:
        """Get configured hotkey"""
        prefs = cls._load_preferences()
        return prefs.get('hotkey', cls.DEFAULT_HOTKEY)

    @classmethod
    def set_hotkey(cls, hotkey: str):
        """Set hotkey"""
        prefs = cls._load_preferences()
        prefs['hotkey'] = hotkey
        cls._save_preferences(prefs)

    @classmethod
    def get_screenshot_hotkey(cls) -> str:
        """Get configured screenshot hotkey"""
        prefs = cls._load_preferences()
        return prefs.get('screenshot_hotkey', cls.DEFAULT_SCREENSHOT_HOTKEY)

    @classmethod
    def set_screenshot_hotkey(cls, hotkey: str):
        """Set screenshot hotkey"""
        prefs = cls._load_preferences()
        prefs['screenshot_hotkey'] = hotkey
        cls._save_preferences(prefs)

    @classmethod
    def is_autostart_enabled(cls) -> bool:
        """Check if autostart is enabled"""
        prefs = cls._load_preferences()
        return prefs.get('autostart', True)

    @classmethod
    def set_autostart_enabled(cls, enabled: bool):
        """Set autostart enabled"""
        prefs = cls._load_preferences()
        prefs['autostart'] = enabled
        cls._save_preferences(prefs)

    @classmethod
    def get_theme(cls) -> str:
        """Get UI theme (system, light, dark)"""
        prefs = cls._load_preferences()
        return prefs.get('theme', 'system')

    @classmethod
    def set_theme(cls, theme: str):
        """Set UI theme"""
        prefs = cls._load_preferences()
        prefs['theme'] = theme
        cls._save_preferences(prefs)

    # ========== API Mode & Provider Settings ==========

    @classmethod
    def get_api_mode(cls) -> str:
        """Get API mode (free, cloud, byok)"""
        # When monetization is disabled, always use BYOK
        if not cls.MONETIZATION_ENABLED:
            return APIMode.BYOK.value
        prefs = cls._load_preferences()
        return prefs.get('api_mode', APIMode.FREE.value)

    @classmethod
    def set_api_mode(cls, mode: str):
        """Set API mode"""
        prefs = cls._load_preferences()
        prefs['api_mode'] = mode
        cls._save_preferences(prefs)

    @classmethod
    def get_byok_provider(cls) -> str:
        """Get BYOK provider (together, openai)"""
        prefs = cls._load_preferences()
        return prefs.get('byok_provider', BYOKProvider.TOGETHER.value)

    @classmethod
    def set_byok_provider(cls, provider: str):
        """Set BYOK provider"""
        prefs = cls._load_preferences()
        prefs['byok_provider'] = provider
        cls._save_preferences(prefs)

    @classmethod
    def get_openai_model(cls) -> str:
        """Get selected OpenAI model"""
        prefs = cls._load_preferences()
        return prefs.get('openai_model', 'gpt-5.2')  # Default to latest

    @classmethod
    def set_openai_model(cls, model: str):
        """Set OpenAI model"""
        prefs = cls._load_preferences()
        prefs['openai_model'] = model
        cls._save_preferences(prefs)

    # ========== Credentials Management ==========

    @classmethod
    def _load_credentials(cls) -> Dict[str, Any]:
        """Load credentials from secure file"""
        try:
            if cls._CREDENTIALS_FILE.exists():
                with open(cls._CREDENTIALS_FILE, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
        return {}

    @classmethod
    def _save_credentials(cls, creds: Dict[str, Any]):
        """Save credentials to secure file with restricted permissions"""
        try:
            cls._CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(cls._CREDENTIALS_FILE, 'w') as f:
                json.dump(creds, f, indent=2)
            # Set file permissions to owner read/write only (600)
            cls._CREDENTIALS_FILE.chmod(0o600)
        except OSError:
            pass

    @classmethod
    def get_byok_api_key(cls) -> str:
        """Get BYOK API key for the current provider"""
        creds = cls._load_credentials()
        provider = cls.get_byok_provider()
        return creds.get(f'{provider}_api_key', '')

    @classmethod
    def set_byok_api_key(cls, api_key: str):
        """Set BYOK API key for the current provider"""
        creds = cls._load_credentials()
        provider = cls.get_byok_provider()
        creds[f'{provider}_api_key'] = api_key
        cls._save_credentials(creds)

    @classmethod
    def get_license_key(cls) -> str:
        """Get TuxAgent Cloud license key"""
        creds = cls._load_credentials()
        return creds.get('license_key', '')

    @classmethod
    def set_license_key(cls, key: str):
        """Set TuxAgent Cloud license key"""
        creds = cls._load_credentials()
        creds['license_key'] = key
        cls._save_credentials(creds)

    # ========== Usage Tracking ==========

    @classmethod
    def get_usage_count(cls) -> int:
        """Get current month's usage count"""
        prefs = cls._load_preferences()
        # Check if we need to reset (new month)
        reset_date = prefs.get('usage_reset_date', '')
        current_month = datetime.now().strftime('%Y-%m')
        if reset_date != current_month:
            # Reset counter for new month
            prefs['usage_count'] = 0
            prefs['usage_reset_date'] = current_month
            cls._save_preferences(prefs)
        return prefs.get('usage_count', 0)

    @classmethod
    def increment_usage(cls):
        """Increment usage counter"""
        prefs = cls._load_preferences()
        current_month = datetime.now().strftime('%Y-%m')
        # Ensure we're in the right month
        if prefs.get('usage_reset_date', '') != current_month:
            prefs['usage_count'] = 0
            prefs['usage_reset_date'] = current_month
        prefs['usage_count'] = prefs.get('usage_count', 0) + 1
        cls._save_preferences(prefs)

    @classmethod
    def get_usage_limit(cls) -> int:
        """Get usage limit for current tier"""
        mode = cls.get_api_mode()
        if mode == APIMode.FREE.value:
            return cls.FREE_TIER_LIMIT
        elif mode == APIMode.CLOUD.value:
            return cls.CLOUD_TIER_LIMIT
        else:  # BYOK
            return -1  # Unlimited

    @classmethod
    def get_usage_remaining(cls) -> int:
        """Get remaining queries for current tier"""
        limit = cls.get_usage_limit()
        if limit < 0:
            return -1  # Unlimited
        return max(0, limit - cls.get_usage_count())

    @classmethod
    def should_show_usage_warning(cls) -> bool:
        """Check if usage warning should be displayed"""
        # No warnings when monetization is disabled
        if not cls.MONETIZATION_ENABLED:
            return False

        mode = cls.get_api_mode()
        if mode == APIMode.BYOK.value:
            return False  # No warnings for BYOK

        remaining = cls.get_usage_remaining()
        limit = cls.get_usage_limit()

        if limit <= 0:
            return False

        if mode == APIMode.FREE.value:
            return remaining <= (limit * cls.USAGE_WARNING_PERCENT_FREE)
        elif mode == APIMode.CLOUD.value:
            return remaining <= (limit * cls.USAGE_WARNING_PERCENT_CLOUD)
        return False

    @classmethod
    def is_usage_exceeded(cls) -> bool:
        """Check if usage limit is exceeded"""
        mode = cls.get_api_mode()
        if mode == APIMode.BYOK.value:
            return False  # No limits for BYOK
        return cls.get_usage_remaining() <= 0

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Get configuration status"""
        return {
            "models_configured": len(cls.MODELS),
            "api_proxy_enabled": cls.USE_API_PROXY,
            "api_proxy_url": cls.API_PROXY_URL,
            "config_dir": str(cls._CONFIG_DIR),
            "data_dir": str(cls._DATA_DIR),
            "cache_dir": str(cls._CACHE_DIR),
            "hotkey": cls.get_hotkey(),
            "screenshot_hotkey": cls.get_screenshot_hotkey(),
            "autostart": cls.is_autostart_enabled(),
            "theme": cls.get_theme(),
            "api_mode": cls.get_api_mode(),
            "byok_provider": cls.get_byok_provider(),
            "usage_count": cls.get_usage_count(),
            "usage_limit": cls.get_usage_limit(),
            "usage_remaining": cls.get_usage_remaining(),
        }
