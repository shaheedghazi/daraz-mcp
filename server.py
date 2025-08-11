# server.py
from mcp.server.fastmcp import FastMCP
import requests, time, random, re
from typing import Optional, List

mcp = FastMCP("Daraz Search")

def _parse_price(price_str: str) -> Optional[float]:
    if not price_str:
        return None
    # Find first number-like substring (e.g. "Rs. 1,234" -> "1234")
    m = re.search(r'[\d,]+(?:\.\d+)?', price_str.replace('Rs', '').replace('PKR', ''))
    if not m:
        return None
    return float(m.group(0).replace(',', ''))

@mcp.tool()
def search_daraz(query: str, max_price: Optional[float] = None, max_results: int = 10, page_limit: int = 5) -> List[dict]:
    """
    Search Daraz.pk for `query`. Returns up to `max_results` product dicts:
      { name, price (float|None), in_stock (raw string), url }
    Notes:
      - Uses the site's JSON search endpoint (?ajax=true).
      - Polite delays included to reduce block risk.
    """
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9",
    }

    page = 1
    while len(results) < max_results and page <= page_limit:
        params = {"q": query, "ajax": "true", "page": page}
        try:
            r = requests.get("https://www.daraz.pk/catalog/", params=params, headers=headers, timeout=10)
            data = r.json()
        except Exception as e:
            # If JSON parsing fails (site block/HTML), stop gracefully
            print(f"[daraz-mcp] non-json response or error on page {page}: {e}")
            break

        items = data.get("mods", {}).get("listItems", [])
        if not items:
            break

        for it in items:
            name = it.get("name") or it.get("title") or ""
            price = _parse_price(it.get("priceShow") or it.get("price") or "")
            if max_price is not None and price is not None and price > float(max_price):
                continue
            url = it.get("itemUrl") or it.get("link") or ""
            if url.startswith("//"):
                url = "https:" + url
            elif url.startswith("/"):
                url = "https://www.daraz.pk" + url
            results.append({
                "name": name,
                "price": price,
                "in_stock": it.get("inStock"),
                "url": url
            })
            if len(results) >= max_results:
                break

        page += 1
        # polite random delay (0.8–1.4s)
        time.sleep(random.uniform(0.8, 1.4))

    return results

if __name__ == "__main__":
    # default transport is STDIO (LM Studio will launch this process)
    mcp.run()