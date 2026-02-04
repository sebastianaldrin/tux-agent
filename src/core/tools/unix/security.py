"""
Security Analysis Tools
SSL, vulnerability scanning, and security header checks
"""
import logging
import socket
import ssl
import requests
from typing import Dict, Any
from datetime import datetime

from ..base import execute_command, DEFAULT_WORKSPACE

logger = logging.getLogger(__name__)


def ssl_certificate_check(domain: str) -> Dict[str, Any]:
    """Check SSL certificate information"""
    try:
        if not domain:
            return {'success': False, 'output': "❌ Domain required"}
        
        # Remove protocol if present
        domain = domain.replace('https://', '').replace('http://', '').split('/')[0]
        
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                
                # Parse certificate info
                subject = dict(x[0] for x in cert['subject'])
                issuer = dict(x[0] for x in cert['issuer'])
                
                not_before = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
                not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                
                days_left = (not_after - datetime.now()).days
                
                output = f"🔒 SSL Certificate for {domain}:\n"
                output += f"• Subject: {subject.get('commonName', 'Unknown')}\n"
                output += f"• Issuer: {issuer.get('organizationName', 'Unknown')}\n"
                output += f"• Valid from: {not_before.strftime('%Y-%m-%d')}\n"
                output += f"• Valid until: {not_after.strftime('%Y-%m-%d')} ({days_left} days left)\n"
                output += f"• Protocol: {ssock.version()}"
                
                return {
                    'success': True,
                    'output': output,
                    'domain': domain,
                    'days_left': days_left,
                    'issuer': issuer.get('organizationName', 'Unknown'),
                    'valid_until': not_after.isoformat()
                }
                
    except socket.gaierror:
        return {'success': False, 'output': f"❌ Cannot resolve '{domain}' - domain may not exist or DNS issue"}
    except socket.timeout:
        return {'success': False, 'output': f"❌ Connection timeout to '{domain}:443' - server may be down or blocking connections"}
    except ssl.SSLError as e:
        return {'success': False, 'output': f"❌ SSL error for '{domain}': {str(e)} - certificate may be invalid or expired"}
    except ConnectionRefusedError:
        return {'success': False, 'output': f"❌ Connection refused to '{domain}:443' - HTTPS service may not be running"}
    except Exception as e:
        return {'success': False, 'output': f"❌ SSL check failed for '{domain}': {str(e)} - unable to verify certificate"}


def security_headers_check(url: str) -> Dict[str, Any]:
    """Check website security headers"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        response = requests.get(url, timeout=10, allow_redirects=True,
                              headers={'User-Agent': 'TuxAgent/1.0'})
        
        headers = response.headers
        security_headers = {
            'Strict-Transport-Security': headers.get('Strict-Transport-Security'),
            'Content-Security-Policy': headers.get('Content-Security-Policy'),
            'X-Frame-Options': headers.get('X-Frame-Options'),
            'X-Content-Type-Options': headers.get('X-Content-Type-Options'),
            'Referrer-Policy': headers.get('Referrer-Policy')
        }
        
        output = f"🛡️ Security Headers for {url}:\n"
        for header, value in security_headers.items():
            status = "✅" if value else "❌"
            output += f"• {header}: {status} {value or 'Not set'}\n"
        
        return {
            'success': True,
            'output': output.strip(),
            'security_headers': security_headers,
            'url': url
        }
        
    except requests.exceptions.RequestException as e:
        return {'success': False, 'output': f"❌ Cannot access '{url}': {str(e)} - check URL or network connection"}
    except Exception as e:
        return {'success': False, 'output': f"❌ Security headers check failed for '{url}': {str(e)} - unable to analyze headers"}


def vulnerability_scan(target: str, workspace=DEFAULT_WORKSPACE, streaming_callback=None) -> Dict[str, Any]:
    """Basic vulnerability assessment with streaming progress"""
    try:
        if not target:
            return {'success': False, 'output': "❌ Target required"}
        
        # Use streaming-enabled shell command for long vulnerability scans
        from .system_tools import shell_command
        command = f"nmap -sV --script=vuln {target}"
        result = shell_command(command, workspace, streaming_callback)
        
        if result['success']:
            output = f"🔍 Vulnerability Scan for {target}:\n{result['raw_output'] if 'raw_output' in result else result['output']}"
            return {
                'success': True,
                'output': output,
                'target': target,
                'scan_result': result['raw_output'] if 'raw_output' in result else result['output']
            }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'output': f"❌ Vulnerability scan failed: {e}"}


def openssl_check(domain: str, port: str = "443") -> Dict[str, Any]:
    """OpenSSL certificate check"""
    try:
        if not domain:
            return {'success': False, 'output': "❌ Domain required"}
        
        # Clean domain
        domain = domain.replace('https://', '').replace('http://', '').split('/')[0]
        
        command = ['openssl', 's_client', '-connect', f'{domain}:{port}', '-servername', domain]
        result = execute_command(command, timeout=30, input_data='\n')
        
        if result['success'] or 'CONNECTED' in result['output']:
            output = f"🔐 OpenSSL Check for {domain}:{port}\n"
            
            # Extract key information
            lines = result['output'].split('\n')
            for line in lines:
                if 'subject=' in line or 'issuer=' in line or 'verify return:' in line:
                    output += f"• {line.strip()}\n"
            
            return {
                'success': True,
                'output': output,
                'domain': domain,
                'port': port
            }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'output': f"❌ OpenSSL check failed: {e}"}
