import requests

print('=== TESTING DOCUMENTED API PATTERNS ===')

# Test documented search endpoint
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
params = {'q': 'wireless mouse', 'ajax': 'true', 'page': '1', '_keyori': 'ss'}

print('Testing documented search endpoint...')
response = requests.get('https://www.daraz.pk/catalog/', params=params, headers=headers, timeout=10)
print(f'Status: {response.status_code}')

if response.status_code == 200:
    data = response.json()
    if 'mods' in data and 'listItems' in data['mods']:
        items = data['mods']['listItems']
        print(f'✅ SUCCESS: Found {len(items)} items using documented mods.listItems structure')
        if items:
            first_item = items[0]
            name = first_item.get('name', 'No name')
            price = first_item.get('priceShow', 'No price')
            print(f'First item: {name} - {price}')
    else:
        print('❌ mods.listItems not found in response')
        print(f'Available keys: {list(data.keys())}')
else:
    print(f'❌ Request failed: {response.status_code}')

print('\n=== TESTING OUR IMPROVED SERVER ===')
from server_merged import search_daraz
result = search_daraz('wireless mouse', max_results=3)
print(result)