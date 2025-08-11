#!/usr/bin/env python3
"""
Test script for the robust Daraz MCP server
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from server_robust import scraper, search_daraz, product_details

def test_json_method():
    """Test the JSON API method"""
    print("Testing JSON method...")
    results = scraper.search_json_method("wireless mouse", 1)
    print(f"JSON method found {len(results)} results")
    if results:
        print(f"First result: {results[0]['name'][:50]}...")
    return len(results) > 0

def test_search_function():
    """Test the main search function"""
    print("\nTesting main search function...")
    results = search_daraz("laptop", max_results=5)
    print(f"Search found {len(results)} results")
    
    for i, result in enumerate(results[:3]):
        print(f"{i+1}. {result['name'][:60]}...")
        print(f"   Price: {result['price']} PKR")
        print(f"   Method: {result['method']}")
        print(f"   URL: {result['url'][:50]}...")
        print()
    
    return len(results) > 0

def test_cache():
    """Test caching functionality"""
    print("Testing cache functionality...")
    
    # First search (should cache)
    results1 = search_daraz("smartphone", max_results=3)
    print(f"First search: {len(results1)} results")
    
    # Second search (should use cache)
    results2 = search_daraz("smartphone", max_results=3)
    print(f"Second search: {len(results2)} results")
    
    # Results should be identical
    cache_working = len(results1) == len(results2)
    if cache_working and results1:
        cache_working = results1[0]['name'] == results2[0]['name']
    
    print(f"Cache working: {cache_working}")
    return cache_working

def main():
    """Run all tests"""
    print("=" * 60)
    print("DARAZ MCP SERVER - ROBUST IMPLEMENTATION TEST")
    print("=" * 60)
    
    tests = [
        ("JSON Method", test_json_method),
        ("Search Function", test_search_function),
        ("Cache System", test_cache),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, "PASS" if result else "FAIL"))
        except Exception as e:
            print(f"ERROR in {test_name}: {e}")
            results.append((test_name, "ERROR"))
        
        print("-" * 40)
    
    print("\nTEST RESULTS:")
    print("=" * 30)
    for test_name, status in results:
        print(f"{test_name:<20}: {status}")
    
    # Overall status
    passed = sum(1 for _, status in results if status == "PASS")
    total = len(results)
    print(f"\nOVERALL: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! Server is ready for LM Studio.")
    else:
        print("❌ Some tests failed. Check the output above.")

if __name__ == "__main__":
    main()