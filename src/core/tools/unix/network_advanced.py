"""
Advanced Network Tools
Traceroute, dig, curl, ping, port scanning, and network connections
"""
import logging
import socket
from typing import Dict, Any

from ..base import execute_command, get_platform_command

logger = logging.getLogger(__name__)


def ping_host(host: str) -> Dict[str, Any]:
    """Ping network connectivity test"""
    try:
        if not host:
            return {'success': False, 'output': "❌ Host required"}
        
        # Clean host input
        host = host.replace('https://', '').replace('http://', '').split('/')[0]
        
        command = ['ping', '-c', '4', host] if get_platform_command('ping') == 'ping' else ['ping', '-n', '4', host]
        result = execute_command(command, timeout=30)
        
        if result['success']:
            output = f"🏓 Ping {host}:\n{result['output']}"
            return {
                'success': True,
                'output': output,
                'host': host
            }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'output': f"❌ Ping failed: {e}"}


def traceroute(host: str) -> Dict[str, Any]:
    """Trace network path to destination"""
    try:
        if not host:
            return {'success': False, 'output': "❌ Host required"}
        
        # Clean host input
        host = host.replace('https://', '').replace('http://', '').split('/')[0]
        
        cmd = get_platform_command('traceroute')
        command = [cmd, host]
        result = execute_command(command, timeout=60)
        
        if result['success']:
            output = f"🗺️ Route to {host}:\n{result['output']}"
            return {
                'success': True,
                'output': output,
                'host': host
            }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'output': f"❌ Traceroute failed: {e}"}


def port_scan(host: str, ports: str = "80,443,22,21,25,53,110,995,993,143") -> Dict[str, Any]:
    """Scan ports on target"""
    try:
        if not host:
            return {'success': False, 'output': "❌ Host required"}
        
        # Clean host input
        host = host.replace('https://', '').replace('http://', '').split('/')[0]
        
        # Parse ports
        port_list = [int(p.strip()) for p in ports.split(',')]
        
        open_ports = []
        closed_ports = []
        
        for port in port_list:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result == 0:
                    open_ports.append(port)
                else:
                    closed_ports.append(port)
            except:
                closed_ports.append(port)
        
        output = f"🔍 Port Scan for {host}:\n"
        if open_ports:
            output += f"• Open ports: {', '.join(map(str, open_ports))}\n"
        if closed_ports:
            output += f"• Closed/filtered: {', '.join(map(str, closed_ports))}"
        
        return {
            'success': True,
            'output': output,
            'host': host,
            'open_ports': open_ports,
            'closed_ports': closed_ports
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Port scan failed: {e}"}


def dig_lookup(domain: str, record_type: str = "A") -> Dict[str, Any]:
    """Advanced DNS lookup with dig"""
    try:
        if not domain:
            return {'success': False, 'output': "❌ Domain required"}
        
        command = ['dig', '+short', domain, record_type.upper()]
        result = execute_command(command, timeout=30)
        
        if result['success']:
            output = f"🔍 Dig lookup for {domain} ({record_type}):\n{result['output']}"
            return {
                'success': True,
                'output': output,
                'domain': domain,
                'record_type': record_type
            }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'output': f"❌ Dig lookup failed: {e}"}


def curl_request(url: str, method: str = "GET", headers: str = None, data: str = None) -> Dict[str, Any]:
    """HTTP request with curl"""
    try:
        if not url:
            return {'success': False, 'output': "❌ URL required"}
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        command = ['curl', '-s', '-X', method.upper(), url]
        
        if headers:
            for header in headers.split('\n'):
                if header.strip():
                    command.extend(['-H', header.strip()])
        
        if data and method.upper() in ['POST', 'PUT', 'PATCH']:
            command.extend(['-d', data])
        
        result = execute_command(command, timeout=30)
        
        if result['success']:
            output = f"🌐 HTTP {method} {url}:\n{result['output'][:500]}{'...' if len(result['output']) > 500 else ''}"
            return {
                'success': True,
                'output': output,
                'url': url,
                'method': method
            }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'output': f"❌ Curl request failed: {e}"}


def netstat_connections() -> Dict[str, Any]:
    """Show network connections"""
    try:
        command = ['netstat', '-tuln']
        result = execute_command(command, timeout=30)
        
        if result['success']:
            output = f"🔗 Network Connections:\n{result['output']}"
            return {
                'success': True,
                'output': output
            }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'output': f"❌ Netstat failed: {e}"}


