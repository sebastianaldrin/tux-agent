"""
Power Monitoring Tools for Unix/Linux Systems
Provides battery, CPU frequency, temperature, and power state monitoring
"""
import logging
import platform
import os
import glob
from typing import Dict, Any, Optional, List
import psutil
from ..base import execute_command

logger = logging.getLogger(__name__)


def battery_monitor() -> Dict[str, Any]:
    """Monitor battery status, charge level, health, and power consumption"""
    try:
        # Primary: psutil cross-platform battery info
        battery = psutil.sensors_battery()
        if battery:
            status = "Charging" if battery.power_plugged else "Discharging"
            time_remaining = None
            if battery.secsleft != psutil.POWER_TIME_UNLIMITED and battery.secsleft > 0:
                hours = battery.secsleft // 3600
                minutes = (battery.secsleft % 3600) // 60
                time_remaining = f"{hours}h {minutes}m"
            
            result = {
                'success': True,
                'output': f"🔋 Battery Monitor\n• Status: {status}\n• Charge: {battery.percent}%\n• Power Connected: {'Yes' if battery.power_plugged else 'No'}",
                'battery_percent': battery.percent,
                'power_plugged': battery.power_plugged,
                'status': status,
                'time_remaining': time_remaining,
                'platform': 'unix'
            }
            
            if time_remaining:
                result['output'] += f"\n• Time Remaining: {time_remaining}"
            
            # Enhanced Unix-specific battery information
            try:
                # Try to get additional battery details from /sys filesystem
                battery_paths = glob.glob('/sys/class/power_supply/BAT*')
                if battery_paths:
                    battery_path = battery_paths[0]
                    
                    # Read battery health information
                    try:
                        with open(f"{battery_path}/energy_full", 'r') as f:
                            energy_full = int(f.read().strip())
                        with open(f"{battery_path}/energy_full_design", 'r') as f:
                            energy_design = int(f.read().strip())
                        
                        health_percent = (energy_full / energy_design) * 100
                        result['battery_health'] = round(health_percent, 1)
                        result['output'] += f"\n• Health: {health_percent:.1f}%"
                        
                    except (FileNotFoundError, ValueError, ZeroDivisionError):
                        pass
                    
                    # Read cycle count if available
                    try:
                        with open(f"{battery_path}/cycle_count", 'r') as f:
                            cycle_count = int(f.read().strip())
                        result['cycle_count'] = cycle_count
                        result['output'] += f"\n• Cycle Count: {cycle_count}"
                    except (FileNotFoundError, ValueError):
                        pass
                        
            except Exception as e:
                logger.debug(f"Failed to read extended battery info: {e}")
            
            return result
        
        # Fallback: acpi command
        acpi_result = execute_command(['acpi', '-b'])
        if acpi_result['success']:
            acpi_output = acpi_result['output']
            
            # Parse acpi output
            if 'Battery' in acpi_output:
                return {
                    'success': True,
                    'output': f"🔋 Battery Monitor\n• ACPI Info: {acpi_output.strip()}",
                    'acpi_data': acpi_output.strip(),
                    'platform': 'unix'
                }
        
        # Final fallback: Check if power supply exists
        if os.path.exists('/sys/class/power_supply/'):
            return {
                'success': False,
                'output': "❌ Battery information unavailable - device may not have a battery or battery driver not loaded"
            }
        
        return {
            'success': False,
            'output': "❌ No battery detected - device appears to be a desktop system"
        }
        
    except psutil.AccessDenied:
        return {
            'success': False,
            'output': "❌ Permission denied accessing battery information - elevated privileges may be required"
        }
    except Exception as e:
        logger.error(f"Battery monitoring error: {e}")
        return {
            'success': False,
            'output': f"❌ Battery monitoring failed: {str(e)} - unexpected error during monitoring"
        }


