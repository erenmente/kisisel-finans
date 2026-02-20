from tefas import Crawler
from datetime import datetime, timedelta
import sys
import requests
from bs4 import BeautifulSoup
import yfinance as yf

# Windows terminalinde Türkçe karakter sorununu çöz
sys.stdout.reconfigure(encoding='utf-8')

def debug_tefas():
    print(f"--- DEBUG BAŞLANGIÇ: {datetime.now().strftime('%Y-%m-%d %H:%M')} ---")
    
    # 1. TEFAS Kütüphanesi (Geçmiş Veri)
    print("\n[1] TEFAS Kütüphanesi Kontrolü:")
    crawler = Crawler()
    for i in range(5):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        try:
            res = crawler.fetch(start=d, end=d, columns=["code", "date", "price"])
            tte = res[res['code'] == "TTE"]
            if not tte.empty:
                print(f"  {d}: BULUNDU -> {tte.iloc[0]['price']}")
            else:
                print(f"  {d}: Veri Yok")
        except Exception as e:
            print(f"  {d}: Hata ({e})")

    # 2. TEFAS FonAnaliz (Anlık/Son Fiyat)
    print("\n[2] TEFAS FonAnaliz (Direct Scraping) Kontrolü:")
    url = "https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod=TTE"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    }
    try:
        resp = requests.get(url, headers=headers, verify=False, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")
        price = soup.find("span", {"id": "MainContent_PanelInfo_lblPrice"})
        date = soup.find("span", {"id": "MainContent_PanelInfo_lblDate"})
        if price:
            print(f"  Fiyat: {price.text}")
        if date:
            print(f"  Tarih: {date.text}")
    except Exception as e:
        print(f"  Hata: {e}")

    # 3. Yahoo Finance (Hisse)
    print("\n[3] Yahoo Finance (THYAO.IS) Kontrolü:")
    try:
        ticker = yf.Ticker("THYAO.IS")
        hist = ticker.history(period="5d")
        print(hist[['Close']])
    except Exception as e:
        print(f"  Hata: {e}")

if __name__ == "__main__":
    debug_tefas()
