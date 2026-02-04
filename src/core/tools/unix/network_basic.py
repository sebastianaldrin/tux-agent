"""
Basic Network Tools
DNS, WHOIS, and website analysis tools
"""
import logging
from typing import Dict, Any
import requests
from bs4 import BeautifulSoup
import dns.resolver
import whois

logger = logging.getLogger(__name__)


def dns_lookup(domain: str) -> Dict[str, Any]:
    """DNS lookup for domain"""
    try:
        # Validate domain
        if not domain or len(domain) > 255:
            return {'success': False, 'output': "❌ Invalid domain - domain name required and must be under 255 characters"}
            
        # Get A records
        result = dns.resolver.resolve(domain, 'A')
        ips = [str(rdata) for rdata in result]
        
        return {
            'success': True,
            'output': f"🌐 {domain} resolves to: {', '.join(ips)}",
            'ips': ips,
            'domain': domain
        }
    except dns.resolver.NXDOMAIN:
        return {'success': False, 'output': f"❌ Domain '{domain}' does not exist - check spelling or try a different domain"}
    except dns.resolver.NoAnswer:
        return {'success': False, 'output': f"❌ No A records found for '{domain}' - domain exists but has no IP address assigned"}
    except dns.resolver.Timeout:
        return {'success': False, 'output': f"❌ DNS query timeout for '{domain}' - DNS server not responding, try again later"}
    except dns.resolver.NoNameservers:
        return {'success': False, 'output': f"❌ No nameservers available for '{domain}' - DNS configuration issue"}
    except Exception as e:
        return {'success': False, 'output': f"❌ DNS lookup failed for '{domain}': {str(e)} - check domain format or network connection"}


def whois_lookup(domain: str) -> Dict[str, Any]:
    """WHOIS lookup for domain"""
    try:
        # Validate domain
        if not domain or len(domain) > 255:
            return {'success': False, 'output': "❌ Invalid domain - domain name required and must be under 255 characters"}
            
        result = whois.whois(domain)
        registrar = getattr(result, 'registrar', 'Unknown')
        creation_date = getattr(result, 'creation_date', 'Unknown')
        
        return {
            'success': True,
            'output': f"📋 {domain}\n• Registrar: {registrar}\n• Created: {creation_date}",
            'registrar': registrar,
            'creation_date': str(creation_date),
            'domain': domain
        }
    except whois.parser.PywhoisError as e:
        if "No whois server" in str(e):
            return {'success': False, 'output': f"❌ WHOIS not available for '{domain}' - this domain extension doesn't support WHOIS queries"}
        else:
            return {'success': False, 'output': f"❌ WHOIS lookup failed for '{domain}': domain may not exist or WHOIS data unavailable"}
    except ConnectionError:
        return {'success': False, 'output': f"❌ Cannot connect to WHOIS server for '{domain}' - network connection issue, try again later"}
    except Exception as e:
        error_msg = str(e).lower()
        if "timeout" in error_msg:
            return {'success': False, 'output': f"❌ WHOIS query timeout for '{domain}' - server not responding, try again later"}
        elif "rate limit" in error_msg or "too many" in error_msg:
            return {'success': False, 'output': f"❌ WHOIS rate limited for '{domain}' - too many requests, wait a few minutes and try again"}
        else:
            return {'success': False, 'output': f"❌ WHOIS lookup failed for '{domain}': {str(e)} - check domain format or try again later"}


def analyze_website(url: str) -> Dict[str, Any]:
    """Simple website analysis"""
    try:
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        response = requests.get(url, timeout=10, allow_redirects=True, 
                              headers={'User-Agent': 'TuxAgent/1.0'})
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title = soup.find('title')
        title_text = title.get_text().strip() if title else "No title"
        
        # Get basic info
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', 'No description') if meta_desc else 'No description'
        
        return {
            'success': True,
            'output': f"🌐 Website Analysis: {url}\n• Title: {title_text}\n• Status: {response.status_code}\n• Description: {description}",
            'title': title_text,
            'status_code': response.status_code,
            'description': description,
            'url': url
        }
    except requests.exceptions.SSLError as e:
        if "IP address" in str(e) or "certificate verify failed" in str(e):
            return {'success': False, 'output': f"❌ SSL certificate error for '{url}' - if accessing by IP address, try using the domain name instead"}
        else:
            return {'success': False, 'output': f"❌ SSL certificate error for '{url}' - website may have invalid or expired certificate"}
    except requests.exceptions.ConnectionError as e:
        if "Connection refused" in str(e):
            return {'success': False, 'output': f"❌ Connection refused to '{url}' - server may be down or blocking connections"}
        elif "Name or service not known" in str(e) or "nodename nor servname" in str(e):
            return {'success': False, 'output': f"❌ Cannot resolve '{url}' - domain may not exist or DNS issue"}
        else:
            return {'success': False, 'output': f"❌ Cannot connect to '{url}' - network issue or server unreachable"}
    except requests.exceptions.Timeout:
        return {'success': False, 'output': f"❌ Connection timeout to '{url}' - server is slow to respond, try again later"}
    except requests.exceptions.TooManyRedirects:
        return {'success': False, 'output': f"❌ Too many redirects for '{url}' - website has redirect loop configuration issue"}
    except requests.exceptions.RequestException as e:
        return {'success': False, 'output': f"❌ Cannot access '{url}': {str(e)} - check URL format or network connection"}
    except Exception as e:
        return {'success': False, 'output': f"❌ Website analysis failed for '{url}': {str(e)} - unable to parse website content"}