def arp_table() -> Dict[str, Any]:
    """Show ARP table (local network discovery)"""
    try:
        command = ['arp', '-a']
        result = execute_command(command, timeout=30)
        
        if result['success']:
            output = f"📡 ARP Table:\n{result['output']}"
            return {
                'success': True,
                'output': output
            }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'output': f"❌ ARP table failed: {e}"}


def view_source(url: str, element_type: str = "script") -> Dict[str, Any]:
    """Extract specific code elements from website source"""
    try:
        if not url:
            return {'success': False, 'output': "❌ URL required"}
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        command = ['curl', '-s', url]
        result = execute_command(command, timeout=30)
        
        if result['success']:
            source = result['output']
            
            if element_type.lower() == 'script':
                import re
                scripts = re.findall(r'<script[^>]*>(.*?)</script>', source, re.DOTALL)
                output = f"📄 Scripts from {url}:\n"
                for i, script in enumerate(scripts[:5]):
                    output += f"Script {i+1}: {script[:100]}...\n"
            else:
                output = f"📄 Source from {url}:\n{source[:1000]}{'...' if len(source) > 1000 else ''}"
            
            return {
                'success': True,
                'output': output,
                'url': url
            }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'output': f"❌ View source failed: {e}"}


def nslookup_query(domain: str, record_type: str = "A") -> Dict[str, Any]:
    """DNS lookup with nslookup"""
    try:
        if not domain:
            return {'success': False, 'output': "❌ Domain required"}
        
        command = ['nslookup', '-type=' + record_type.upper(), domain]
        result = execute_command(command, timeout=30)
        
        if result['success']:
            output = f"🔍 NSLookup for {domain} ({record_type}):\n{result['output']}"
            return {
                'success': True,
                'output': output,
                'domain': domain,
                'record_type': record_type
            }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'output': f"❌ NSLookup failed: {e}"}


def network_speed_test(streaming_callback=None) -> Dict[str, Any]:
    """Test internet connection speed with streaming progress"""
    try:
        import speedtest
        import asyncio
        
        def safe_callback(message):
            """Thread-safe callback for speedtest progress"""
            if streaming_callback:
                try:
                    # Schedule callback on main thread if possible
                    loop = asyncio.get_running_loop()
                    loop.call_soon_threadsafe(lambda: asyncio.create_task(streaming_callback(message)))
                except RuntimeError:
                    # No running event loop, skip callback
                    pass
        
        output = "🚀 Network Speed Test:\n"
        
        if streaming_callback:
            safe_callback("⏱️ Network speed test starting...\n💡 This may take 30-60 seconds\n\n")
        
        st = speedtest.Speedtest()
        
        if streaming_callback:
            safe_callback("🔍 Finding best server...\n")
        
        st.get_best_server()
        server_info = st.results.server
        
        if streaming_callback:
            safe_callback(f"📡 Testing with: {server_info['name']} ({server_info['country']})\n")
        
        # Download test
        if streaming_callback:
            safe_callback("⬇️ Testing download speed...\n")
            
        download_speed = st.download() / 1_000_000  # Convert to Mbps
        
        if streaming_callback:
            safe_callback(f"⬇️ Download: {download_speed:.1f} Mbps\n")
        
        # Upload test
        if streaming_callback:
            safe_callback("⬆️ Testing upload speed...\n")
            
        upload_speed = st.upload() / 1_000_000  # Convert to Mbps
        
        # Ping test
        ping = st.results.ping
        
        output += f"• Server: {server_info['name']} ({server_info['country']})\n"
        output += f"• Download: {download_speed:.1f} Mbps\n"
        output += f"• Upload: {upload_speed:.1f} Mbps\n"
        output += f"• Ping: {ping:.1f} ms"
        
        if streaming_callback:
            safe_callback(f"✅ Speed test completed!\n⬇️ Download: {download_speed:.1f} Mbps | ⬆️ Upload: {upload_speed:.1f} Mbps | 📶 Ping: {ping:.1f} ms\n\n")
        
        return {
            'success': True,
            'output': output,
            'download_mbps': download_speed,
            'upload_mbps': upload_speed,
            'ping_ms': ping
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Speed test failed: {e}"}