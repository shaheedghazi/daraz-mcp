# Daraz MCP Server - Clean & Fast

A streamlined Model Context Protocol (MCP) server for searching Daraz.pk products. Built using **documented Daraz API patterns** for maximum reliability and performance.

## ✨ Features

- **🎯 Simple & Clean**: Just 2 tools instead of 6 confusing ones
- **📡 Official API Patterns**: Uses documented `mods.listItems` structure and `ajax=true` endpoints  
- **💸 Smart Cheapest Search**: Auto-detects "cheapest" queries and searches extensively
- **🚫 No Cache**: Always fresh results, no .db files created
- **🔄 Multi-method**: JSON API primary, Playwright browser fallback
- **🎨 Beautiful Output**: Human-readable results with clickable links
- **⚡ Fast**: Optimized using officially documented endpoints

## 🛠️ Tools Available

### 1. `search_daraz` - The Main Search Tool
Smart search that handles everything automatically:

```python
# Regular search
search_daraz("wireless mouse")

# Auto-detects cheapest requests  
search_daraz("cheapest wireless mouse")  # Searches 15 pages, sorts by price

# Explicit cheapest mode
search_daraz("mouse", cheapest=True)

# Price filtering
search_daraz("laptops", max_price=50000)

# Category search (uses documented category endpoints)
search_daraz("TV", category="televisions")
```

**Features:**
- Auto-detects "cheapest" in query and switches to extensive search mode
- Searches 15 pages for cheapest queries vs 5 for regular
- Sorts results by price for cheapest queries
- Returns formatted, clickable results

### 2. `product_details` - Get Product Info
```python
product_details("https://www.daraz.pk/products/product-url")
```

## 📡 API Implementation

This server uses **officially documented Daraz.pk endpoints**:

### Search Endpoint
```
GET https://www.daraz.pk/catalog/
    ?ajax=true
    &q=query
    &page=1
    &_keyori=ss
```

### Category Endpoint  
```
GET https://www.daraz.pk/{category}/
    ?ajax=true
    &page=1
    &q=search_within_category
```

**Response Structure:** `data.mods.listItems[]` contains product array

## 🚀 Quick Setup

1. **Install dependencies:**
```bash
pip install fastmcp requests beautifulsoup4 playwright
```

2. **Add to LM Studio `mcp.json`:**
```json
{
  "mcpServers": {
    "daraz-search": {
      "command": "C:\\path\\to\\python.exe",
      "args": ["C:\\path\\to\\server_merged.py"]
    }
  }
}
```

3. **Test in LM Studio:**
   - "Find cheapest Nothing phone case"
   - "Search for wireless mice under 2000 PKR" 
   - "Show me gaming laptops"

## 🎯 Improvements from Previous Version

### Before (Confusing):
❌ 6 different tools: `search_daraz`, `search_daraz_structured`, `search_daraz_formatted`, `search_cheapest_daraz`, `search_most_expensive_daraz`, `product_details`
❌ Cache causing stale results  
❌ AI couldn't decide which tool to use

### After (Clean):
✅ 2 simple tools: `search_daraz` (smart), `product_details`
✅ No cache - always fresh results
✅ Auto-detection of user intent
✅ Uses documented API patterns

## 📊 Search Behavior

| Query Type | Pages Searched | Results | Sorting |
|------------|---------------|---------|---------|
| Regular search | 5 pages | Up to 10 | As found |
| "Cheapest" query | 15 pages | 1 item | Price (lowest first) |
| With `cheapest=True` | 15 pages | 1 item | Price (lowest first) |
| With `max_price` | 5 pages | Filtered | As found |

## 🔧 No Cache = Always Fresh

- ✅ No `.db` files created
- ✅ Every search hits Daraz API fresh
- ✅ Latest prices and stock status
- ✅ No stale cached results

## 🛡️ Anti-Bot Protection

- User-Agent rotation (5 different browsers)
- Random delays between requests (1.0-2.5s)
- Proper headers and referrers
- Graceful fallback to browser automation

## 📖 Usage Examples

### For Users in LM Studio:
- *"Find me the cheapest Nothing phone 1 case"*
- *"Search for wireless mice under 1500 PKR"*
- *"What are some good gaming laptops?"*
- *"Show me TVs in the television category"*

### For Developers:
```python
# The AI will automatically choose the right parameters
search_daraz("cheapest phone cases")  # cheapest=True, max_results=1
search_daraz("phone cases")           # regular search, max_results=10
search_daraz("cases", max_price=500)  # price filtering
```

## 🎉 Ready to Use

This server is production-ready and uses officially documented Daraz.pk API patterns for maximum reliability. No seller account required - works with public endpoints only.

**Start LM Studio, add the MCP server, and start shopping! 🛍️**