def cpu_frequency_monitor() -> Dict[str, Any]:
    """Monitor CPU frequency, scaling governor, and performance states"""
    try:
        # Primary: psutil CPU frequency info
        freq_info = psutil.cpu_freq(percpu=True)
        system_freq = psutil.cpu_freq()
        
        if system_freq:
            result = {
                'success': True,
                'output': f"⚡ CPU Frequency Monitor\n• Current: {system_freq.current:.0f}MHz\n• Range: {system_freq.min:.0f}-{system_freq.max:.0f}MHz",
                'current_freq': system_freq.current,
                'min_freq': system_freq.min,
                'max_freq': system_freq.max,
                'platform': 'unix'
            }
            
            if freq_info:
                result['per_cpu_freq'] = [
                    {
                        'cpu': i,
                        'current': f.current,
                        'min': f.min,
                        'max': f.max
                    } for i, f in enumerate(freq_info)
                ]
                result['output'] += f"\n• CPU Cores: {len(freq_info)}"
            
            # Enhanced Unix-specific CPU information
            try:
                # Get scaling governor information
                governor_paths = glob.glob('/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor')
                if governor_paths:
                    with open(governor_paths[0], 'r') as f:
                        governor = f.read().strip()
                    result['scaling_governor'] = governor
                    result['output'] += f"\n• Governor: {governor}"
                    
                    # Get available governors
                    try:
                        available_path = governor_paths[0].replace('scaling_governor', 'scaling_available_governors')
                        with open(available_path, 'r') as f:
                            available_governors = f.read().strip().split()
                        result['available_governors'] = available_governors
                    except FileNotFoundError:
                        pass
                
                # Get CPU temperature if available for context
                try:
                    temps = psutil.sensors_temperatures()
                    if temps and 'coretemp' in temps:
                        cpu_temp = temps['coretemp'][0].current
                        result['cpu_temperature'] = cpu_temp
                        result['output'] += f"\n• CPU Temp: {cpu_temp:.1f}°C"
                except (AttributeError, IndexError, KeyError):
                    pass
                    
            except Exception as e:
                logger.debug(f"Failed to read extended CPU frequency info: {e}")
            
            return result
        
        # Fallback: lscpu command
        lscpu_result = execute_command(['lscpu'])
        if lscpu_result['success']:
            lscpu_output = lscpu_result['output']
            
            # Parse basic CPU information
            return {
                'success': True,
                'output': f"⚡ CPU Frequency Monitor\n• System Info:\n{lscpu_output[:500]}...",
                'lscpu_data': lscpu_output,
                'platform': 'unix'
            }
        
        # Final fallback: /proc/cpuinfo
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
            
            # Extract basic frequency information
            lines = cpuinfo.split('\n')
            cpu_mhz_lines = [line for line in lines if 'cpu MHz' in line.lower()]
            if cpu_mhz_lines:
                freq_str = cpu_mhz_lines[0].split(':')[1].strip()
                frequency = float(freq_str)
                
                return {
                    'success': True,
                    'output': f"⚡ CPU Frequency Monitor\n• Current: {frequency:.0f}MHz\n• Source: /proc/cpuinfo",
                    'current_freq': frequency,
                    'platform': 'unix'
                }
        except Exception as e:
            logger.debug(f"Failed to read /proc/cpuinfo: {e}")
        
        return {
            'success': False,
            'output': "❌ CPU frequency information unavailable - frequency scaling may not be supported"
        }
        
    except Exception as e:
        logger.error(f"CPU frequency monitoring error: {e}")
        return {
            'success': False,
            'output': f"❌ CPU frequency monitoring failed: {str(e)} - unexpected error during monitoring"
        }


def temperature_monitor() -> Dict[str, Any]:
    """Monitor system temperatures from CPU, GPU, and other sensors"""
    try:
        # Primary: psutil temperature sensors (Linux only)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                output_lines = ["🌡️ Temperature Monitor"]
                temp_data = {}
                
                for sensor_name, sensor_list in temps.items():
                    temp_data[sensor_name] = []
                    for sensor in sensor_list:
                        temp_info = {
                            'label': sensor.label or 'Unknown',
                            'current': sensor.current,
                            'high': sensor.high,
                            'critical': sensor.critical
                        }
                        temp_data[sensor_name].append(temp_info)
                        
                        # Format temperature display
                        temp_str = f"• {sensor_name}"
                        if sensor.label:
                            temp_str += f" ({sensor.label})"
                        temp_str += f": {sensor.current:.1f}°C"
                        
                        if sensor.high:
                            temp_str += f" (High: {sensor.high:.1f}°C)"
                        if sensor.critical:
                            temp_str += f" (Critical: {sensor.critical:.1f}°C)"
                            
                        output_lines.append(temp_str)
                
                return {
                    'success': True,
                    'output': '\n'.join(output_lines),
                    'temperature_data': temp_data,
                    'platform': 'unix'
                }
        except AttributeError:
            # psutil.sensors_temperatures() not available on this platform
            pass
        
        # Fallback: sensors command
        sensors_result = execute_command(['sensors'])
        if sensors_result['success']:
            sensors_output = sensors_result['output']
            
            # Parse sensors output for key temperatures
            lines = sensors_output.split('\n')
            temp_lines = []
            for line in lines:
                if '°C' in line and ('Core' in line or 'temp' in line.lower() or 'CPU' in line):
                    temp_lines.append(line.strip())
            
            if temp_lines:
                output = "🌡️ Temperature Monitor\n" + '\n'.join(f"• {line}" for line in temp_lines[:10])
                return {
                    'success': True,
                    'output': output,
                    'sensors_data': sensors_output,
                    'platform': 'unix'
                }
        
        # Fallback: Direct thermal zone reading
        thermal_zones = glob.glob('/sys/class/thermal/thermal_zone*/temp')
        if thermal_zones:
            output_lines = ["🌡️ Temperature Monitor"]
            temp_data = []
            
            for i, zone_path in enumerate(thermal_zones[:10]):  # Limit to first 10 zones
                try:
                    with open(zone_path, 'r') as f:
                        temp_millic = int(f.read().strip())
                    temp_celsius = temp_millic / 1000.0
                    
                    # Try to get zone type
                    zone_type = "Unknown"
                    try:
                        type_path = zone_path.replace('/temp', '/type')
                        with open(type_path, 'r') as f:
                            zone_type = f.read().strip()
                    except FileNotFoundError:
                        pass
                    
                    temp_data.append({
                        'zone': i,
                        'type': zone_type,
                        'temperature': temp_celsius
                    })
                    
                    output_lines.append(f"• Zone {i} ({zone_type}): {temp_celsius:.1f}°C")
                    
                except (ValueError, FileNotFoundError):
                    continue
            
            if temp_data:
                return {
                    'success': True,
                    'output': '\n'.join(output_lines),
                    'thermal_zones': temp_data,
                    'platform': 'unix'
                }
        
        return {
            'success': False,
            'output': "❌ Temperature monitoring unavailable - no thermal sensors detected or lm-sensors not installed"
        }
        
    except Exception as e:
        logger.error(f"Temperature monitoring error: {e}")
        return {
            'success': False,
            'output': f"❌ Temperature monitoring failed: {str(e)} - unexpected error during monitoring"
        }


