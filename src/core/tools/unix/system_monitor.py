"""
System Monitoring Tools
System resource monitoring and process analysis
"""
import logging
import psutil
import platform
from typing import Dict, Any

from ..base import execute_command

logger = logging.getLogger(__name__)


def system_monitor() -> Dict[str, Any]:
    """Monitor system resources (CPU, RAM, disk)"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'success': True,
            'output': f"💻 System Monitor\n• CPU: {cpu_percent}%\n• RAM: {memory.percent}% ({memory.used // (1024**3)}GB/{memory.total // (1024**3)}GB)\n• Disk: {disk.percent}% ({disk.used // (1024**3)}GB/{disk.total // (1024**3)}GB)",
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'disk_percent': disk.percent
        }
    except psutil.AccessDenied:
        return {'success': False, 'output': "❌ Permission denied accessing system information - elevated privileges may be required"}
    except psutil.NoSuchProcess:
        return {'success': False, 'output': "❌ Process information unavailable - system process may have terminated"}
    except OSError as e:
        if "No such file or directory" in str(e):
            return {'success': False, 'output': "❌ System monitoring failed - disk path not accessible (may be Windows vs Linux path issue)"}
        else:
            return {'success': False, 'output': f"❌ System error during monitoring: {str(e)} - unable to access system resources"}
    except Exception as e:
        return {'success': False, 'output': f"❌ System monitoring failed: {str(e)} - unable to retrieve system information"}


def process_analyzer() -> Dict[str, Any]:
    """Analyze running processes and resource usage"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                proc_info = proc.info
                if proc_info['cpu_percent'] > 1.0 or proc_info['memory_percent'] > 1.0:
                    processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        top_processes = processes[:10]
        
        output = "🔍 Top Resource-Heavy Processes:\n"
        for proc in top_processes:
            output += f"• {proc['name']} (PID: {proc['pid']}) - CPU: {proc['cpu_percent']:.1f}%, RAM: {proc['memory_percent']:.1f}%\n"
        
        return {
            'success': True,
            'output': output,
            'process_count': len(processes),
            'top_processes': top_processes
        }
    except psutil.AccessDenied:
        return {'success': False, 'output': "❌ Permission denied accessing process information - elevated privileges required to view all processes"}
    except psutil.NoSuchProcess:
        return {'success': False, 'output': "❌ Process information unavailable - processes may have terminated during analysis"}
    except OSError as e:
        return {'success': False, 'output': f"❌ System error during process analysis: {str(e)} - unable to access process information"}
    except Exception as e:
        return {'success': False, 'output': f"❌ Process analysis failed: {str(e)} - unable to analyze running processes"}


def top_snapshot() -> Dict[str, Any]:
    """Real-time process snapshot"""
    try:
        system = platform.system().lower()
        
        if system == 'windows':
            command = ['tasklist', '/FO', 'CSV']
        else:
            command = ['top', '-b', '-n', '1']
        
        result = execute_command(command, timeout=30)
        
        if result['success']:
            lines = result['output'].split('\n')[:20]  # First 20 lines
            
            output = f"📊 Process Snapshot:\n"
            for line in lines:
                if line.strip():
                    output += f"• {line}\n"
            
            return {
                'success': True,
                'output': output,
                'process_count': len(lines)
            }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'output': f"❌ Process snapshot failed: {e}"}


def disk_usage() -> Dict[str, Any]:
    """Disk space usage by filesystem"""
    try:
        system = platform.system().lower()
        
        if system == 'windows':
            command = ['wmic', 'logicaldisk', 'get', 'size,freespace,caption']
        else:
            command = ['df', '-h']
        
        result = execute_command(command, timeout=30)
        
        if result['success']:
            output = f"💾 Disk Usage:\n{result['output']}"
            return {
                'success': True,
                'output': output,
                'raw_data': result['output']
            }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'output': f"❌ Disk usage failed: {e}"}


def memory_info() -> Dict[str, Any]:
    """Detailed memory usage"""
    try:
        system = platform.system().lower()
        
        if system == 'windows':
            command = ['wmic', 'OS', 'get', 'TotalVisibleMemorySize,FreePhysicalMemory']
        else:
            command = ['free', '-h']
        
        result = execute_command(command, timeout=30)
        
        if result['success']:
            output = f"🧠 Memory Information:\n{result['output']}"
            return {
                'success': True,
                'output': output,
                'raw_data': result['output']
            }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'output': f"❌ Memory info failed: {e}"}


def system_info() -> Dict[str, Any]:
    """System information"""
    try:
        command = ['uname', '-a']
        result = execute_command(command, timeout=30)
        
        if result['success']:
            output = f"💻 System Information:\n{result['output']}"
            return {
                'success': True,
                'output': output,
                'system_info': result['output']
            }
        else:
            # Fallback for Windows
            info = f"{platform.system()} {platform.release()} {platform.machine()}"
            return {
                'success': True,
                'output': f"💻 System Information:\n{info}",
                'system_info': info
            }
            
    except Exception as e:
        return {'success': False, 'output': f"❌ System info failed: {e}"}


def uptime_info() -> Dict[str, Any]:
    """System uptime and load"""
    try:
        command = ['uptime']
        result = execute_command(command, timeout=30)
        
        if result['success']:
            output = f"⏰ System Uptime:\n{result['output']}"
            return {
                'success': True,
                'output': output,
                'uptime_info': result['output']
            }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'output': f"❌ Uptime failed: {e}"}