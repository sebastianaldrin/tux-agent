"""
Web Analysis Tools
Page performance testing, link checking, hosting provider lookup
"""
import logging
import requests
import time
from bs4 import BeautifulSoup
from typing import Dict, Any

logger = logging.getLogger(__name__)


def page_performance_test(url: str) -> Dict[str, Any]:
    """Test webpage loading performance"""
    try:
        if not url:
            return {'success': False, 'output': "❌ URL required"}
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        start_time = time.time()
        response = requests.get(url, timeout=30, headers={'User-Agent': 'TuxAgent/1.0'})
        load_time = time.time() - start_time
        
        size_kb = len(response.content) / 1024
        
        output = f"🏁 Performance Test for {url}:\n"
        output += f"• Load time: {load_time:.2f} seconds\n"
        output += f"• Status code: {response.status_code}\n"
        output += f"• Page size: {size_kb:.1f} KB\n"
        output += f"• Response headers: {len(response.headers)} headers"
        
        return {
            'success': True,
            'output': output,
            'load_time': load_time,
            'status_code': response.status_code,
            'size_kb': size_kb
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Performance test failed: {e}"}


def link_checker(url: str) -> Dict[str, Any]:
    """Check if links on a webpage are working"""
    try:
        if not url:
            return {'success': False, 'output': "❌ URL required"}
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        response = requests.get(url, timeout=30, headers={'User-Agent': 'TuxAgent/1.0'})
        soup = BeautifulSoup(response.content, 'html.parser')
        
        links = soup.find_all('a', href=True)
        
        working_links = 0
        broken_links = 0
        checked_links = []
        
        for link in links[:10]:  # Check first 10 links
            href = link['href']
            if href.startswith('http'):
                try:
                    link_response = requests.head(href, timeout=10)
                    if link_response.status_code < 400:
                        working_links += 1
                        status = "✅ Working"
                    else:
                        broken_links += 1
                        status = f"❌ Broken ({link_response.status_code})"
                except:
                    broken_links += 1
                    status = "❌ Broken (No response)"
                
                checked_links.append(f"{status} - {href[:50]}...")
        
        output = f"🔗 Link Check for {url}:\n"
        output += f"• Total links found: {len(links)}\n"
        output += f"• Working: {working_links}, Broken: {broken_links}\n\n"
        output += "\n".join(checked_links)
        
        return {
            'success': True,
            'output': output,
            'total_links': len(links),
            'working_links': working_links,
            'broken_links': broken_links
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Link checker failed: {e}"}


def hosting_provider_lookup(domain: str) -> Dict[str, Any]:
    """Lookup hosting provider information"""
    try:
        if not domain:
            return {'success': False, 'output': "❌ Domain required"}
        
        # Simple hosting provider detection based on nameservers
        import dns.resolver
        
        try:
            ns_records = dns.resolver.resolve(domain, 'NS')
            nameservers = [str(ns) for ns in ns_records]
            
            # Detect common hosting providers
            provider = "Unknown"
            for ns in nameservers:
                ns_lower = ns.lower()
                if 'cloudflare' in ns_lower:
                    provider = "Cloudflare"
                elif 'amazonaws' in ns_lower:
                    provider = "Amazon AWS"
                elif 'googledomains' in ns_lower:
                    provider = "Google Domains"
                elif 'godaddy' in ns_lower:
                    provider = "GoDaddy"
                elif 'namecheap' in ns_lower:
                    provider = "Namecheap"
                
                if provider != "Unknown":
                    break
            
            output = f"🏠 Hosting Provider for {domain}:\n"
            output += f"• Detected provider: {provider}\n"
            output += f"• Nameservers: {', '.join(nameservers)}"
            
            return {
                'success': True,
                'output': output,
                'domain': domain,
                'provider': provider,
                'nameservers': nameservers
            }
            
        except Exception as e:
            return {'success': False, 'output': f"❌ DNS lookup failed: {e}"}
            
    except Exception as e:
        return {'success': False, 'output': f"❌ Hosting lookup failed: {e}"}