def power_state_monitor() -> Dict[str, Any]:
    """Monitor power management states, plans, and energy consumption"""
    try:
        output_lines = ["🔌 Power State Monitor"]
        power_data = {}
        
        # Check system power state capabilities
        try:
            if os.path.exists('/sys/power/state'):
                with open('/sys/power/state', 'r') as f:
                    available_states = f.read().strip().split()
                power_data['available_states'] = available_states
                output_lines.append(f"• Available States: {', '.join(available_states)}")
        except Exception as e:
            logger.debug(f"Failed to read power states: {e}")
        
        # Check CPU scaling governor (power management)
        try:
            governor_paths = glob.glob('/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor')
            if governor_paths:
                with open(governor_paths[0], 'r') as f:
                    current_governor = f.read().strip()
                power_data['cpu_governor'] = current_governor
                output_lines.append(f"• CPU Governor: {current_governor}")
                
                # Get available governors
                try:
                    available_path = governor_paths[0].replace('scaling_governor', 'scaling_available_governors')
                    with open(available_path, 'r') as f:
                        available_governors = f.read().strip().split()
                    power_data['available_governors'] = available_governors
                    output_lines.append(f"• Available Governors: {', '.join(available_governors)}")
                except FileNotFoundError:
                    pass
        except Exception as e:
            logger.debug(f"Failed to read CPU governor: {e}")
        
        # Check power supply information
        try:
            ac_adapters = glob.glob('/sys/class/power_supply/A[CD]*')
            for adapter in ac_adapters:
                try:
                    online_path = os.path.join(adapter, 'online')
                    if os.path.exists(online_path):
                        with open(online_path, 'r') as f:
                            online = f.read().strip()
                        adapter_name = os.path.basename(adapter)
                        status = "Connected" if online == '1' else "Disconnected"
                        power_data[f'{adapter_name}_status'] = status
                        output_lines.append(f"• {adapter_name}: {status}")
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Failed to read power supply info: {e}")
        
        # Try systemctl for power management services
        try:
            systemctl_result = execute_command(['systemctl', 'status', 'systemd-logind', '--no-pager', '--lines=0'])
            if systemctl_result['success']:
                if 'active (running)' in systemctl_result['output']:
                    output_lines.append("• Power Management: Active (systemd-logind)")
                    power_data['power_management'] = 'systemd-logind'
        except Exception as e:
            logger.debug(f"Failed to check systemctl: {e}")
        
        # Get load average as power consumption indicator
        try:
            load_avg = os.getloadavg()
            power_data['load_average'] = {
                '1min': load_avg[0],
                '5min': load_avg[1],
                '15min': load_avg[2]
            }
            output_lines.append(f"• Load Average: {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}")
        except Exception as e:
            logger.debug(f"Failed to get load average: {e}")
        
        # Check if running on laptop (has battery)
        try:
            battery = psutil.sensors_battery()
            if battery:
                power_data['device_type'] = 'laptop'
                output_lines.append("• Device Type: Laptop (battery detected)")
            else:
                power_data['device_type'] = 'desktop'
                output_lines.append("• Device Type: Desktop (no battery)")
        except Exception:
            pass
        
        if len(output_lines) > 1:  # Has actual data beyond header
            return {
                'success': True,
                'output': '\n'.join(output_lines),
                'power_state_data': power_data,
                'platform': 'unix'
            }
        
        return {
            'success': False,
            'output': "❌ Power state information unavailable - power management interfaces not accessible"
        }
        
    except Exception as e:
        logger.error(f"Power state monitoring error: {e}")
        return {
            'success': False,
            'output': f"❌ Power state monitoring failed: {str(e)} - unexpected error during monitoring"
        }