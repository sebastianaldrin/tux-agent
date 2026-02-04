"""
Web Search Tools
Search engine integration for information retrieval
"""
import logging
import requests
from typing import Dict, Any
from urllib.parse import quote_plus
import json
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def web_search(query: str, num_results: int = 5) -> Dict[str, Any]:
    """Search the web using a simple search approach that provides search engine links"""
    try:
        # Validate query
        if not query or len(query.strip()) < 2:
            return {'success': False, 'output': "❌ Search query required - please provide a search term with at least 2 characters"}
        
        # Validate num_results
        if not isinstance(num_results, int) or num_results < 1 or num_results > 20:
            num_results = 5
        
        # Clean and encode query
        clean_query = query.strip()
        encoded_query = quote_plus(clean_query)
        
        # Create search results with multiple search engines
        search_engines = [
            {
                'name': 'Google',
                'url': f'https://www.google.com/search?q={encoded_query}',
                'description': 'Most comprehensive search results'
            },
            {
                'name': 'DuckDuckGo',
                'url': f'https://duckduckgo.com/?q={encoded_query}',
                'description': 'Privacy-focused search engine'
            },
            {
                'name': 'Bing',
                'url': f'https://www.bing.com/search?q={encoded_query}',
                'description': 'Microsoft search engine'
            },
            {
                'name': 'Startpage',
                'url': f'https://www.startpage.com/sp/search?query={encoded_query}',
                'description': 'Private Google results'
            },
            {
                'name': 'Yandex',
                'url': f'https://yandex.com/search/?text={encoded_query}',
                'description': 'Good for technical and international results'
            }
        ]
        
        # Format output with search engine options
        output = f"🔍 Web Search for '{clean_query}':\n\n"
        output += "Search this query on multiple engines:\n\n"
        
        for i, engine in enumerate(search_engines[:num_results], 1):
            output += f"{i}. {engine['name']}\n"
            output += f"   {engine['description']}\n"
            output += f"   🔗 {engine['url']}\n\n"
        
        # Add helpful search tips
        output += "💡 Search Tips:\n"
        output += f"• Use quotes for exact phrases: \"{clean_query}\"\n"
        output += f"• Add site: for specific sites: site:stackoverflow.com {clean_query}\n"
        output += f"• Use - to exclude terms: {clean_query} -ads\n"
        output += f"• Try different keywords if no results\n"
        
        return {
            'success': True,
            'output': output,
            'query': clean_query,
            'search_engines': search_engines,
            'total_results': len(search_engines)
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Search failed for '{query}': {str(e)} - unexpected error during search"}


def search_news(query: str, num_results: int = 5) -> Dict[str, Any]:
    """Search for recent news articles"""
    try:
        # Validate query
        if not query or len(query.strip()) < 2:
            return {'success': False, 'output': "❌ News search query required - please provide a search term with at least 2 characters"}
        
        clean_query = query.strip()
        
        # Add news-specific terms to query
        news_query = f"{clean_query} news recent"
        
        # Delegate to main search function with news-specific query
        result = web_search(news_query, num_results)
        
        if result['success']:
            # Modify output to indicate it's a news search
            result['output'] = result['output'].replace('🔍 Web Search for', '📰 News Search for')
            result['search_type'] = 'news'
        
        return result
        
    except Exception as e:
        return {'success': False, 'output': f"❌ News search failed for '{query}': {str(e)} - unexpected error during news search"}


def search_images(query: str, num_results: int = 5) -> Dict[str, Any]:
    """Search for images (returns image search suggestions)"""
    try:
        # Validate query
        if not query or len(query.strip()) < 2:
            return {'success': False, 'output': "❌ Image search query required - please provide a search term with at least 2 characters"}
        
        clean_query = query.strip()
        
        # Since we can't easily return actual images, provide search suggestions
        output = f"🖼️ Image Search for '{clean_query}':\n\n"
        output += "To search for images, try these search engines:\n"
        output += f"• Google Images: https://images.google.com/search?q={quote_plus(clean_query)}\n"
        output += f"• Bing Images: https://www.bing.com/images/search?q={quote_plus(clean_query)}\n"
        output += f"• DuckDuckGo Images: https://duckduckgo.com/?q={quote_plus(clean_query)}&iax=images&ia=images\n"
        output += f"• Unsplash: https://unsplash.com/s/photos/{quote_plus(clean_query)}\n"
        
        return {
            'success': True,
            'output': output,
            'query': clean_query,
            'search_type': 'images',
            'suggested_urls': [
                f"https://images.google.com/search?q={quote_plus(clean_query)}",
                f"https://www.bing.com/images/search?q={quote_plus(clean_query)}",
                f"https://duckduckgo.com/?q={quote_plus(clean_query)}&iax=images&ia=images",
                f"https://unsplash.com/s/photos/{quote_plus(clean_query)}"
            ]
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Image search failed for '{query}': {str(e)} - unexpected error during image search"}


def search_stackoverflow(query: str, num_results: int = 5) -> Dict[str, Any]:
    """Search Stack Overflow for programming questions and answers"""
    try:
        # Validate query
        if not query or len(query.strip()) < 2:
            return {'success': False, 'output': "❌ Stack Overflow search query required - please provide a search term with at least 2 characters"}
        
        clean_query = query.strip()
        
        # Add site-specific search to query
        so_query = f"site:stackoverflow.com {clean_query}"
        
        # Delegate to main search function with Stack Overflow-specific query
        result = web_search(so_query, num_results)
        
        if result['success']:
            # Modify output to indicate it's a Stack Overflow search
            result['output'] = result['output'].replace('🔍 Web Search for', '💻 Stack Overflow Search for')
            result['search_type'] = 'stackoverflow'
        
        return result
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Stack Overflow search failed for '{query}': {str(e)} - unexpected error during Stack Overflow search"}


def search_github(query: str, num_results: int = 5) -> Dict[str, Any]:
    """Search GitHub for repositories and code"""
    try:
        # Validate query
        if not query or len(query.strip()) < 2:
            return {'success': False, 'output': "❌ GitHub search query required - please provide a search term with at least 2 characters"}
        
        clean_query = query.strip()
        
        # Add site-specific search to query
        github_query = f"site:github.com {clean_query}"
        
        # Delegate to main search function with GitHub-specific query
        result = web_search(github_query, num_results)
        
        if result['success']:
            # Modify output to indicate it's a GitHub search
            result['output'] = result['output'].replace('🔍 Web Search for', '🐙 GitHub Search for')
            result['search_type'] = 'github'
        
        return result
        
    except Exception as e:
        return {'success': False, 'output': f"❌ GitHub search failed for '{query}': {str(e)} - unexpected error during GitHub search"}