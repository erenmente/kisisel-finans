"""
Finans Asistanı v11 - Browser Agent Edition
============================================
Gerçek tarayıcı otomasyonu ile güvenilir veri çekimi.
Groq AI ile doğal dil sorgulama.

Yenilikler:
- Playwright tabanlı browser agent
- Profesyonel logging sistemi  
- Rate limiting
- Kısmi satış desteği
- İşlem geçmişi
"""

import os
import json
import sys
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Üçüncü parti
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from groq import Groq
import urllib3
from dotenv import load_dotenv
from tefas import Crawler  # TEFAS resmi API
from datetime import datetime, timedelta

# Yerel modüller
from database import PortfolioDB
from utils import setup_logger, rate_limited, acquire
from browser_agent import SyncBrowserAgent, BrowserAgent

# --- YAPILANDIRMA ---
sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logger'ı başlat
logger = setup_logger("FinansAsistan", logging.INFO)

# API Ayarları
MODEL_NAME = "llama-3.3-70b-versatile"
API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    logger.error("GROQ_API_KEY bulunamadı!")
    sys.exit("HATA: .env dosyasında GROQ_API_KEY bulunamadı.")

# Veritabanı
db = PortfolioDB()

# Browser Agent (varsayılan: headless)
# show_browser=True yaparak tarayıcıyı görünür yapabilirsin
USE_BROWSER_AGENT = True  # False = eski scraping yöntemi
SHOW_BROWSER = False       # True = tarayıcı görünür şekilde açılır

browser_agent: Optional[SyncBrowserAgent] = None


class SuppressOutput:
    """yfinance uyarılarını bastır"""
    def __enter__(self):
        self._original_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr.close()
        sys.stderr = self._original_stderr


def get_browser_agent() -> SyncBrowserAgent:
    """Browser agent'ı başlat (lazy loading)"""
    global browser_agent
    if browser_agent is None:
        logger.info("🌐 Browser Agent başlatılıyor...")
        browser_agent = SyncBrowserAgent(show_browser=SHOW_BROWSER)
    return browser_agent


# ============================================================
# VERİ ÇEKME FONKSİYONLARI (BROWSER AGENT + FALLBACK)
# ============================================================

@rate_limited("tefas")
def _check_tefas_crawler(code: str) -> Optional[Dict]:
    """TEFAS - tefas-crawler kütüphanesi ile (resmi API)"""
    try:
        crawler = Crawler()
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        # Son 1 günlük veriyi çek
        data = crawler.fetch(
            start=yesterday.strftime("%Y-%m-%d"),
            end=today.strftime("%Y-%m-%d"),
            name=code.upper()
        )
        
        if not data.empty:
            # En son fiyatı al
            latest = data.iloc[-1]
            return {
                "symbol": code.upper(),
                "title": latest.get("Fon Adı", code),
                "price": str(round(latest["Fiyat"], 4)),
                "date": str(latest.get("Tarih", today.strftime("%Y-%m-%d"))),
                "source": "TEFAS (Resmi API)"
            }
    except Exception as e:
        logger.warning(f"TEFAS Crawler hatası: {e}")
    return None


@rate_limited("tefas")
def _check_tefas_browser(code: str) -> Optional[Dict]:
    """TEFAS - Browser Agent ile (şu an TEFAS bot koruması var, devre dışı)"""
    # TEFAS headless tarayıcıları engelliyor, bu yüzden devre dışı
    return None



@rate_limited("tefas")
def _check_tefas_requests(code: str) -> Optional[Dict]:
    """TEFAS - Requests ile (fallback)"""
    url = f"https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod={code}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Referer": "https://www.google.com/"
    }
    
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                
                result = {"symbol": code, "source": "TEFAS"}
                
                # Başlık
                title = soup.find("span", {"id": "MainContent_PanelInfo_lblFundTitle"})
                if title:
                    result["title"] = title.text.strip()
                
                # Fiyat ve tarih
                for li in soup.find_all("li"):
                    text = li.text
                    if "Fiyat" in text and "TL" in text:
                        span = li.find("span")
                        if span:
                            result["price"] = span.text.strip()
                    elif "Tarih" in text:
                        span = li.find("span")
                        if span:
                            result["date"] = span.text.strip()
                
                if "price" in result:
                    return result
                    
        except Exception as e:
            logger.debug(f"TEFAS requests hatası ({attempt+1}/3): {e}")
    
    return None


