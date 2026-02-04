"""
Platform Router for Tool Discovery
TuxAgent version - Linux-only implementation
"""
import platform
import importlib
from typing import Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class PlatformRouter:
    """Routes tool requests to platform-specific implementations (Linux only)"""

    def __init__(self):
        self.platform = 'unix'  # TuxAgent is Linux-only
        self._tool_cache = {}
        logger.info(f"Platform router initialized for: {self.platform}")

    def get_tool_function(self, module_name: str, function_name: str) -> Callable:
        """Get platform-specific tool function"""
        cache_key = f"{self.platform}.{module_name}.{function_name}"

        if cache_key not in self._tool_cache:
            # Try multiple import paths to handle different execution contexts
            import_paths = [
                f"src.core.tools.{self.platform}.{module_name}",
                f"core.tools.{self.platform}.{module_name}",
            ]

            module = None
            for module_path in import_paths:
                try:
                    module = importlib.import_module(module_path)
                    break
                except ImportError:
                    continue

            if module and hasattr(module, function_name):
                self._tool_cache[cache_key] = getattr(module, function_name)
            else:
                # Fall back to shared module if exists
                shared_paths = [
                    f"src.core.tools.shared.{module_name}",
                    f"core.tools.shared.{module_name}",
                ]

                for module_path in shared_paths:
                    try:
                        module = importlib.import_module(module_path)
                        if hasattr(module, function_name):
                            self._tool_cache[cache_key] = getattr(module, function_name)
                            break
                    except ImportError:
                        continue
                else:
                    raise ImportError(
                        f"Tool {function_name} not found in {module_name} for platform {self.platform}"
                    )

        return self._tool_cache[cache_key]

    def get_available_modules(self) -> Dict[str, str]:
        """Get available tool modules for current platform"""
        modules = {}

        # Define expected modules
        expected_modules = [
            'file_ops', 'network_basic', 'network_advanced', 'system_monitor',
            'system_tools', 'security', 'diagnostics', 'external_security',
            'data_analysis', 'web_analysis', 'web_search', 'power_monitor'
        ]

        for module_name in expected_modules:
            # Try platform-specific first
            import_paths = [
                f"src.core.tools.{self.platform}.{module_name}",
                f"core.tools.{self.platform}.{module_name}",
            ]

            found = False
            for module_path in import_paths:
                try:
                    importlib.import_module(module_path)
                    modules[module_name] = f"{self.platform}.{module_name}"
                    found = True
                    break
                except ImportError:
                    continue

            if not found:
                # Fall back to shared
                shared_paths = [
                    f"src.core.tools.shared.{module_name}",
                    f"core.tools.shared.{module_name}",
                ]

                for module_path in shared_paths:
                    try:
                        importlib.import_module(module_path)
                        modules[module_name] = f"shared.{module_name}"
                        found = True
                        break
                    except ImportError:
                        continue

                if not found:
                    logger.warning(f"Module {module_name} not found for platform {self.platform}")

        return modules

    def get_platform_info(self) -> Dict[str, Any]:
        """Get detailed platform information"""
        return {
            'platform': self.platform,
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version()
        }


# Global router instance
router = PlatformRouter()
