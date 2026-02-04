"""
OpenAI tool schemas for Kimi K2.5 function calling
Converts TuxAgent tools to OpenAI's format with vision support
"""


def get_all_openai_tools():
    """Get all tool schemas in OpenAI's function calling format"""
    return [
        # Essential Filesystem Tools
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read any file type (text, PDF, DOCX, Excel) with smart pagination. Auto-truncates large files (>2000 lines) for safety.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to file to read"},
                        "start_line": {"type": "integer", "description": "Starting line number (1-indexed)"},
                        "limit_lines": {"type": "integer", "description": "Number of lines to read"},
                        "auto_truncate": {"type": "boolean", "description": "Auto-truncate large files (default: true)"}
                    },
                    "required": ["file_path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write content to file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to file to write"},
                        "content": {"type": "string", "description": "Content to write to file"}
                    },
                    "required": ["file_path", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": "List directory contents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path to list", "default": "."}
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "find_files",
                "description": "Search for files and directories by pattern",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "File pattern to search"},
                        "path": {"type": "string", "description": "Path to search in", "default": "."}
                    },
                    "required": ["pattern"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "grep_search",
                "description": "Search text patterns in files",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Text pattern to search"},
                        "file_path": {"type": "string", "description": "File to search in"}
                    },
                    "required": ["pattern", "file_path"]
                }
            }
        },

        # System Monitoring Tools
        {
            "type": "function",
            "function": {
                "name": "system_monitor",
                "description": "Monitor system resources (CPU, RAM, disk usage)",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "process_analyzer",
                "description": "Analyze running processes and resource usage",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "disk_usage",
                "description": "Disk space usage by filesystem",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "memory_info",
                "description": "Detailed memory usage information",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "system_info",
                "description": "System information (OS, kernel, architecture)",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },

        # Network Tools
        {
            "type": "function",
            "function": {
                "name": "dns_lookup",
                "description": "DNS lookup for domain to get IP addresses",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string", "description": "Domain name to lookup"}
                    },
                    "required": ["domain"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "ping_host",
                "description": "Ping host for connectivity test",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string", "description": "Host to ping"}
                    },
                    "required": ["host"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "wifi_analyzer",
                "description": "Analyze WiFi networks and signal strength",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "internet_connectivity_test",
                "description": "Comprehensive internet connectivity test",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },

        # Shell Command Tool
        {
            "type": "function",
            "function": {
                "name": "shell_command",
                "description": "Execute command line tools. Use this for any Linux command.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Command to execute"}
                    },
                    "required": ["command"]
                }
            }
        },

        # Web Search Tools
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "num_results": {"type": "integer", "description": "Number of results (1-20)", "default": 5}
                    },
                    "required": ["query"]
                }
            }
        },

        # Power Monitoring
        {
            "type": "function",
            "function": {
                "name": "battery_monitor",
                "description": "Monitor battery status for laptops",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "temperature_monitor",
                "description": "Monitor system temperatures",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        }
    ]


def get_tool_schemas_for_request() -> list:
    """Get tool schemas formatted for API request"""
    return get_all_openai_tools()
