"""
Platform-Aware Tool Executor for TuxAgent
Dynamically loads tools based on platform using the platform router
"""
import os
import logging
import functools
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path

# Import platform router and shared utilities
from .tools.platform_router import router
from .tools.base import DEFAULT_WORKSPACE, resolve_path

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Executes tools with workspace awareness and platform-specific routing
    TuxAgent version - Linux-only, no Flet/GUI dependencies
    """

    def __init__(self, workspace_path: str = None):
        self.workspace = Path(workspace_path) if workspace_path else DEFAULT_WORKSPACE
        self.workspace.mkdir(parents=True, exist_ok=True)

        logger.info(f"ToolExecutor initialized with workspace: {self.workspace}")

        # Initialize platform router and tool registry
        self.router = router

        # Token context for tools
        self._token_context = None
        self.functions = self._register_tools()

        logger.info(f"Tool executor initialized with {len(self.functions)} tools for {self.router.platform}")

    def _create_workspace_wrapper(self, module_name: str, function_name: str):
        """Create workspace-aware wrapper for file operations"""
        base_func = self.router.get_tool_function(module_name, function_name)

        @functools.wraps(base_func)
        def wrapper(*args, **kwargs):
            # Add workspace if not provided
            if 'workspace' not in kwargs:
                kwargs['workspace'] = self.workspace
            return base_func(*args, **kwargs)

        return wrapper

    def _register_tools(self) -> Dict[str, Callable]:
        """Register all tools dynamically using platform router"""
        tools = {}

        try:
            # Essential Filesystem Tools - workspace-aware
            tools['read_file'] = self._create_workspace_wrapper('file_ops', 'read_file')
            tools['write_file'] = self._create_workspace_wrapper('file_ops', 'write_file')
            tools['list_directory'] = self._create_workspace_wrapper('file_ops', 'list_directory')
            tools['find_files'] = self._create_workspace_wrapper('file_ops', 'find_files')
            tools['grep_search'] = self._create_workspace_wrapper('file_ops', 'grep_search')
            tools['word_count'] = self._create_workspace_wrapper('file_ops', 'word_count')
            tools['file_head'] = self._create_workspace_wrapper('file_ops', 'file_head')
            tools['file_tail'] = self._create_workspace_wrapper('file_ops', 'file_tail')
            tools['file_info'] = self._create_workspace_wrapper('file_ops', 'file_info')

            # Document Processing Tools - workspace-aware
            tools['create_pdf'] = self._create_workspace_wrapper('file_ops', 'create_pdf')
            tools['create_docx'] = self._create_workspace_wrapper('file_ops', 'create_docx')
            tools['read_image_metadata'] = self._create_workspace_wrapper('file_ops', 'read_image_metadata')

            # Basic Network Tools - direct
            tools['dns_lookup'] = self.router.get_tool_function('network_basic', 'dns_lookup')
            tools['whois_lookup'] = self.router.get_tool_function('network_basic', 'whois_lookup')
            tools['analyze_website'] = self.router.get_tool_function('network_basic', 'analyze_website')

            # Advanced Network Tools - direct
            tools['ping_host'] = self.router.get_tool_function('network_advanced', 'ping_host')
            tools['traceroute'] = self.router.get_tool_function('network_advanced', 'traceroute')
            tools['port_scan'] = self.router.get_tool_function('network_advanced', 'port_scan')
            tools['dig_lookup'] = self.router.get_tool_function('network_advanced', 'dig_lookup')
            tools['curl_request'] = self.router.get_tool_function('network_advanced', 'curl_request')
            tools['netstat_connections'] = self.router.get_tool_function('network_advanced', 'netstat_connections')
            tools['arp_table'] = self.router.get_tool_function('network_advanced', 'arp_table')
            tools['view_source'] = self.router.get_tool_function('network_advanced', 'view_source')
            tools['nslookup_query'] = self.router.get_tool_function('network_advanced', 'nslookup_query')
            tools['network_speed_test'] = self.router.get_tool_function('network_advanced', 'network_speed_test')

            # System Monitoring Tools - direct
            tools['system_monitor'] = self.router.get_tool_function('system_monitor', 'system_monitor')
            tools['process_analyzer'] = self.router.get_tool_function('system_monitor', 'process_analyzer')
            tools['top_snapshot'] = self.router.get_tool_function('system_monitor', 'top_snapshot')
            tools['disk_usage'] = self.router.get_tool_function('system_monitor', 'disk_usage')
            tools['memory_info'] = self.router.get_tool_function('system_monitor', 'memory_info')
            tools['system_info'] = self.router.get_tool_function('system_monitor', 'system_info')
            tools['uptime_info'] = self.router.get_tool_function('system_monitor', 'uptime_info')

            # Security Tools - direct
            tools['ssl_certificate_check'] = self.router.get_tool_function('security', 'ssl_certificate_check')
            tools['security_headers_check'] = self.router.get_tool_function('security', 'security_headers_check')
            tools['vulnerability_scan'] = self.router.get_tool_function('security', 'vulnerability_scan')
            tools['openssl_check'] = self.router.get_tool_function('security', 'openssl_check')

            # Data Analysis Tools
            tools['json_analyzer'] = self.router.get_tool_function('data_analysis', 'json_analyzer')
            tools['hash_calculator'] = self.router.get_tool_function('data_analysis', 'hash_calculator')
            tools['base64_encode'] = self.router.get_tool_function('data_analysis', 'base64_encode')
            tools['compress_file'] = self._create_workspace_wrapper('data_analysis', 'compress_file')

            # Web Analysis Tools - direct
            tools['page_performance_test'] = self.router.get_tool_function('web_analysis', 'page_performance_test')
            tools['link_checker'] = self.router.get_tool_function('web_analysis', 'link_checker')
            tools['hosting_provider_lookup'] = self.router.get_tool_function('web_analysis', 'hosting_provider_lookup')

            # Diagnostics Tools - direct
            tools['internet_connectivity_test'] = self.router.get_tool_function('diagnostics', 'internet_connectivity_test')
            tools['network_speed_diagnosis'] = self.router.get_tool_function('diagnostics', 'network_speed_diagnosis')
            tools['domain_health_check'] = self.router.get_tool_function('diagnostics', 'domain_health_check')
            tools['network_troubleshoot_wizard'] = self.router.get_tool_function('diagnostics', 'network_troubleshoot_wizard')
            tools['wifi_analyzer'] = self.router.get_tool_function('diagnostics', 'wifi_analyzer')

            # External Security Tools - direct
            tools['external_subdomain_enum'] = self.router.get_tool_function('external_security', 'external_subdomain_enum')
            tools['external_tech_stack_detection'] = self.router.get_tool_function('external_security', 'external_tech_stack_detection')
            tools['external_network_discovery'] = self.router.get_tool_function('external_security', 'external_network_discovery')
            tools['external_web_vuln_scan'] = self.router.get_tool_function('external_security', 'external_web_vuln_scan')
            tools['external_comprehensive_security_audit'] = self.router.get_tool_function('external_security', 'external_comprehensive_security_audit')

            # System Tools - workspace-aware
            tools['shell_command'] = self._create_workspace_wrapper('system_tools', 'shell_command')
            tools['wget_download'] = self._create_workspace_wrapper('system_tools', 'wget_download')

            # Web Search Tools - direct
            tools['web_search'] = self.router.get_tool_function('web_search', 'web_search')
            tools['search_news'] = self.router.get_tool_function('web_search', 'search_news')
            tools['search_images'] = self.router.get_tool_function('web_search', 'search_images')
            tools['search_stackoverflow'] = self.router.get_tool_function('web_search', 'search_stackoverflow')
            tools['search_github'] = self.router.get_tool_function('web_search', 'search_github')

            # Power Monitoring Tools - direct
            tools['battery_monitor'] = self.router.get_tool_function('power_monitor', 'battery_monitor')
            tools['cpu_frequency_monitor'] = self.router.get_tool_function('power_monitor', 'cpu_frequency_monitor')
            tools['temperature_monitor'] = self.router.get_tool_function('power_monitor', 'temperature_monitor')
            tools['power_state_monitor'] = self.router.get_tool_function('power_monitor', 'power_state_monitor')

        except ImportError as e:
            logger.error(f"Failed to register tools: {e}")

        logger.info(f"Successfully registered {len(tools)} tools for platform: {self.router.platform}")
        return tools

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return list(self.functions.keys())

    def get_tool_count(self) -> int:
        """Get total number of available tools"""
        return len(self.functions)

    def execute_tool_sync(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool synchronously"""
        if tool_name not in self.functions:
            return {
                'success': False,
                'output': f"Tool '{tool_name}' not found. Available tools: {', '.join(self.functions.keys())}"
            }

        try:
            # Add token context for tools that support it
            if self._token_context and tool_name in ['read_file']:
                kwargs['_context'] = self._token_context

            # Execute the tool
            result = self.functions[tool_name](**kwargs)

            # Ensure result has required format
            if not isinstance(result, dict):
                result = {'success': False, 'output': str(result)}

            # Add platform info for debugging
            if isinstance(result, dict) and result.get('success'):
                result['platform'] = self.router.platform

            return result

        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                logger.warning(f"Invalid parameters for {tool_name}: {e}")
                return {
                    'success': False,
                    'output': f"Invalid arguments for '{tool_name}': {str(e)}"
                }
            else:
                logger.error(f"Type error executing tool {tool_name}: {e}")
                return {
                    'success': False,
                    'output': f"Tool execution error for '{tool_name}': {str(e)}"
                }
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                'success': False,
                'output': f"Tool '{tool_name}' failed: {str(e)}"
            }

    def execute_tool(self, tool_name: str, streaming_callback=None, **kwargs) -> Dict[str, Any]:
        """Execute a tool with optional streaming callback"""
        # Tools that support streaming
        streaming_tools = {
            'shell_command', 'vulnerability_scan', 'wget_download',
            'find_files', 'network_speed_test'
        }

        # If this is a streaming tool and callback provided, pass it along
        if tool_name in streaming_tools and streaming_callback is not None:
            kwargs['streaming_callback'] = streaming_callback

        return self.execute_tool_sync(tool_name, **kwargs)

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get information about a specific tool"""
        if tool_name not in self.functions:
            return {'exists': False, 'error': f"Tool '{tool_name}' not found"}

        import inspect
        tool_func = self.functions[tool_name]

        return {
            'exists': True,
            'name': tool_name,
            'module': tool_func.__module__,
            'doc': inspect.getdoc(tool_func),
            'signature': str(inspect.signature(tool_func)),
            'platform': self.router.platform
        }

    def get_platform_info(self) -> Dict[str, Any]:
        """Get platform information"""
        return self.router.get_platform_info()

    def get_workspace_path(self) -> str:
        """Get current workspace path"""
        return str(self.workspace)

    def set_workspace_path(self, path: str):
        """Set workspace path"""
        old_workspace = self.workspace
        self.workspace = Path(path)
        self.workspace.mkdir(parents=True, exist_ok=True)
        logger.info(f"Workspace changed from {old_workspace} to {self.workspace}")

    def set_token_context(self, current_tokens: int, max_tokens: int = 40960):
        """Set token context for tools to make intelligent decisions"""
        reserved_for_response = 8000
        safety_margin = 1000
        available = max(1000, max_tokens - current_tokens - reserved_for_response - safety_margin)

        self._token_context = {
            'current_tokens': current_tokens,
            'max_tokens': max_tokens,
            'available_tokens': available,
            'reserved_response': reserved_for_response,
            'safety_margin': safety_margin
        }

    def get_status_summary(self) -> Dict[str, Any]:
        """Get status summary"""
        return {
            'system': 'platform-router',
            'total_tools': len(self.functions),
            'platform': self.router.platform,
            'workspace': str(self.workspace)
        }
