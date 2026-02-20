import requests
from bs4 import BeautifulSoup
import yfinance as yf
import sys
import urllib3

sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def debug_direct():
    print("--- DIRECT DEBUG ---")
    
    # 1. TEFAS Direct
    print("\n[1] TEFAS FonAnaliz:")
    url = "https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod=TTE"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, verify=False, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")
        
        # Yeni Mantık: ID yok, text üzerinden bul
        price = None
        date = None
        
        # Fiyatı bul
        for li in soup.find_all("li"):
            if "Fiyat" in li.text and "TL" in li.text:
                span = li.find("span")
                if span:
                    price = span.text
                    print(f"  Fiyat (Scraped): {price}")
                    break
        
        # Tarihi bul (Genellikle "Son İşlem Tarihi" veya benzeri)
        # HTML'de tarih nerede? Tahmin: "Tarih" içeren li
        for li in soup.find_all("li"):
            if "Tarih" in li.text:
                span = li.find("span")
                if span:
                    date = span.text
                    print(f"  Tarih (Scraped): {date}")
                    break
                    
    except Exception as e:
        print(f"  Hata: {e}")

    # 2. Yahoo Finance
    print("\n[2] Yahoo Finance (THYAO.IS):")
    try:
        ticker = yf.Ticker("THYAO.IS")
        hist = ticker.history(period="5d")
        print(hist[['Close']].tail())
    except Exception as e:
        print(f"  Hata: {e}")

if __name__ == "__main__":
    debug_direct()
