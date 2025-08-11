import asyncio
import hashlib
import json
import logging
import random
import re
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from fastmcp import FastMCP
from playwright.async_api import async_playwright

# Configure logging - NO .db files, always fresh
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('daraz_mcp_debug.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

mcp = FastMCP("Daraz Search Clean")

class DarazScraper:
    def __init__(self):
        # NO CACHE - Always fresh searches
        logger.info("Cache system DISABLED - always fresh searches")
        
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
    def _parse_price(self, price_str: str) -> Optional[float]:
        """Parse price string to float"""
        if not price_str:
            return None
        
        clean_price = price_str.strip()
        clean_price = re.sub(r'Rs\.?|PKR|₨|rupees?|Rupees?', '', clean_price, flags=re.IGNORECASE)
        clean_price = re.sub(r'[^\d,.-]', '', clean_price)
        
        patterns = [
            r'(\d{1,3}(?:,\d{3})+(?:\.\d{2})?)',  # 1,234.00 or 1,234
            r'(\d+\.\d{2})',                       # 1234.00
            r'(\d{4,})',                           # 1234+ (4+ digits)
            r'(\d+)',                              # Any remaining digits
        ]
        
        for pattern in patterns:
            m = re.search(pattern, clean_price)
            if m:
                try:
                    return float(m.group(1).replace(',', ''))
                except ValueError:
                    continue
        return None

    def search_json_method(self, query: str, page: int, category: Optional[str] = None) -> List[Dict]:
        """Search using Daraz JSON API"""
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.daraz.pk/"
        }
        
        # Use category endpoint if specified, otherwise use search endpoint
        if category:
            # Category endpoint: https://www.daraz.pk/{category}/?ajax=true&page=N
            url = f"https://www.daraz.pk/{category}/"
            params = {
                "ajax": "true",
                "page": page
            }
            # Add search within category if query provided
            if query:
                params["q"] = query
        else:
            # Search endpoint: https://www.daraz.pk/catalog/?ajax=true&q=query&page=N
            url = "https://www.daraz.pk/catalog/"
            params = {
                "q": query,
                "ajax": "true", 
                "page": page,
                "_keyori": "ss"  # Documented parameter for search
            }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Extract items using documented structure: mods.listItems is primary
            items = []
            try:
                # Primary documented path
                if "mods" in data and "listItems" in data["mods"]:
                    items = data["mods"]["listItems"]
                    logger.info("Using documented mods.listItems structure")
                # Fallback paths for edge cases  
                elif "results" in data:
                    items = data["results"]
                elif "listItems" in data:
                    items = data["listItems"]
                elif "data" in data and "products" in data["data"]:
                    items = data["data"]["products"]
            except (KeyError, TypeError) as e:
                logger.warning(f"Error accessing data structure: {e}")
                items = []
            
            if not items:
                logger.info("No items found in JSON response")
                return []
            
            logger.info(f"JSON method found {len(items)} items")
            
            results = []
            for item in items:
                # Extract data with multiple field attempts
                name = (item.get("name") or item.get("title") or 
                       item.get("productName") or "").strip()
                
                # Price extraction
                price_raw = (item.get("priceShow") or item.get("price") or 
                           item.get("salePrice") or item.get("currentPrice") or "")
                price = self._parse_price(str(price_raw))
                
                # Original price for discount calculation
                orig_price_raw = (item.get("originalPrice") or item.get("listPrice") or 
                                item.get("marketPrice") or "")
                orig_price = self._parse_price(str(orig_price_raw))
                
                # URL
                url = item.get("itemUrl") or item.get("link") or item.get("url") or ""
                if url.startswith("//"):
                    url = "https:" + url
                elif url.startswith("/"):
                    url = "https://www.daraz.pk" + url
                
                # Stock status
                stock = item.get("inStock") or item.get("stock") or item.get("available")
                
                if name and url:
                    result = {
                        "name": name,
                        "price": price,
                        "original_price": orig_price,
                        "in_stock": stock,
                        "url": url
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"JSON method failed: {e}")
            return []

    def search_with_fallback(self, query: str, page: int, category: Optional[str] = None) -> List[Dict]:
        """Search with JSON method, fallback to browser if needed"""
        logger.info(f"Trying JSON method for query: {query}, page: {page}" + (f", category: {category}" if category else ""))
        
        # Try JSON first
        results = self.search_json_method(query, page, category)
        if results:
            return results
        
        logger.info("JSON method failed, trying browser fallback")
        return self.search_browser_method(query, page)
    
    def search_browser_method(self, query: str, page: int) -> List[Dict]:
        """Fallback browser search with Playwright"""
        try:
            import asyncio
            return asyncio.run(self._browser_search_async(query, page))
        except Exception as e:
            logger.error(f"Browser method failed: {e}")
            return []
    
    async def _browser_search_async(self, query: str, page: int) -> List[Dict]:
        """Async browser search"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=random.choice(self.user_agents)
                )
                page_obj = await context.new_page()
                
                # Navigate to search
                search_url = f"https://www.daraz.pk/catalog/?q={query}&page={page}"
                await page_obj.goto(search_url, wait_until="networkidle")
                await page_obj.wait_for_timeout(2000)
                
                # Extract products
                products = await page_obj.query_selector_all('[data-qa-locator="product-item"]')
                
                if not products:
                    logger.warning("Product selector not found, trying alternative selectors")
                    selectors = ['.gridItem', '.product-item', '.item', '[data-qa-locator*="product"]']
                    for selector in selectors:
                        products = await page_obj.query_selector_all(selector)
                        if products:
                            break
                
                results = []
                for product in products:
                    try:
                        content = await product.inner_html()
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Extract name
                        name_elem = soup.find(['a', 'h2', 'h3'], string=True)
                        name = name_elem.get_text(strip=True) if name_elem else ""
                        
                        # Extract price
                        price_elem = soup.find(['span', 'div'], class_=re.compile(r'price', re.I))
                        price_text = price_elem.get_text(strip=True) if price_elem else ""
                        price = self._parse_price(price_text)
                        
                        # Extract URL
                        link_elem = soup.find('a', href=True)
                        url = link_elem['href'] if link_elem else ""
                        if url.startswith('/'):
                            url = "https://www.daraz.pk" + url
                        
                        if name and url:
                            results.append({
                                "name": name,
                                "price": price,
                                "original_price": None,
                                "in_stock": "true",  # Default for browser results
                                "url": url
                            })
                    except Exception as e:
                        logger.debug(f"Error parsing product: {e}")
                        continue
                
                await browser.close()
                logger.info(f"Browser method found {len(results)} items")
                return results
                
        except Exception as e:
            logger.error(f"Browser search failed: {e}")
            return []

# Initialize scraper
scraper = DarazScraper()

@mcp.tool()
def search_daraz(query: str, cheapest: bool = False, max_price: Optional[float] = None, max_results: int = 10, category: Optional[str] = None) -> str:
    """
    Search Daraz.pk for products with intelligent result handling.
    
    Args:
        query: What to search for (e.g., "wireless mouse", "Nothing phone case", "Express Ultra detergent")
        cheapest: Set to True to find the absolute cheapest item(s) (searches more pages, sorts by price)
        max_price: Maximum price filter in PKR (optional)
        max_results: How many results to show (default: 10, or 1 if cheapest=True)
        category: Optional category slug for focused search (e.g., "televisions", "mobile-phones")
        
    Returns:
        Beautifully formatted results with prices, stock status, and clickable links
        
    Examples:
        - search_daraz("wireless mouse") → Regular search
        - search_daraz("wireless mouse", cheapest=True) → Find THE cheapest mouse
        - search_daraz("laptops", max_price=50000) → Laptops under 50k
        - search_daraz("TV", category="televisions") → Search within TV category
    """
    
    # Auto-detect "cheapest" requests
    if "cheapest" in query.lower() or "cheap" in query.lower():
        cheapest = True
    
    # Adjust search parameters for cheapest queries
    if cheapest:
        page_limit = 15  # Search more pages for cheapest
        search_results = max_results * 10  # Get more results to sort
        if max_results == 10:  # Default case
            max_results = 1  # Show only THE cheapest
    else:
        page_limit = 5   # Regular search
        search_results = max_results
    
    # Perform search
    all_results = []
    page = 1
    
    while len(all_results) < search_results and page <= page_limit:
        logger.info(f"Searching page {page} for query: {query}")
        
        # Get results for this page
        page_results = scraper.search_with_fallback(query, page, category)
        
        if not page_results:
            logger.info(f"No more results found on page {page}")
            break
        
        # Filter and process results
        for result in page_results:
            if len(all_results) >= search_results:
                break
                
            # Apply max_price filter
            if max_price and result.get('price') and result['price'] > max_price:
                continue
            
            all_results.append(result)
        
        page += 1
        # Random delay between pages
        delay = random.uniform(1.0, 2.5)
        logger.info(f"Waiting {delay:.1f}s before next page")
        time.sleep(delay)
    
    if not all_results:
        return f"❌ No products found for '{query}'" + (f" under Rs. {max_price:,.0f}" if max_price else "")
    
    # Sort results if cheapest requested
    if cheapest:
        all_results = sorted(
            [r for r in all_results if r.get('price') is not None], 
            key=lambda x: x['price']
        )[:max_results]
    else:
        all_results = all_results[:max_results]
    
    logger.info(f"Found {len(all_results)} total results for query: {query}")
    
    # Format output
    if cheapest and max_results == 1:
        header = f"💸 **THE CHEAPEST {query.title()} on Daraz**"
    elif cheapest:
        header = f"💸 **{len(all_results)} CHEAPEST {query.title()} on Daraz (Sorted by Price)**"
    else:
        header = f"🛍️ **Found {len(all_results)} {'result' if len(all_results) == 1 else 'results'} for '{query}'**"
        if max_price:
            header = f"💰 **{query.title()} under Rs. {max_price:,.0f}**"
    
    formatted_output = f"{header}\n\n"
    
    for i, product in enumerate(all_results, 1):
        formatted_output += f"**{i}. {product['name']}**\n"
        
        # Price with discount info
        if product.get('original_price') and product['original_price'] > product['price']:
            discount = ((product['original_price'] - product['price']) / product['original_price']) * 100
            formatted_output += f"💰 **Price:** ~~Rs. {product['original_price']:,.0f}~~ **Rs. {product['price']:,.0f}** ({discount:.1f}% off)\n"
        else:
            formatted_output += f"💰 **Price:** Rs. {product['price']:,.0f}\n"
        
        # Stock status
        stock_status = "✅ In Stock" if str(product.get('in_stock', '')).lower() == 'true' else "❌ Out of Stock"
        formatted_output += f"📦 **Status:** {stock_status}\n"
        
        # Clickable link - multiple formats for compatibility
        formatted_output += f"🔗 **View Product:** [Click here to view on Daraz]({product['url']})\n"
        formatted_output += f"📱 **Direct Link:** {product['url']}\n\n"
    
    # Add disclaimer
    if cheapest:
        formatted_output += "⚠️ **Note:** These are the cheapest available. Prices may vary on the actual product page. Always verify current prices before purchasing.\n"
    else:
        formatted_output += "⚠️ **Note:** Prices may vary on the actual product page due to dynamic pricing. Always verify current prices before purchasing.\n"
    
    return formatted_output

@mcp.tool()
def product_details(url: str) -> str:
    """
    Get detailed information about a specific Daraz product.
    
    Args:
        url: Full Daraz product URL
        
    Returns:
        Detailed product information including description, specifications, seller info, etc.
    """
    try:
        headers = {
            "User-Agent": random.choice(scraper.user_agents),
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract product details
        name = soup.find('h1')
        name = name.get_text(strip=True) if name else "Product name not found"
        
        price_elem = soup.find(['span', 'div'], class_=re.compile(r'price', re.I))
        price = price_elem.get_text(strip=True) if price_elem else "Price not found"
        
        # Format response
        details = f"📦 **Product Details**\n\n"
        details += f"**Name:** {name}\n"
        details += f"**Price:** {price}\n"
        details += f"**URL:** {url}\n\n"
        details += "ℹ️ For complete details, specifications, and reviews, please visit the product page.\n"
        
        return details
        
    except Exception as e:
        return f"❌ Error fetching product details: {str(e)}\nPlease check the URL and try again."

if __name__ == "__main__":
    mcp.run()