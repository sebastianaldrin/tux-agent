"""
System Tools
Shell command execution and wget downloads
"""
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from ..base import execute_command, resolve_path, DEFAULT_WORKSPACE

logger = logging.getLogger(__name__)


def _get_clean_environment():
    """Clean environment for subprocess - fixes AppImage Python path conflicts"""
    import os

    if 'APPIMAGE' not in os.environ:
        return None  # No changes for non-AppImage platforms

    clean_env = os.environ.copy()

    # Remove AppImage Python variables that cause subprocess conflicts
    clean_env.pop('PYTHONHOME', None)              # Points to /tmp/.mount_*/usr/bin
    clean_env.pop('PYTHONPATH', None)              # Points to AppImage site-packages
    clean_env.pop('PYTHONDONTWRITEBYTECODE', None) # Prevents bytecode conflicts

    return clean_env


def _check_dangerous_command(command: str) -> Optional[str]:
    """
    Check if a command is dangerous and return guidance message.
    Returns None if command is safe, or a guidance message if dangerous.

    Philosophy: Guide the AI to use safer alternatives, don't just block.
    """
    import re
    cmd_lower = command.lower().strip()

    # File deletion - guide to use trash instead
    # Match: rm, rm -f, rm -rf, rm -r, etc. (but not 'grep rm' or 'echo rm')
    if re.match(r'^rm\s+', cmd_lower) or re.match(r'^sudo\s+rm\s+', cmd_lower):
        return (
            "⚠️ **Safety Notice**: The `rm` command permanently deletes files (no recovery possible).\n\n"
            "**Safer alternative**: Use `gio trash <file>` instead - this moves files to Trash where they can be recovered.\n\n"
            "Example:\n"
            "  • Instead of: `rm document.pdf`\n"
            "  • Use: `gio trash document.pdf`\n\n"
            "The user can restore files from Trash if needed, or empty Trash later to permanently delete."
        )

    # Disk/partition destruction
    if re.match(r'^(sudo\s+)?(dd|mkfs|fdisk|parted|wipefs)\s+', cmd_lower):
        return (
            "⚠️ **Safety Notice**: This command can destroy disk data or partitions.\n\n"
            "These operations are irreversible and could cause data loss. "
            "Please ask the user to confirm they want to proceed, and consider if there's a safer GUI alternative."
        )

    # Recursive permission changes
    if re.match(r'^(sudo\s+)?chmod\s+.*-[rR]', cmd_lower) or 'chmod 777' in cmd_lower:
        return (
            "⚠️ **Safety Notice**: Recursive permission changes can break system security.\n\n"
            "`chmod -R` or `chmod 777` can make files world-writable or cause security issues. "
            "Consider changing permissions on specific files instead of recursively."
        )

    # System destruction commands
    if re.match(r'^(sudo\s+)?rm\s+.*-[rR].*\s+/', cmd_lower) or 'rm -rf /' in cmd_lower:
        return (
            "🛑 **Blocked**: This command could delete critical system files.\n\n"
            "Recursive deletion at root or system paths is extremely dangerous."
        )

    # Fork bombs and resource exhaustion
    if ':(){ :|:& };:' in command or re.search(r'\|\s*:\s*\|', command):
        return "🛑 **Blocked**: This appears to be a fork bomb that would crash the system."

    # Overwriting important files
    if re.match(r'^.*>\s*/(etc|boot|usr|bin|sbin)/', cmd_lower):
        return (
            "⚠️ **Safety Notice**: This command would overwrite system files.\n\n"
            "Redirecting output to system directories can break your installation."
        )

    # Downloading and executing unknown scripts
    if ('curl' in cmd_lower or 'wget' in cmd_lower) and ('| sh' in cmd_lower or '| bash' in cmd_lower):
        return (
            "⚠️ **Safety Notice**: Piping downloaded scripts directly to shell is risky.\n\n"
            "**Safer alternative**: Download the script first, review it, then execute:\n"
            "  1. `wget <url> -O script.sh`\n"
            "  2. `cat script.sh`  (review the contents)\n"
            "  3. `bash script.sh` (if it looks safe)"
        )

    return None  # Command appears safe