@rate_limited("bloomberg")
def _check_bloomberg_gold_browser() -> Optional[Dict]:
    """Bloomberg Altın - Browser Agent ile"""
    try:
        agent = get_browser_agent()
        result = agent.get_gold()
        if "error" not in result and "price" in result:
            return result
    except Exception as e:
        logger.warning(f"Browser Agent Bloomberg hatası: {e}")
    return None


@rate_limited("yahoo")
def _check_yahoo(symbol: str) -> Optional[Dict]:
    """Yahoo Finance - yfinance kütüphanesi ile"""
    
    # Altın özel hesaplaması
    if symbol == "ALTIN":
        with SuppressOutput():
            try:
                xau = yf.Ticker("XAUUSD=X")
                usd = yf.Ticker("TRY=X")
                
                xau_price = getattr(xau.fast_info, 'last_price', None)
                usd_price = getattr(usd.fast_info, 'last_price', None)
                
                if xau_price and usd_price:
                    gram_try = (xau_price * usd_price) / 31.1035
                    return {
                        "symbol": "ALTIN",
                        "price": round(gram_try, 2),
                        "currency": "TRY",
                        "source": "Yahoo (Hesaplanan)"
                    }
            except Exception as e:
                logger.debug(f"Yahoo altın hatası: {e}")
                # Fallback: Bloomberg
                return _check_bloomberg_gold_browser()
    
    # Döviz mapping
    mapping = {
        "USD": "TRY=X",
        "DOLAR": "TRY=X", 
        "EUR": "EURTRY=X",
        "EURO": "EURTRY=X",
        "BITCOIN": "BTC-USD",
        "BTC": "BTC-USD"
    }
    symbol = mapping.get(symbol.upper(), symbol)
    
    with SuppressOutput():
        try:
            ticker = yf.Ticker(symbol)
            price = getattr(ticker.fast_info, 'last_price', None)
            
            if price is None:
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
            
            if price:
                return {
                    "symbol": symbol,
                    "price": round(price, 2),
                    "currency": "TRY",
                    "source": "Yahoo Finance"
                }
        except Exception as e:
            logger.debug(f"Yahoo hatası: {e}")
    
    return None


def get_financial_data(query: str) -> str:
    """
    Ana veri çekme fonksiyonu.
    Browser Agent veya fallback yöntemleri kullanır.
    """
    query = query.upper().strip().split()[0].replace(",", "")
    logger.info(f"🔍 Aranıyor: {query}")
    
    result = None
    
    # ADIM 1: TEFAS (3 harfli kodlar)
    if len(query) == 3:
        # Önce tefas-crawler dene (resmi API)
        result = _check_tefas_crawler(query)
        
        if not result:
            logger.debug("TEFAS Crawler başarısız, requests deneniyor...")
            result = _check_tefas_requests(query)
    
    # ADIM 2: BIST Hissesi
    if not result and "." not in query:
        result = _check_yahoo(f"{query}.IS")
    
    # ADIM 3: Global/Döviz/Altın
    if not result:
        result = _check_yahoo(query)
    
    # ADIM 4: Altın için fallback
    if not result and query == "ALTIN":
        result = _check_bloomberg_gold_browser()
    
    if result:
        logger.info(f"✅ Bulundu: {result.get('symbol')} = {result.get('price')}")
        return json.dumps(result, ensure_ascii=False)
    
    logger.warning(f"⚠️ Veri bulunamadı: {query}")
    return json.dumps({"error": f"'{query}' verisi bulunamadı."})


