# server_robust.py - Robust Daraz MCP Server with multi-method fetching and caching
from mcp.server.fastmcp import FastMCP
import requests
import time
import random
import re
import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import logging

# Configure logging with more detail and UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('daraz_mcp_debug.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

mcp = FastMCP("Daraz Search Robust")

class DarazScraper:
    def __init__(self, cache_expiry_hours: int = 3):
        self.cache_expiry_hours = cache_expiry_hours
        self.init_cache()
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
    def init_cache(self):
        """Initialize SQLite cache database"""
        self.conn = sqlite3.connect("daraz_cache.db", check_same_thread=False)
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS search_cache (
                cache_key TEXT PRIMARY KEY,
                query TEXT,
                page INTEGER,
                results TEXT,
                created_at TEXT,
                expires_at TEXT
            )
        ''')
        self.conn.commit()
        
    def get_cache_key(self, query: str, page: int) -> str:
        """Generate cache key for query and page"""
        return hashlib.md5(f"{query}_{page}".encode()).hexdigest()
        
    def get_cached_results(self, query: str, page: int) -> Optional[List[Dict]]:
        """Get cached results if not expired"""
        cache_key = self.get_cache_key(query, page)
        cursor = self.conn.execute(
            "SELECT results, expires_at FROM search_cache WHERE cache_key = ?",
            (cache_key,)
        )
        row = cursor.fetchone()
        
        if row:
            results_json, expires_at = row
            if datetime.fromisoformat(expires_at) > datetime.now():
                logger.info(f"Cache hit for query: {query}, page: {page}")
                return json.loads(results_json)
            else:
                # Remove expired cache
                self.conn.execute("DELETE FROM search_cache WHERE cache_key = ?", (cache_key,))
                self.conn.commit()
                
        return None
        
    def cache_results(self, query: str, page: int, results: List[Dict]):
        """Cache search results"""
        cache_key = self.get_cache_key(query, page)
        created_at = datetime.now()
        expires_at = created_at + timedelta(hours=self.cache_expiry_hours)
        
        self.conn.execute(
            "INSERT OR REPLACE INTO search_cache (cache_key, query, page, results, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
            (cache_key, query, page, json.dumps(results), created_at.isoformat(), expires_at.isoformat())
        )
        self.conn.commit()
        logger.info(f"Cached results for query: {query}, page: {page}")
        
    def _parse_price(self, price_str: str) -> Optional[float]:
        """Parse price string to float with comprehensive debugging"""
        logger.debug(f"Parsing price string: '{price_str}'")
        
        if not price_str:
            logger.debug("Price string is empty or None")
            return None
            
        # Clean the price string more thoroughly
        original_price = price_str
        clean_price = price_str.strip()
        
        # Remove common currency symbols and text
        clean_price = re.sub(r'Rs\.?|PKR|₨|rupees?|Rupees?', '', clean_price, flags=re.IGNORECASE)
        clean_price = re.sub(r'[^\d,.-]', '', clean_price)  # Keep only digits, commas, dots, minus
        
        logger.debug(f"Cleaned price string: '{clean_price}'")
        
        # Multiple regex patterns to catch different formats (order matters!)
        patterns = [
            r'(\d{1,3}(?:,\d{3})+(?:\.\d{2})?)',  # 1,234.00 or 1,234 (comma-separated)
            r'(\d+\.\d{2})',                      # 1234.00 (with decimals)
            r'(\d{4,})',                          # 1234+ (4+ digits without commas)
            r'(\d+)',                             # Any remaining digits
        ]
        
        for pattern in patterns:
            m = re.search(pattern, clean_price)
            if m:
                try:
                    price_value = float(m.group(1).replace(',', ''))
                    logger.debug(f"Successfully parsed price: {price_value} from '{original_price}'")
                    return price_value
                except ValueError as e:
                    logger.debug(f"Failed to convert '{m.group(1)}' to float: {e}")
                    continue
        
        logger.warning(f"Could not parse price from: '{original_price}' -> '{clean_price}'")
        return None
            
    def get_random_headers(self) -> Dict[str, str]:
        """Get randomized headers to avoid detection"""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://www.daraz.pk/",
        }
        
    def search_json_method(self, query: str, page: int = 1) -> List[Dict]:
        """Primary method: Use JSON API endpoint"""
        headers = self.get_random_headers()
        params = {"q": query, "ajax": "true", "page": page}
        
        try:
            logger.info(f"Trying JSON method for query: {query}, page: {page}")
            r = requests.get("https://www.daraz.pk/catalog/", 
                           params=params, headers=headers, timeout=15)
            
            # Check if we got blocked or redirected
            if r.status_code >= 400:
                logger.warning(f"HTTP {r.status_code} response, falling back to browser method")
                return []
                
            # Try to parse as JSON
            data = r.json()
            logger.debug(f"JSON response keys: {list(data.keys())}")
            
            items = data.get("mods", {}).get("listItems", [])
            if not items:
                # Try alternative paths in JSON structure
                alt_paths = [
                    ("results",),
                    ("data", "products"),
                    ("products",),
                    ("items",),
                    ("mods", "products"),
                    ("searchResult", "products")
                ]
                
                for path in alt_paths:
                    current = data
                    for key in path:
                        current = current.get(key, {})
                        if not current:
                            break
                    if isinstance(current, list) and current:
                        items = current
                        logger.debug(f"Found items at path: {' -> '.join(path)}")
                        break
            
            # Log first item structure for debugging
            if items:
                logger.debug(f"First item keys: {list(items[0].keys())}")
                logger.debug(f"First item sample: {items[0]}")
            
            if not items:
                logger.info("No items found in JSON response")
                return []
                
            results = []
            for i, item in enumerate(items):
                logger.debug(f"Processing item {i+1}: {list(item.keys())}")
                
                # Try multiple fields for name
                name = (item.get("name") or 
                       item.get("title") or 
                       item.get("productName") or 
                       item.get("itemTitle") or "")
                
                # Try multiple fields for price
                price_fields = ["priceShow", "price", "originalPrice", "currentPrice", "sellingPrice"]
                price_raw = None
                for field in price_fields:
                    if field in item and item[field]:
                        price_raw = str(item[field])
                        logger.debug(f"Found price in field '{field}': {price_raw}")
                        break
                
                if not price_raw:
                    logger.debug(f"No price found in any field for item: {name}")
                    logger.debug(f"Available fields: {list(item.keys())}")
                
                price = self._parse_price(price_raw) if price_raw else None
                
                # Try multiple fields for URL
                url = (item.get("itemUrl") or 
                      item.get("link") or 
                      item.get("productUrl") or 
                      item.get("url") or "")
                
                if url.startswith("//"):
                    url = "https:" + url
                elif url.startswith("/"):
                    url = "https://www.daraz.pk" + url
                
                # Try multiple fields for stock
                stock = (item.get("inStock") or 
                        item.get("stock") or 
                        item.get("availability") or 
                        item.get("stockStatus") or "")
                
                if name and url:  # Only add if we have basic info
                    result = {
                        "name": name,
                        "price": price,
                        "in_stock": str(stock),
                        "url": url,
                        "method": "json"
                    }
                    results.append(result)
                    logger.debug(f"Added result: {name} - {price} PKR (raw: '{price_raw}')")
                else:
                    logger.debug(f"Skipped item due to missing name or URL: name='{name}', url='{url}'")
                
            logger.info(f"JSON method found {len(results)} items")
            return results
            
        except (requests.exceptions.RequestException, ValueError, KeyError) as e:
            logger.warning(f"JSON method failed: {e}")
            return []
            
    def search_browser_method(self, query: str, page: int = 1) -> List[Dict]:
        """Fallback method: Use Playwright browser automation"""
        try:
            logger.info(f"Trying browser method for query: {query}, page: {page}")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=random.choice(self.user_agents)
                )
                page_obj = context.new_page()
                
                # Navigate to search page
                search_url = f"https://www.daraz.pk/catalog/?q={query}&page={page}"
                page_obj.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                
                # Wait for products to load
                try:
                    page_obj.wait_for_selector('[data-qa-locator="product-item"]', timeout=10000)
                except:
                    logger.warning("Product selector not found, trying alternative selectors")
                
                # Get page content and parse with BeautifulSoup
                content = page_obj.content()
                browser.close()
                
            soup = BeautifulSoup(content, 'html.parser')
            results = []
            
            # Try multiple possible selectors for products
            product_selectors = [
                '[data-qa-locator="product-item"]',
                '.gridItem',
                '.product-item',
                '[class*="product"]'
            ]
            
            products = []
            for selector in product_selectors:
                products = soup.select(selector)
                if products:
                    logger.info(f"Found {len(products)} products with selector: {selector}")
                    break
                    
            for product in products[:20]:  # Limit to 20 products per page
                try:
                    # Extract product name
                    name_elem = product.select_one('[title]') or product.select_one('a')
                    name = name_elem.get('title', '') or name_elem.get_text(strip=True) if name_elem else ""
                    
                    # Extract price
                    price_elem = product.select_one('[class*="price"]') or product.select_one('.currency')
                    price_text = price_elem.get_text(strip=True) if price_elem else ""
                    price = self._parse_price(price_text)
                    
                    # Extract URL
                    link_elem = product.select_one('a[href]')
                    url = link_elem.get('href', '') if link_elem else ""
                    if url.startswith("//"):
                        url = "https:" + url
                    elif url.startswith("/"):
                        url = "https://www.daraz.pk" + url
                        
                    # Extract stock info
                    stock_elem = product.select_one('[class*="stock"]')
                    in_stock = stock_elem.get_text(strip=True) if stock_elem else "Available"
                    
                    if name and url:  # Only add if we have basic info
                        results.append({
                            "name": name[:200],  # Limit name length
                            "price": price,
                            "in_stock": in_stock,
                            "url": url,
                            "method": "browser"
                        })
                        
                except Exception as e:
                    logger.debug(f"Error parsing product: {e}")
                    continue
                    
            logger.info(f"Browser method found {len(results)} items")
            return results
            
        except Exception as e:
            logger.error(f"Browser method failed: {e}")
            return []
            
    def search_with_fallback(self, query: str, page: int = 1) -> List[Dict]:
        """Search with automatic fallback between methods"""
        # Check cache first
        cached = self.get_cached_results(query, page)
        if cached:
            return cached
            
        # Try JSON method first
        results = self.search_json_method(query, page)
        
        # Fallback to browser method if JSON fails
        if not results:
            logger.info("JSON method failed, trying browser fallback")
            results = self.search_browser_method(query, page)
            
        # Cache results if we got any
        if results:
            self.cache_results(query, page, results)
            
        return results

# Global scraper instance
scraper = DarazScraper()

@mcp.tool()
def search_daraz(query: str, max_price: Optional[float] = None, max_results: int = 10, page_limit: int = 5) -> List[dict]:
    """
    Search Daraz.pk for products with robust multi-method fetching and caching.
    
    Args:
        query: Search term (e.g., "wireless mouse", "smartphone 128GB")
        max_price: Maximum price filter (in PKR)
        max_results: Maximum number of results to return
        page_limit: Maximum number of pages to search
        
    Returns:
        List of product dictionaries with: name, price, in_stock, url, method
    """
    all_results = []
    page = 1
    
    while len(all_results) < max_results and page <= page_limit:
        logger.info(f"Searching page {page} for query: {query}")
        
        # Get results for this page
        page_results = scraper.search_with_fallback(query, page)
        
        if not page_results:
            logger.info(f"No more results found on page {page}")
            break
            
        # Filter by price if specified
        for result in page_results:
            if len(all_results) >= max_results:
                break
                
            if max_price is not None and result.get("price"):
                if result["price"] > max_price:
                    continue
                    
            all_results.append(result)
            
        page += 1
        
        # Polite delay between pages
        if page <= page_limit:
            delay = random.uniform(1.0, 2.0)
            logger.info(f"Waiting {delay:.1f}s before next page")
            time.sleep(delay)
            
    logger.info(f"Found {len(all_results)} total results for query: {query}")
    return all_results

@mcp.tool()
def product_details(url: str) -> dict:
    """
    Get detailed information about a specific product from its URL.
    
    Args:
        url: Full Daraz product URL
        
    Returns:
        Dictionary with detailed product information
    """
    try:
        headers = scraper.get_random_headers()
        
        # Try to get product page
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return {"error": f"Failed to fetch product page: HTTP {r.status_code}"}
            
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # Extract detailed information
        details = {"url": url}
        
        # Product title
        title_elem = soup.select_one('h1') or soup.select_one('[class*="title"]')
        details["title"] = title_elem.get_text(strip=True) if title_elem else ""
        
        # Price
        price_elem = soup.select_one('[class*="price"]') or soup.select_one('.currency')
        if price_elem:
            details["price"] = scraper._parse_price(price_elem.get_text())
            
        # Rating
        rating_elem = soup.select_one('[class*="rating"]') or soup.select_one('[class*="star"]')
        details["rating"] = rating_elem.get_text(strip=True) if rating_elem else ""
        
        # Seller
        seller_elem = soup.select_one('[class*="seller"]') or soup.select_one('[class*="shop"]')
        details["seller"] = seller_elem.get_text(strip=True) if seller_elem else ""
        
        # Specifications (if available)
        spec_elements = soup.select('[class*="spec"]') or soup.select('.key-features li')
        specs = []
        for spec in spec_elements[:10]:  # Limit to 10 specs
            spec_text = spec.get_text(strip=True)
            if spec_text:
                specs.append(spec_text)
        details["specifications"] = specs
        
        return details
        
    except Exception as e:
        return {"error": f"Failed to get product details: {str(e)}"}

if __name__ == "__main__":
    mcp.run()