def shell_command(command: str, workspace: Path = DEFAULT_WORKSPACE, streaming_callback=None, permission_manager=None, page=None) -> Dict[str, Any]:
    """Execute shell commands with optional permission check"""
    try:
        if not command:
            return {'success': False, 'output': "❌ Command required"}

        # Safety guidance for dangerous commands
        # Guide the AI to use safer alternatives instead of blocking
        safety_check = _check_dangerous_command(command)
        if safety_check:
            logger.warning(f"Dangerous command blocked: {command}")
            return {'success': False, 'output': safety_check}

        # Debug logging
        logger.info(f"Shell command called: {command}")
        logger.info(f"Permission manager: {'Present' if permission_manager else 'None'}")
        logger.info(f"Page: {'Present' if page else 'None'}")

        # Permission checking is handled at the LlamaExecutor level for async support
        # This function just executes commands as requested
        logger.info(f"Executing shell command: {command}")
        
        # Execute command in workspace directory
        import subprocess
        import os
        
        # Ensure workspace exists
        workspace_str = str(workspace)
        if not os.path.exists(workspace_str):
            return {'success': False, 'output': f"❌ Workspace directory does not exist: {workspace_str}"}
        
        # Check if command contains shell operators (pipes, redirects, etc.)
        shell_operators = ['|', '>', '<', '&', ';', '$(', '`']
        use_shell = any(op in command for op in shell_operators)
        
        # Smart timeout based on command type
        timeout = 60  # Default timeout
        is_long_command = False
        command_type = "standard"
        
        if any(cmd in command.lower() for cmd in ['nmap', 'masscan', 'nikto', 'sqlmap']):
            timeout = 1800  # 30 minutes for security scanning tools
            is_long_command = True
            command_type = "security_scan"
        elif any(cmd in command.lower() for cmd in ['find', 'grep -r', 'du -', 'tar ', 'zip ', 'wget ']):
            timeout = 600   # 10 minutes for file operations and downloads
            is_long_command = True
            command_type = "file_operation"
        
        # Don't show time estimates upfront - they're often inaccurate for quick scans
        # Time estimates will be shown dynamically if command actually takes >30 seconds
        
        try:
            # Get clean environment for subprocess execution
            clean_env = _get_clean_environment()
            
            # For long commands with streaming, use real-time output
            if is_long_command and streaming_callback:
                return _execute_with_streaming(command, use_shell, timeout, workspace_str, streaming_callback, command_type)
            else:
                # For normal commands, use standard execution
                if use_shell:
                    # For commands with shell operators, run with shell=True
                    result = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=workspace_str,  # Run in workspace directory
                        env=clean_env       # Use clean environment for AppImage
                    )
                else:
                    # For simple commands, parse and run without shell for security
                    import shlex
                    try:
                        command_args = shlex.split(command)
                    except ValueError:
                        return {'success': False, 'output': "❌ Invalid command syntax"}
                    
                    result = subprocess.run(
                        command_args,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=workspace_str,  # Run in workspace directory
                        env=clean_env       # Use clean environment for AppImage
                    )
            
            result = {
                'success': result.returncode == 0,
                'output': result.stdout if result.returncode == 0 else result.stderr,
                'return_code': result.returncode,
                'command': command
            }
        except subprocess.TimeoutExpired:
            result = {'success': False, 'output': f"❌ Command timeout after {timeout}s - command '{command.split()[0] if command else 'unknown'}' took too long to execute"}
        except Exception as e:
            result = {'success': False, 'output': f"❌ Command failed: {e}"}
        
        if result['success']:
            output = f"💻 Shell Command: {command}\n"
            output += f"Output:\n{result['output']}"
            
            return {
                'success': True,
                'output': output,
                'command': command,
                'raw_output': result['output']
            }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'output': f"❌ Shell command failed: {e}"}