# ============================================================
# PORTFÖY FONKSİYONLARI
# ============================================================

def add_investment(sembol: str, miktar: float, maliyet: float) -> str:
    """Portföye yatırım ekle"""
    logger.info(f"💾 Ekleniyor: {sembol} x{miktar} @ {maliyet}")
    return json.dumps({"msg": db.ekle(sembol, miktar, maliyet)}, ensure_ascii=False)


def sell_investment(sembol: str, miktar: float, satis_fiyati: float) -> str:
    """Yatırım sat (kısmi satış destekli)"""
    logger.info(f"💰 Satılıyor: {sembol} x{miktar} @ {satis_fiyati}")
    return json.dumps({"msg": db.sat(sembol, miktar, satis_fiyati)}, ensure_ascii=False)


def update_investment(sembol: str, yeni_miktar: Optional[float] = None, 
                     yeni_maliyet: Optional[float] = None) -> str:
    """Yatırım güncelle"""
    logger.info(f"🔄 Güncelleniyor: {sembol}")
    return json.dumps({"msg": db.guncelle(sembol, yeni_miktar, yeni_maliyet)}, ensure_ascii=False)


def get_portfolio() -> str:
    """Portföyü getir"""
    logger.info("📂 Portföy okunuyor...")
    return json.dumps(db.getir(), ensure_ascii=False)


def get_transaction_history(sembol: Optional[str] = None) -> str:
    """İşlem geçmişini getir"""
    logger.info(f"📜 İşlem geçmişi: {sembol or 'Tümü'}")
    return json.dumps(db.islem_gecmisi(sembol), ensure_ascii=False)


def get_portfolio_summary() -> str:
    """Portföy özeti"""
    logger.info("📊 Portföy özeti")
    return json.dumps(db.ozet(), ensure_ascii=False)


# ============================================================
# AI YAPILANDIRMASI
# ============================================================

