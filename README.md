# Daraz MCP Server - Robust Implementation

A production-ready MCP (Model Context Protocol) server that enables LM Studio to search Daraz.pk products with automatic fallback methods, intelligent caching, and anti-bot protection.

## 🚀 Features

### Multi-Method Fetching
- **Primary**: Fast JSON API endpoint (`?ajax=true`)
- **Fallback**: Playwright browser automation when JSON fails
- **Auto-switch**: Detects blocks/CAPTCHAs and switches methods automatically

### Anti-Bot Protection
- Rotating User-Agent strings
- Random delays between requests (0.8-2.0s)
- Polite rate limiting with backoff
- Browser automation for complex scenarios

### Intelligent Caching
- SQLite-based cache with 3-hour expiry (configurable)
- Instant responses for repeated queries
- Automatic cache cleanup for expired entries

### Robust Error Handling
- Graceful degradation when methods fail
- Comprehensive logging for debugging
- Fallback parsing for different page layouts

## 📁 Project Structure

```
daraz mcp/
├── server_robust.py      # Main robust MCP server
├── server.py             # Simple version (backup)
├── test_server.py        # Test suite
├── mcp.json             # LM Studio configuration
├── requirements.txt     # Dependencies
├── daraz_cache.db       # SQLite cache (auto-created)
└── README.md           # This file
```

## 🛠️ Installation

### Prerequisites
- Python 3.10+
- LM Studio installed
- VS Code (optional but recommended)

### Step 1: Clone and Setup

```powershell
# Create project directory
mkdir "C:\Users\YourName\daraz-mcp"
cd "C:\Users\YourName\daraz-mcp"

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install --upgrade pip
pip install "mcp[cli]" fastmcp requests playwright beautifulsoup4

# Install browser for Playwright
playwright install chromium
```

### Step 2: Copy Files

Copy all the files from this project to your directory, or create them manually:

- `server_robust.py` - Main server implementation
- `mcp.json` - LM Studio configuration
- `test_server.py` - Test suite

### Step 3: Test Installation

```powershell
python test_server.py
```

You should see:
```
✅ All tests passed! Server is ready for LM Studio.
```

## 🔧 LM Studio Configuration

### Option 1: Copy mcp.json (Recommended)

1. Copy the `mcp.json` from this project
2. Edit the paths to match your setup:

```json
{
  "mcpServers": {
    "daraz-search": {
      "command": "C:\\Users\\YourName\\daraz-mcp\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\YourName\\daraz-mcp\\server_robust.py"
      ]
    }
  }
}
```

### Option 2: Add to Existing mcp.json

If you already have an `mcp.json`, add this entry to the `mcpServers` section:

```json
"daraz-search": {
  "command": "C:\\Users\\YourName\\daraz-mcp\\.venv\\Scripts\\python.exe",
  "args": [
    "C:\\Users\\YourName\\daraz-mcp\\server_robust.py"
  ]
}
```

### Step 4: Configure LM Studio

1. Open LM Studio
2. Go to **Program → Install → Edit mcp.json**
3. Paste your configuration
4. Save and restart LM Studio

## 🎯 Usage in LM Studio

### Basic Searches

Ask your AI assistant natural questions like:

```
"Find wireless mice under 2000 PKR on Daraz"
"Show me the cheapest laptops available on Daraz"
"Search for smartphone cases with good ratings"
```

### Advanced Queries

```
"Compare the top 5 gaming headsets on Daraz under 5000 PKR"
"Find DSLR cameras and show me detailed specs for the best ones"
"What are the most popular fitness trackers under 15000 PKR?"
```

## 🔧 Available Tools

### `search_daraz(query, max_price=None, max_results=10, page_limit=5)`

Main search function with these parameters:

- **query** (required): Search term (e.g., "wireless mouse", "smartphone 128GB")
- **max_price** (optional): Maximum price filter in PKR
- **max_results** (optional): Maximum number of results (default: 10)
- **page_limit** (optional): Maximum pages to search (default: 5)

**Returns**: List of products with:
- `name`: Product title
- `price`: Price in PKR (float) or null
- `in_stock`: Stock status
- `url`: Direct product link
- `method`: Which method was used ("json" or "browser")

### `product_details(url)`

Get detailed information about a specific product:

- **url** (required): Full Daraz product URL

**Returns**: Dictionary with:
- `title`: Full product title
- `price`: Current price
- `rating`: User rating
- `seller`: Seller information
- `specifications`: List of key features

## 🐛 Troubleshooting

### Common Issues

**1. "Server not starting"**
```powershell
# Check if Python path is correct
.\.venv\Scripts\python.exe --version

# Test server manually
.\.venv\Scripts\python.exe server_robust.py
```

**2. "No results found"**
- Daraz may be blocking requests
- Try different search terms
- Check if the site is accessible from your location
- The browser fallback should activate automatically

**3. "Permission errors"**
```powershell
# If PowerShell blocks scripts:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**4. "Module not found errors"**
```powershell
# Reinstall dependencies
pip install --force-reinstall "mcp[cli]" fastmcp requests playwright beautifulsoup4
playwright install chromium
```

### Debug Mode

For verbose logging, modify `server_robust.py`:

```python
# Change this line:
logging.basicConfig(level=logging.INFO)
# To:
logging.basicConfig(level=logging.DEBUG)
```

### Cache Issues

Clear the cache if you're getting stale results:

```powershell
del daraz_cache.db
```

## ⚖️ Legal and Ethical Usage

### Important Notes

- **Respect robots.txt**: Check Daraz's robots.txt file
- **Rate limiting**: Built-in delays prevent server overload
- **Personal use**: Intended for personal shopping assistance
- **Terms of Service**: Ensure compliance with Daraz's ToS

### Responsible Usage

- Don't make excessive requests
- Use caching to minimize server load
- Respect the website's resources
- Consider using official APIs when available

## 🔧 Advanced Configuration

### Cache Settings

Modify cache duration in `server_robust.py`:

```python
# Change cache expiry (in hours)
scraper = DarazScraper(cache_expiry_hours=6)  # 6 hours instead of 3
```

### Request Delays

Adjust delays for your needs:

```python
# In search_with_fallback method, change:
delay = random.uniform(1.0, 2.0)  # 1-2 seconds
# To:
delay = random.uniform(2.0, 4.0)  # 2-4 seconds for slower requests
```

### User Agent Rotation

Add more user agents in the `__init__` method:

```python
self.user_agents = [
    # ... existing agents ...
    "Your custom user agent string here"
]
```

## 📊 Performance

### Typical Response Times

- **Cache hit**: < 50ms
- **JSON method**: 1-3 seconds
- **Browser fallback**: 5-10 seconds
- **Product details**: 2-5 seconds

### Resource Usage

- **Memory**: ~50-100MB for JSON, ~200-300MB with browser
- **Storage**: Cache grows ~1MB per 1000 searches
- **Network**: ~1-5KB per JSON request, ~500KB-2MB per browser request

## 🤝 Contributing

Want to improve the server? Here are some ideas:

1. **Add more e-commerce sites** (Amazon.pk, OLX, etc.)
2. **Implement price tracking** over time
3. **Add image extraction** for products
4. **Create a web dashboard** for cache management
5. **Add proxy support** for high-volume usage

## 📝 Changelog

### v1.0 (Current)
- Multi-method fetching (JSON + Browser)
- SQLite caching with expiry
- Anti-bot protection
- Product details extraction
- Comprehensive error handling
- Full LM Studio integration

## 📄 License

This project is for educational and personal use. Respect the terms of service of all websites you interact with.

---

**Built with ❤️ for the LM Studio and MCP community**