def wget_download(url: str, output_file: Optional[str] = None, workspace: Path = DEFAULT_WORKSPACE, streaming_callback=None) -> Dict[str, Any]:
    """Download file with wget and streaming progress"""
    try:
        if not url:
            return {'success': False, 'output': "❌ URL required"}
        
        # Determine output file
        if output_file:
            # Secure the output path
            output_path = resolve_path(output_file, workspace)
        else:
            # Use URL filename
            filename = url.split('/')[-1] or 'downloaded_file'
            output_path = workspace / filename
        
        # Build wget command with progress output
        command = f"wget --progress=bar:force -O '{output_path}' '{url}'"
        
        # Use streaming shell_command for large file downloads
        result = shell_command(command, workspace, streaming_callback)
        
        if result['success']:
            try:
                file_size = output_path.stat().st_size
                output = f"⬇️ Downloaded: {url}\n"
                output += f"• Saved to: {output_path.name}\n"
                output += f"• Size: {file_size} bytes"
                
                return {
                    'success': True,
                    'output': output,
                    'url': url,
                    'output_file': str(output_path),
                    'file_size': file_size
                }
            except:
                return {
                    'success': True,
                    'output': f"⬇️ Downloaded: {url}\n• Saved to: {output_path.name}",
                    'url': url,
                    'output_file': str(output_path)
                }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'output': f"❌ Download failed: {e}"}


def _safe_schedule_callback(callback, message):
    """Thread-safe callback scheduling with comprehensive error handling"""
    import asyncio
    
    try:
        if not callback or not callable(callback):
            return
            
        async def safe_callback_wrapper():
            """Wrapper to handle callback errors gracefully"""
            try:
                await callback(message)
            except Exception as e:
                logger.error(f"Streaming callback execution failed: {e}")
                # Don't re-raise - continue execution without crashing
        
        # Try to get the current event loop
        try:
            loop = asyncio.get_running_loop()
            # Schedule callback on the main thread
            loop.call_soon_threadsafe(lambda: asyncio.create_task(safe_callback_wrapper()))
        except RuntimeError:
            # No running event loop - try direct call (for testing environments)
            try:
                asyncio.run(safe_callback_wrapper())
            except Exception as e:
                logger.warning(f"Direct callback execution failed: {e}")
                
    except Exception as e:
        logger.error(f"Safe callback scheduling failed: {e}")
        # Continue execution without failing