client = Groq(api_key=API_KEY)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_financial_data",
            "description": "Hisse, fon, döviz veya altın fiyatını getirir. Gerçek tarayıcı ile veri çeker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Sembol (Örn: TTE, THYAO, USD, ALTIN, BITCOIN)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_investment",
            "description": "Portföye yeni yatırım ekler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sembol": {"type": "string", "description": "Yatırım sembolü"},
                    "miktar": {"type": "number", "description": "Adet/Pay sayısı"},
                    "maliyet": {"type": "number", "description": "Birim alış fiyatı (TL)"}
                },
                "required": ["sembol", "miktar", "maliyet"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sell_investment",
            "description": "Portföyden yatırım satar. Kısmi satış destekler ve kar/zarar hesaplar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sembol": {"type": "string", "description": "Satılacak sembol"},
                    "miktar": {"type": "number", "description": "Satılacak adet"},
                    "satis_fiyati": {"type": "number", "description": "Birim satış fiyatı (TL)"}
                },
                "required": ["sembol", "miktar", "satis_fiyati"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_investment",
            "description": "Mevcut yatırımı günceller (miktar veya maliyet).",
            "parameters": {
                "type": "object",
                "properties": {
                    "sembol": {"type": "string", "description": "Güncellenecek sembol"},
                    "yeni_miktar": {"type": "number", "description": "Yeni adet (opsiyonel)"},
                    "yeni_maliyet": {"type": "number", "description": "Yeni maliyet (opsiyonel)"}
                },
                "required": ["sembol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio",
            "description": "Mevcut portföyü listeler.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_transaction_history",
            "description": "İşlem geçmişini gösterir (alış, satış, güncelleme).",
            "parameters": {
                "type": "object",
                "properties": {
                    "sembol": {"type": "string", "description": "Filtrelenecek sembol (opsiyonel)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_summary",
            "description": "Portföy özetini gösterir (toplam maliyet, sembol sayısı vs).",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

SYSTEM_PROMPT = """
Sen Eren'in akıllı Finans Asistanısın. Gerçek tarayıcı ile veri çekebilirsin.

📌 Görevlerin:
1. Fiyat sorgula: get_financial_data ile sembol fiyatını bul
2. Portföy yönet: Ekle, sat, güncelle işlemlerini yap
3. Analiz yap: Portföy durumunu değerlendir

📌 Önemli Kurallar:
- Türkçe ve kısa cevaplar ver
- 1.017 gibi sayılar ondalıktır (bin değil)
- Kullanıcı "ne alayım" derse: THYAO, ASELS, TTE, YAS, ALTIN fiyatlarını kontrol et
- Satış işleminde kar/zarar bilgisini mutlaka belirt

📌 Yeni Özellikler:
- Kısmi satış: "50 adet TTE sat" gibi komutlar
- İşlem geçmişi: "son işlemlerimi göster"
- Portföy özeti: "portföy özetim"
"""


def process_tool_calls(tool_calls) -> list:
    """Tool çağrılarını işle"""
    results = []
    
    for tool in tool_calls:
        try:
            args = json.loads(tool.function.arguments)
        except json.JSONDecodeError:
            args = {}
        
        func_name = tool.function.name
        data = ""
        
        if func_name == "get_financial_data":
            query = args.get('query', '').split()[0].replace(",", "").strip()
            data = get_financial_data(query)
            
        elif func_name == "add_investment":
            data = add_investment(args['sembol'], args['miktar'], args['maliyet'])
            
        elif func_name == "sell_investment":
            data = sell_investment(args['sembol'], args['miktar'], args['satis_fiyati'])
            
        elif func_name == "update_investment":
            data = update_investment(
                args['sembol'],
                args.get('yeni_miktar'),
                args.get('yeni_maliyet')
            )
            
        elif func_name == "get_portfolio":
            data = get_portfolio()
            
        elif func_name == "get_transaction_history":
            data = get_transaction_history(args.get('sembol'))
            
        elif func_name == "get_portfolio_summary":
            data = get_portfolio_summary()
        
        results.append({
            "role": "tool",
            "tool_call_id": tool.id,
            "content": data
        })
    
    return results


def chat_with_groq():
    """Ana sohbet döngüsü"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    print("\n" + "=" * 50)
    print("  EREN'İN FİNANS ASİSTANI v11 - Browser Agent")
    print("=" * 50)
    print("  🌐 Gerçek tarayıcı ile veri çekimi")
    print("  💰 Kısmi satış & Kar/Zarar hesaplama")
    print("  📜 İşlem geçmişi takibi")
    print("-" * 50)
    print("  Çıkış: 'q' veya 'çıkış'")
    print("=" * 50 + "\n")
    
    while True:
        try:
            user_input = input("Sen: ").strip()
            
            if not user_input:
                continue
            if user_input.lower() in ['q', 'exit', 'çıkış', 'quit']:
                break
            
            messages.append({"role": "user", "content": user_input})
            
            # AI'ya gönder
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            
            msg = response.choices[0].message
            
            # Tool çağrısı varsa işle
            if msg.tool_calls:
                messages.append(msg)
                tool_results = process_tool_calls(msg.tool_calls)
                messages.extend(tool_results)
                
                # Sonuçlarla tekrar AI'ya sor
                final = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages
                )
                reply = final.choices[0].message.content
                messages.append({"role": "assistant", "content": reply})
            else:
                reply = msg.content
                messages.append(msg)
            
            print(f"\nAsistan: {reply}\n")
            
        except KeyboardInterrupt:
            print("\n\nÇıkış yapılıyor...")
            break
        except Exception as e:
            logger.error(f"Hata: {e}")
            print(f"\n❌ Bir hata oluştu: {e}\n")
    
    # Temizlik
    if browser_agent:
        browser_agent.close()
    db.close()
    print("\n👋 Görüşmek üzere!")


if __name__ == "__main__":
    chat_with_groq()