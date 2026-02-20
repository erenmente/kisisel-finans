import os
import json
import requests
import time
import yfinance as yf
from bs4 import BeautifulSoup
from groq import Groq
import urllib3
import sys
from database import PortfolioDB
from dotenv import load_dotenv

# --- AYARLAR ---
load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MODEL_NAME = "llama-3.3-70b-versatile"
API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    sys.exit("HATA: .env dosyasında GROQ_API_KEY bulunamadı.")

# Terminal Temizliği
class SuppressOutput:
    def __enter__(self):
        self._original_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr.close()
        sys.stderr = self._original_stderr

db = PortfolioDB()

# --- 1. TEFAS FONKSİYONU ---
def _check_tefas(code):
    url = f"https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod={code}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    for i in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                price = soup.find("span", {"id": "MainContent_PanelInfo_lblPrice"})
                title = soup.find("span", {"id": "MainContent_PanelInfo_lblFundTitle"})
                if price and title and price.text.strip():
                    return {"symbol": code, "title": title.text.strip(), "price": price.text.strip(), "source": "TEFAS"}
        except: time.sleep(1)
    return None

# --- 2. BLOOMBERG HT ---
def _check_bloomberg(code):
    url = f"https://www.bloomberght.com/yatirim-fonu/{code.lower()}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            price_box = soup.find("span", class_="value")
            if not price_box and soup.title:
                title_parts = soup.title.string.split("|")
                if len(title_parts) > 1:
                    return {"symbol": code, "title": "Bloomberg Fon", "price": title_parts[-1].strip(), "source": "Bloomberg HT"}
            if price_box:
                return {"symbol": code, "title": "Yatırım Fonu", "price": price_box.text.strip(), "source": "Bloomberg HT"}
    except: pass
    return None

# --- 3. YAHOO FINANCE ---
def _check_yahoo(symbol):
    mapping = {"USD": "TRY=X", "DOLAR": "TRY=X", "EUR": "EURTRY=X", "ALTIN": "GC=F", "BITCOIN": "BTC-USD"}
    symbol = mapping.get(symbol, symbol)
    with SuppressOutput():
        try:
            ticker = yf.Ticker(symbol)
            price = None
            if hasattr(ticker, 'fast_info'): price = ticker.fast_info.last_price
            if price is None:
                hist = ticker.history(period="1d")
                if not hist.empty: price = hist['Close'].iloc[-1]
            if price:
                return {"symbol": symbol, "price": round(price, 2), "currency": "TRY", "source": "Global Piyasa"}
        except: pass
    return None

# --- YÖNETİCİ FONKSİYON ---
def get_financial_data(query):
    query = query.upper().strip()
    print(f"[SİSTEM] 🔍 '{query}' aranıyor...")
    
    # ADIM 1: TEFAS
    if len(query) == 3:
        res = _check_tefas(query)
        if res: return json.dumps(res, ensure_ascii=False)
        print(f"[SİSTEM] ⚠️ TEFAS yanıt vermedi, Bloomberg deneniyor...")
        res = _check_bloomberg(query)
        if res: return json.dumps(res, ensure_ascii=False)
    
    # ADIM 2: BIST
    if "." not in query:
        res = _check_yahoo(f"{query}.IS")
        if res: return json.dumps(res)
    
    # ADIM 3: GLOBAL
    res = _check_yahoo(query)
    if res: return json.dumps(res)
    
    # Hata döndürme, boş döndür ki AI yorumlasın
    return json.dumps({"error": f"'{query}' verisi bulunamadı, farklı bir sembol dene."})

# --- DİĞER FONKSİYONLAR ---
def add_investment(sembol, miktar, maliyet):
    print(f"[SİSTEM] 💾 Kaydediliyor...")
    return json.dumps({"msg": db.ekle(sembol, miktar, maliyet)})

def get_portfolio():
    print(f"[SİSTEM] 📂 Portföy okunuyor...")
    return json.dumps(db.getir())

# --- AI YAPILANDIRMASI (RESET MODE) ---
client = Groq(api_key=API_KEY)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_financial_data",
            "description": "Verilen sembolün (Hisse, Fon, Altın) fiyatını getirir.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "query": {"type": "string", "description": "Sembol (Örn: TTE, ASELS, USD)"}
                }, 
                "required": ["query"]
            }
        }
    },
    {
        "type": "function", 
        "function": {"name": "add_investment", "description": "Portföye ekler.", "parameters": {"type": "object", "properties": {"sembol": {"type": "string"}, "miktar": {"type": "number"}, "maliyet": {"type": "number"}}, "required": ["sembol", "miktar", "maliyet"]}}
    },
    {
        "type": "function", 
        "function": {"name": "get_portfolio", "description": "Mevcut portföyü listeler.", "parameters": {"type": "object", "properties": {}, "required": []}}
    }
]

def chat_with_groq():
    # SİSTEM TALİMATI (ÇOK BASİTLEŞTİRİLDİ - HATAYI ÖNLEMEK İÇİN)
    system_prompt = """
    Sen Eren'in Finans Asistanısın.
    
    Görevlerin:
    1. Kullanıcının sorduğu sembollerin fiyatını 'get_financial_data' aracıyla bul.
    2. Eğer kullanıcı genel yatırım tavsiyesi isterse (Örn: "Ne alayım?", "Hisselere bak"):
       - Kendin bir analiz yapamazsın.
       - Ancak şunu yapabilirsin: "Senin için popüler araçları kontrol edeyim" de ve şu sembolleri sırayla kontrol et: THYAO, ASELS, TTE, YAS, ALTIN.
       - Sonra bu fiyatlara göre yorum yap.
    
    Kurallar:
    - 1.017 sayısı ondalıktır.
    - Cevapların kısa ve Türkçe olsun.
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    print(f"--- EREN'İN ASİSTANI (V9 - Clean Slate) ---")
    
    while True:
        try:
            user_input = input("\nSen: ")
            if user_input.lower() in ['q', 'exit']: break
            
            messages.append({"role": "user", "content": user_input})
            
            response = client.chat.completions.create(
                model=MODEL_NAME, messages=messages, tools=tools, tool_choice="auto"
            )
            msg = response.choices[0].message
            
            # Tool Çağrısı Var mı?
            if msg.tool_calls:
                for tool in msg.tool_calls:
                    try:
                        args = json.loads(tool.function.arguments)
                    except: continue

                    if tool.function.name == "get_financial_data": 
                        # Yine de güvenlik: İlk kelimeyi al
                        raw_query = args['query'].split()[0].replace(",", "").strip()
                        data = get_financial_data(raw_query)
                        
                    elif tool.function.name == "add_investment": 
                        data = add_investment(args['sembol'], args['miktar'], args['maliyet'])
                    elif tool.function.name == "get_portfolio": 
                        data = get_portfolio()
                    
                    messages.append(msg)
                    messages.append({"role": "tool", "tool_call_id": tool.id, "content": data})
                
                final = client.chat.completions.create(model=MODEL_NAME, messages=messages)
                print(f"Asistan: {final.choices[0].message.content}")
            else:
                print(f"Asistan: {msg.content}")
                messages.append(msg)
                
        except Exception as e: 
            print(f"Hata: {e}")

if __name__ == "__main__":
    chat_with_groq()