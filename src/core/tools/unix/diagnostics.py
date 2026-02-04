"""
Network Diagnostics Tools
Advanced network troubleshooting and connectivity testing
"""
import logging
import speedtest
from typing import Dict, Any

from ..base import execute_command

logger = logging.getLogger(__name__)


def internet_connectivity_test() -> Dict[str, Any]:
    """Test internet connectivity"""
    try:
        # Test multiple endpoints
        test_hosts = ['8.8.8.8', 'google.com', 'cloudflare.com']
        results = []
        
        for host in test_hosts:
            command = ['ping', '-c', '1', host]
            result = execute_command(command, timeout=10)
            results.append({
                'host': host,
                'success': result['success']
            })
        
        successful_tests = sum(1 for r in results if r['success'])
        
        output = f"🌐 Internet Connectivity Test:\n"
        for result in results:
            status = "✅" if result['success'] else "❌"
            output += f"• {status} {result['host']}\n"
        
        output += f"\nConnectivity: {successful_tests}/{len(test_hosts)} tests passed"
        
        return {
            'success': True,
            'output': output,
            'successful_tests': successful_tests,
            'total_tests': len(test_hosts)
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Connectivity test failed: {e}"}


def network_speed_diagnosis() -> Dict[str, Any]:
    """Test network speed"""
    try:
        output = "📊 Network Speed Test:\n"
        output += "• Testing download/upload speeds...\n"
        
        st = speedtest.Speedtest()
        st.get_best_server()
        
        # Download test
        download_speed = st.download() / 1_000_000  # Convert to Mbps
        
        # Upload test
        upload_speed = st.upload() / 1_000_000  # Convert to Mbps
        
        # Ping test
        ping = st.results.ping
        
        output += f"• Download: {download_speed:.1f} Mbps\n"
        output += f"• Upload: {upload_speed:.1f} Mbps\n"
        output += f"• Ping: {ping:.1f} ms"
        
        return {
            'success': True,
            'output': output,
            'download_mbps': download_speed,
            'upload_mbps': upload_speed,
            'ping_ms': ping
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Speed test failed: {e}"}


def domain_health_check(domain: str) -> Dict[str, Any]:
    """Comprehensive domain health check"""
    try:
        if not domain:
            return {'success': False, 'output': "❌ Domain required"}
        
        output = f"🏥 Domain Health Check for {domain}:\n"
        
        # DNS check
        import dns.resolver
        try:
            dns.resolver.resolve(domain, 'A')
            output += "• ✅ DNS resolution: Working\n"
            dns_status = True
        except:
            output += "• ❌ DNS resolution: Failed\n"
            dns_status = False
        
        # HTTP check
        import requests
        try:
            response = requests.get(f"https://{domain}", timeout=10)
            output += f"• ✅ HTTPS: {response.status_code}\n"
            https_status = True
        except:
            output += "• ❌ HTTPS: Failed\n"
            https_status = False
        
        # SSL check
        try:
            import ssl
            import socket
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    output += "• ✅ SSL Certificate: Valid\n"
                    ssl_status = True
        except:
            output += "• ❌ SSL Certificate: Invalid\n"
            ssl_status = False
        
        overall_health = "Healthy" if all([dns_status, https_status, ssl_status]) else "Issues detected"
        output += f"\nOverall health: {overall_health}"
        
        return {
            'success': True,
            'output': output,
            'domain': domain,
            'dns_status': dns_status,
            'https_status': https_status,
            'ssl_status': ssl_status
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Domain health check failed: {e}"}


def network_troubleshoot_wizard() -> Dict[str, Any]:
    """Network troubleshooting wizard"""
    try:
        output = "🔧 Network Troubleshooting Wizard:\n\n"
        
        # Step 1: Local connectivity
        output += "Step 1: Testing local connectivity...\n"
        local_result = execute_command(['ping', '-c', '1', '127.0.0.1'], timeout=5)
        if local_result['success']:
            output += "• ✅ Local loopback: Working\n"
        else:
            output += "• ❌ Local loopback: Failed\n"
        
        # Step 2: Gateway connectivity
        output += "\nStep 2: Testing gateway connectivity...\n"
        try:
            import subprocess
            route_result = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=5)
            if route_result.returncode == 0:
                output += "• ✅ Routing table: Accessible\n"
            else:
                output += "• ❌ Routing table: Issues detected\n"
        except:
            output += "• ❌ Routing table: Cannot access\n"
        
        # Step 3: DNS connectivity
        output += "\nStep 3: Testing DNS...\n"
        dns_result = execute_command(['nslookup', 'google.com'], timeout=10)
        if dns_result['success']:
            output += "• ✅ DNS resolution: Working\n"
        else:
            output += "• ❌ DNS resolution: Failed\n"
        
        # Step 4: Internet connectivity
        output += "\nStep 4: Testing internet...\n"
        internet_result = execute_command(['ping', '-c', '1', '8.8.8.8'], timeout=10)
        if internet_result['success']:
            output += "• ✅ Internet connectivity: Working\n"
        else:
            output += "• ❌ Internet connectivity: Failed\n"
        
        output += "\n📋 Troubleshooting complete!"
        
        return {
            'success': True,
            'output': output
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Network troubleshooting failed: {e}"}


def wifi_analyzer() -> Dict[str, Any]:
    """Analyze WiFi networks"""
    try:
        output = "📶 WiFi Network Analysis:\n"
        
        # Use iwlist to scan for networks (Linux)
        command = ['iwlist', 'scan']
        result = execute_command(command, timeout=30)
        
        if result['success']:
            output += result['output'][:1000] + "..." if len(result['output']) > 1000 else result['output']
        else:
            # Fallback - just show interface info
            command = ['iwconfig']
            result = execute_command(command, timeout=10)
            if result['success']:
                output += f"Network interfaces:\n{result['output']}"
            else:
                output += "• WiFi scanning not available on this system"
        
        return {
            'success': True,
            'output': output
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ WiFi analysis failed: {e}"}