import requests
from bs4 import BeautifulSoup
import sys

sys.stdout.reconfigure(encoding='utf-8')

def check_bloomberg_gold():
    print("\nChecking Bloomberg HT (Gram Altin)...")
    url = "https://www.bloomberght.com/altin/gram-altin"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10, verify=False)
        soup = BeautifulSoup(resp.content, "html.parser")
        
        # Selector found from HTML inspection
        price_span = soup.select_one(".security-gram-altin .lastPrice")
        
        if price_span:
            print(f"  Price (Scraped): {price_span.text.strip()}")
        else:
            print("  Price NOT found with selector '.security-gram-altin .lastPrice'")
            
    except Exception as e:
        print(f"  Error: {e}")

check_bloomberg_gold()
