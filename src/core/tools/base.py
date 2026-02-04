"""
Base utilities for tool operations
Shared functions used across tool modules
"""
import subprocess
import platform
from typing import Dict, List, Any, Optional
from pathlib import Path
import os

# Default workspace setup - TuxAgent uses user's home directory
DEFAULT_WORKSPACE = Path(os.getenv('TUXAGENT_WORKSPACE', Path.home()))


def resolve_path(path: str, workspace: Path) -> Path:
    """Secure path resolution with subdirectory support and configurable workspace"""
    # Handle current directory reference
    if path in ('.', ''):
        return workspace

    # Convert to Path object for manipulation
    path_obj = Path(path)

    # Security check: block any path traversal attempts
    if '..' in path_obj.parts:
        # If contains .., just use the final filename for security
        safe_name = path_obj.name.replace('..', '').replace('/', '_')
        if not safe_name:
            safe_name = 'file.txt'
        return workspace / safe_name

    # Handle absolute paths - TuxAgent allows access to any path on the system
    if path_obj.is_absolute():
        return path_obj

    # Handle relative paths within workspace
    try:
        # Build secure path within workspace
        safe_parts = []
        for part in path_obj.parts:
            safe_part = part.replace('..', '').replace('/', '_')
            if safe_part and safe_part != '.':
                safe_parts.append(safe_part)

        if not safe_parts:
            return workspace

        return workspace / Path(*safe_parts)

    except (ValueError, OSError):
        safe_name = path_obj.name.replace('..', '').replace('/', '_')
        if not safe_name:
            safe_name = 'file.txt'
        return workspace / safe_name


def execute_command(command: List[str], timeout: int = 30, input_data: str = None,
                   cwd: str = None) -> Dict[str, Any]:
    """Safe command execution for Linux systems"""
    try:
        # Validate command to prevent injection
        if not command or not isinstance(command, list):
            return {'success': False, 'output': "Invalid command format"}

        if not command[0] or not command[0].strip():
            return {'success': False, 'output': "Empty command not allowed"}

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input_data,
            cwd=cwd
        )

        return {
            'success': result.returncode == 0,
            'output': result.stdout if result.returncode == 0 else result.stderr,
            'return_code': result.returncode,
            'command': ' '.join(command)
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'output': f"Command timeout after {timeout}s"}
    except FileNotFoundError:
        return {'success': False, 'output': f"Command not found: '{command[0]}'"}
    except PermissionError:
        return {'success': False, 'output': f"Permission denied executing '{command[0]}'"}
    except OSError as e:
        return {'success': False, 'output': f"System error: {str(e)}"}
    except Exception as e:
        return {'success': False, 'output': f"Command failed: {str(e)}"}


def get_platform_command(base_command: str) -> str:
    """Get platform-appropriate command (Linux only for TuxAgent)"""
    # TuxAgent is Linux-only, so no command mapping needed
    return base_command
