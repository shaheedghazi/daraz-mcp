import requests
import json

print('=== TESTING URL EXTRACTION ===')

# Test direct API call to see what URLs we get
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
params = {'q': 'nothing phone 1 case', 'ajax': 'true', 'page': '1', '_keyori': 'ss'}

response = requests.get('https://www.daraz.pk/catalog/', params=params, headers=headers, timeout=10)
if response.status_code == 200:
    data = response.json()
    if 'mods' in data and 'listItems' in data['mods']:
        items = data['mods']['listItems']
        print(f'Found {len(items)} items')
        
        for i, item in enumerate(items[:3], 1):  # Check first 3 items
            name = item.get('name', 'No name')[:50]
            url = item.get('itemUrl') or item.get('link') or item.get('url') or 'NO_URL'
            price_raw = item.get('priceShow', 'No price')
            
            print(f'\n{i}. {name}...')
            print(f'   Raw URL: {url}')
            
            # Fix URL if needed
            if url.startswith('//'):
                fixed_url = 'https:' + url
                print(f'   Fixed URL: {fixed_url}')
            elif url.startswith('/'):
                fixed_url = 'https://www.daraz.pk' + url
                print(f'   Fixed URL: {fixed_url}')
            elif url == 'NO_URL':
                print(f'   ❌ NO URL FOUND!')
                print(f'   Available keys: {list(item.keys())}')
            else:
                print(f'   ✅ URL OK: {url}')
            
            print(f'   Price: {price_raw}')
    else:
        print('No items found in mods.listItems')
else:
    print(f'API request failed: {response.status_code}')