def _execute_with_streaming(command, use_shell, timeout, workspace_str, streaming_callback, command_type):
    """Execute long-running commands with real-time progress streaming"""
    import subprocess
    import threading
    import time
    import shlex
    
    try:
        # Get clean environment for subprocess execution
        clean_env = _get_clean_environment()
        
        # Prepare command
        if use_shell:
            cmd = command
            shell = True
        else:
            try:
                cmd = shlex.split(command)
                shell = False
            except ValueError:
                return {'success': False, 'output': "❌ Invalid command syntax"}
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=workspace_str,
            bufsize=1,  # Line buffered
            universal_newlines=True,
            env=clean_env  # Use clean environment for AppImage
        )
        
        output_lines = []
        error_lines = []
        start_time = time.time()
        last_update = start_time
        
        def stream_progress():
            """Stream real-time progress updates"""
            nonlocal last_update
            first_update_sent = False
            
            while process.poll() is None:
                current_time = time.time()
                elapsed = current_time - start_time
                
                # Send first update after 30 seconds (only for truly long commands)
                if elapsed >= 30 and not first_update_sent:
                    if command_type == "security_scan":
                        estimated_time = "15-30 minutes"
                        message = "⏱️ Security Scan taking longer than expected...\n💡 Estimated total time: 15-30 minutes\n\n"
                    else:  # file_operation
                        estimated_time = "2-10 minutes"
                        message = "⏱️ File Operation taking longer than expected...\n💡 Estimated total time: 2-10 minutes\n\n"
                    
                    _safe_schedule_callback(streaming_callback, message)
                    first_update_sent = True
                    last_update = current_time
                
                # Send periodic updates every 30 seconds after first update
                elif first_update_sent and current_time - last_update >= 30:
                    elapsed_str = f"{int(elapsed//60)}m {int(elapsed%60)}s" if elapsed >= 60 else f"{int(elapsed)}s"
                    
                    if command_type == "security_scan":
                        # Parse nmap-style progress from stderr
                        recent_output = '\n'.join(output_lines[-5:] + error_lines[-5:])
                        progress_msg = _parse_scan_progress(recent_output, elapsed)
                        _safe_schedule_callback(streaming_callback,
                            f"🔍 Security scan running... ({elapsed_str} elapsed)\n{progress_msg}\n"
                        )
                    else:
                        _safe_schedule_callback(streaming_callback,
                            f"⚙️ {command_type.replace('_', ' ')} running... ({elapsed_str} elapsed)\n"
                        )
                    
                    last_update = current_time
                
                time.sleep(5)  # Check every 5 seconds
        
        # Start progress monitoring in background
        progress_thread = threading.Thread(target=stream_progress, daemon=True)
        progress_thread.start()
        
        # Read output line by line
        while True:
            # Check if process finished
            if process.poll() is not None:
                break
                
            # Read stdout
            try:
                stdout_line = process.stdout.readline()
                if stdout_line:
                    output_lines.append(stdout_line.strip())
                    # Stream interesting nmap output immediately
                    if command_type == "security_scan" and any(keyword in stdout_line.lower() for keyword in 
                        ['open', 'filtered', 'closed', 'discovered', 'completed', 'finished']):
                        _safe_schedule_callback(streaming_callback, f"📊 {stdout_line.strip()}\n")
            except:
                pass
                
            # Read stderr
            try:
                stderr_line = process.stderr.readline()
                if stderr_line:
                    error_lines.append(stderr_line.strip())
            except:
                pass
                
            # Check timeout
            if time.time() - start_time > timeout:
                process.terminate()
                process.wait(timeout=5)
                return {'success': False, 'output': f"❌ Command timeout after {timeout}s"}
        
        # Wait for process to complete
        stdout, stderr = process.communicate()
        if stdout:
            output_lines.extend(stdout.strip().split('\n'))
        if stderr:
            error_lines.extend(stderr.strip().split('\n'))
        
        # Final progress update
        elapsed = time.time() - start_time
        elapsed_str = f"{int(elapsed//60)}m {int(elapsed%60)}s" if elapsed >= 60 else f"{int(elapsed)}s"
        
        if process.returncode == 0:
            _safe_schedule_callback(streaming_callback, f"✅ Command completed successfully in {elapsed_str}!\n\n")
            full_output = '\n'.join(output_lines)
            return {
                'success': True,
                'output': f"💻 Shell Command: {command}\nOutput:\n{full_output}",
                'command': command,
                'raw_output': full_output,
                'execution_time': elapsed
            }
        else:
            full_error = '\n'.join(error_lines) or '\n'.join(output_lines)
            return {
                'success': False,
                'output': full_error,
                'return_code': process.returncode,
                'command': command,
                'execution_time': elapsed
            }
            
    except Exception as e:
        return {'success': False, 'output': f"❌ Streaming command failed: {e}"}


def _parse_scan_progress(output_text, elapsed_seconds):
    """Parse nmap/security scan progress from output"""
    if not output_text:
        return "🔍 Scanning in progress..."
    
    # Look for nmap-style progress indicators
    lines = output_text.lower()
    
    if 'host discovery' in lines or 'ping scan' in lines:
        return "🌐 Discovering live hosts..."
    elif 'port scan' in lines or 'scanning' in lines:
        return "🔍 Scanning ports..."
    elif 'service detection' in lines or 'version detection' in lines:
        return "🔬 Detecting service versions..."
    elif 'script scan' in lines or 'nse' in lines:
        return "📋 Running security scripts..."
    elif 'completed' in lines:
        return "🎯 Finalizing scan results..."
    elif elapsed_seconds > 300:  # 5+ minutes
        return "🔍 Deep scan in progress... (this may take a while)"
    else:
        return "🔍 Security analysis running..."