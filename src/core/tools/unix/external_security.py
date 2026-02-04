"""
External Security Testing Tools
Subdomain enumeration, technology detection, vulnerability scanning
"""
import logging
import requests
import dns.resolver
from typing import Dict, Any, List

from ..base import execute_command

logger = logging.getLogger(__name__)


def external_subdomain_enum(domain: str) -> Dict[str, Any]:
    """Enumerate subdomains"""
    try:
        if not domain:
            return {'success': False, 'output': "❌ Domain required"}
        
        # Common subdomain list
        common_subdomains = [
            'www', 'mail', 'ftp', 'admin', 'api', 'blog', 'shop', 'test', 'dev',
            'staging', 'cdn', 'assets', 'images', 'static', 'support', 'help'
        ]
        
        found_subdomains = []
        
        output = f"🔍 Subdomain Enumeration for {domain}:\n"
        
        for subdomain in common_subdomains:
            full_domain = f"{subdomain}.{domain}"
            try:
                dns.resolver.resolve(full_domain, 'A')
                found_subdomains.append(full_domain)
                output += f"• ✅ {full_domain}\n"
            except:
                pass  # Subdomain doesn't exist
        
        if not found_subdomains:
            output += "• No common subdomains found\n"
        
        output += f"\nFound {len(found_subdomains)} subdomains"
        
        return {
            'success': True,
            'output': output,
            'domain': domain,
            'subdomains': found_subdomains
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Subdomain enumeration failed: {e}"}


def external_tech_stack_detection(url: str) -> Dict[str, Any]:
    """Detect website technology stack"""
    try:
        if not url:
            return {'success': False, 'output': "❌ URL required"}
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        response = requests.get(url, timeout=10, headers={'User-Agent': 'TuxAgent/1.0'})
        headers = response.headers
        content = response.text
        
        technologies = []
        confidence_scores = {}
        
        # Parse HTML for meta tags
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        
        # Check meta generator tag first (most reliable)
        generator_tag = soup.find('meta', attrs={'name': 'generator'})
        if generator_tag and generator_tag.get('content'):
            generator_content = generator_tag['content']
            technologies.append(f"Generator: {generator_content}")
            confidence_scores['generator'] = 100  # Meta generator is definitive
            
            # Parse specific frameworks from generator
            gen_lower = generator_content.lower()
            if 'gatsby' in gen_lower:
                technologies.append("Framework: Gatsby (React-based)")
                confidence_scores['gatsby'] = 100
            elif 'next.js' in gen_lower:
                technologies.append("Framework: Next.js (React-based)")
                confidence_scores['nextjs'] = 100
            elif 'nuxt' in gen_lower:
                technologies.append("Framework: Nuxt.js (Vue-based)")
                confidence_scores['nuxtjs'] = 100
        
        # Check server header
        server = headers.get('Server', '')
        if server:
            technologies.append(f"Server: {server}")
        
        # Check for common technologies in headers
        if 'X-Powered-By' in headers:
            technologies.append(f"Powered by: {headers['X-Powered-By']}")
        
        # Check for hosting providers in headers
        if 'x-vercel-id' in headers or 'x-vercel-cache' in headers:
            technologies.append("Hosting: Vercel")
            confidence_scores['vercel'] = 90
        elif 'x-served-by' in headers and 'cache-' in headers.get('x-served-by', ''):
            technologies.append("CDN: Fastly")
            confidence_scores['fastly'] = 80
        elif 'cf-ray' in headers:
            technologies.append("CDN: Cloudflare")
            confidence_scores['cloudflare'] = 90
        
        # Check content for frameworks (only if not already detected via meta)
        content_lower = content.lower()
        
        # CMS detection
        if 'wordpress' in content_lower or 'wp-content' in content_lower:
            technologies.append("CMS: WordPress")
            confidence_scores['wordpress'] = 85
        elif 'drupal' in content_lower:
            technologies.append("CMS: Drupal")
            confidence_scores['drupal'] = 70
        elif 'joomla' in content_lower:
            technologies.append("CMS: Joomla")
            confidence_scores['joomla'] = 70
        
        # Frontend framework detection (with hierarchy awareness)
        # Check if already detected specific framework via meta
        has_specific_framework = any('gatsby' in t.lower() or 'next.js' in t.lower() or 'nuxt' in t.lower() for t in technologies)
        
        if not has_specific_framework:
            # Only detect base frameworks if no specific framework found
            if 'react' in content_lower or '__react' in content_lower:
                technologies.append("Frontend: React")
                confidence_scores['react'] = 60  # Lower confidence for content-based detection
            elif 'angular' in content_lower or 'ng-' in content_lower:
                technologies.append("Frontend: Angular")
                confidence_scores['angular'] = 60
            elif 'vue' in content_lower or 'v-' in content_lower:
                technologies.append("Frontend: Vue.js")
                confidence_scores['vue'] = 60
        
        # Check for specific Gatsby indicators
        if 'gatsby' in content_lower or 'gatsby-' in content_lower:
            if not any('gatsby' in t.lower() for t in technologies):
                technologies.append("Framework: Gatsby (React-based)")
                confidence_scores['gatsby'] = 80
        
        # Check for libraries
        if 'jquery' in content_lower:
            technologies.append("Library: jQuery")
            confidence_scores['jquery'] = 70
        
        # Check for CSS frameworks
        if 'bootstrap' in content_lower:
            technologies.append("CSS Framework: Bootstrap")
            confidence_scores['bootstrap'] = 70
        elif 'tailwind' in content_lower:
            technologies.append("CSS Framework: Tailwind CSS")
            confidence_scores['tailwind'] = 70
        
        # Check for build tools in HTML comments
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and '<!--' in text):
            if 'webpack' in comment.lower():
                technologies.append("Build Tool: Webpack")
                confidence_scores['webpack'] = 60
            elif 'vite' in comment.lower():
                technologies.append("Build Tool: Vite")
                confidence_scores['vite'] = 60
        
        # Format output with confidence indicators
        output = f"🔬 Technology Stack for {url}:\n"
        if technologies:
            # Sort by confidence (highest first)
            tech_with_confidence = []
            for tech in technologies:
                # Extract key for confidence lookup
                tech_key = tech.split(':')[1].strip().lower() if ':' in tech else tech.lower()
                confidence = confidence_scores.get(tech_key, 50)
                tech_with_confidence.append((tech, confidence))
            
            tech_with_confidence.sort(key=lambda x: x[1], reverse=True)
            
            for tech, confidence in tech_with_confidence:
                if confidence >= 90:
                    output += f"• {tech} ✅ (high confidence)\n"
                elif confidence >= 70:
                    output += f"• {tech} ✓ (good confidence)\n"
                else:
                    output += f"• {tech} ? (detected)\n"
        else:
            output += "• No obvious technologies detected\n"
        
        # Add note about detection method
        if generator_tag:
            output += f"\n📌 Note: Primary detection via meta generator tag"
        
        return {
            'success': True,
            'output': output,
            'url': url,
            'technologies': technologies,
            'confidence_scores': confidence_scores,
            'has_meta_generator': bool(generator_tag)
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Technology detection failed: {e}"}


def external_network_discovery(network: str = '') -> Dict[str, Any]:
    """Network discovery scan"""
    try:
        output = "🕵️ Network Discovery:\n"
        
        if network:
            # Use nmap for network discovery
            command = ['nmap', '-sn', network]
            result = execute_command(command, timeout=60)
            
            if result['success']:
                output += f"Network scan results for {network}:\n{result['output']}"
            else:
                output += f"Network scan failed: {result['output']}"
        else:
            # Default: scan local network
            command = ['arp', '-a']
            result = execute_command(command, timeout=30)
            
            if result['success']:
                output += f"Local network devices (ARP table):\n{result['output']}"
            else:
                output += "Local network discovery failed"
        
        return {
            'success': True,
            'output': output,
            'network': network
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Network discovery failed: {e}"}


def external_web_vuln_scan(url: str) -> Dict[str, Any]:
    """Web vulnerability scan"""
    try:
        if not url:
            return {'success': False, 'output': "❌ URL required"}
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        vulnerabilities = []
        
        output = f"🛡️ Web Vulnerability Scan for {url}:\n"
        
        # Basic security header checks
        try:
            response = requests.get(url, timeout=10)
            headers = response.headers
            
            # Check for missing security headers
            security_headers = {
                'Strict-Transport-Security': 'HSTS not enabled',
                'Content-Security-Policy': 'CSP not configured',
                'X-Frame-Options': 'Clickjacking protection missing',
                'X-Content-Type-Options': 'MIME sniffing protection missing'
            }
            
            for header, issue in security_headers.items():
                if header not in headers:
                    vulnerabilities.append(issue)
            
            # Check for sensitive information disclosure
            if 'server' in headers and 'apache' in headers['server'].lower():
                if any(version in headers['server'].lower() for version in ['2.2', '2.3']):
                    vulnerabilities.append("Outdated Apache version detected")
            
            if vulnerabilities:
                for vuln in vulnerabilities:
                    output += f"• ⚠️ {vuln}\n"
            else:
                output += "• ✅ No obvious vulnerabilities detected\n"
            
        except Exception as e:
            output += f"• ❌ Scan failed: {e}\n"
        
        output += f"\nVulnerabilities found: {len(vulnerabilities)}"
        
        return {
            'success': True,
            'output': output,
            'url': url,
            'vulnerabilities': vulnerabilities
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Vulnerability scan failed: {e}"}


def external_comprehensive_security_audit(url: str) -> Dict[str, Any]:
    """Comprehensive security audit"""
    try:
        if not url:
            return {'success': False, 'output': "❌ URL required"}
        
        # Extract domain/target from URL if needed
        if url.startswith(('http://', 'https://')):
            target = url.replace('http://', '').replace('https://', '').split('/')[0]
        else:
            target = url
        
        output = f"🔒 Comprehensive Security Audit for {target}:\n\n"
        
        # 1. Port scan
        output += "1. Port Scanning:\n"
        try:
            from .network_advanced import port_scan
            port_result = port_scan(target)
            if port_result['success']:
                output += f"   Open ports: {port_result.get('open_ports', [])}\n"
            else:
                output += "   Port scan failed\n"
        except:
            output += "   Port scan unavailable\n"
        
        # 2. Web vulnerability scan
        output += "\n2. Web Vulnerability Scan:\n"
        try:
            web_result = external_web_vuln_scan(target)
            if web_result['success']:
                vulns = web_result.get('vulnerabilities', [])
                output += f"   Vulnerabilities: {len(vulns)}\n"
                for vuln in vulns[:3]:
                    output += f"   • {vuln}\n"
            else:
                output += "   Web scan failed\n"
        except:
            output += "   Web scan unavailable\n"
        
        # 3. Technology detection
        output += "\n3. Technology Detection:\n"
        try:
            tech_result = external_tech_stack_detection(target)
            if tech_result['success']:
                techs = tech_result.get('technologies', [])
                for tech in techs[:3]:
                    output += f"   • {tech}\n"
            else:
                output += "   Technology detection failed\n"
        except:
            output += "   Technology detection unavailable\n"
        
        # 4. Subdomain enumeration
        output += "\n4. Subdomain Enumeration:\n"
        try:
            subdomain_result = external_subdomain_enum(target)
            if subdomain_result['success']:
                subdomains = subdomain_result.get('subdomains', [])
                output += f"   Found {len(subdomains)} subdomains\n"
            else:
                output += "   Subdomain enumeration failed\n"
        except:
            output += "   Subdomain enumeration unavailable\n"
        
        output += "\n📋 Comprehensive audit complete!"
        
        return {
            'success': True,
            'output': output,
            'url': url,
            'target': target
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Comprehensive audit failed: {e}"}