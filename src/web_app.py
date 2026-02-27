"""
Finans Asistanı - Web API & Çoklu Sayfa Arayüz v3
Flask tabanlı modern web uygulaması
Yeni: AI Chatbot, Grafikler, Alarmlar, Performans, Tema
"""

import os
import sys
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Proje modüllerini ekle
sys.path.insert(0, os.path.dirname(__file__))

from database import PortfolioDB
from utils import setup_logger

# Veri çekme
import yfinance as yf
from tefas import Crawler
import urllib3
urllib3.disable_warnings()

# Groq AI
try:
    from groq import Groq
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
except Exception:
    groq_client = None

# Flask
app = Flask(__name__, 
    template_folder='../web/templates',
    static_folder='../web/static',
    static_url_path='/static'
)
CORS(app)

# --- ALT DİZİN (SUBDIRECTORY) DESTEĞİ ---
# Bu bölge, uygulamanın erenmente.com/finans altında çalışmasını sağlar.
class PrefixMiddleware(object):
    def __init__(self, app, prefix=''):
        self.app = app
        self.prefix = prefix
    def __call__(self, environ, start_response):
        if environ['PATH_INFO'].startswith(self.prefix):
            environ['PATH_INFO'] = environ['PATH_INFO'][len(self.prefix):]
            environ['SCRIPT_NAME'] = self.prefix
            return self.app(environ, start_response)
        else:
            # Canlıda Vercel/Render rewrite kullanıyorsak bazen prefix gelmez, 
            # ancak linklerin doğru üretilmesi için SCRIPT_NAME set edilmelidir.
            if os.getenv('FORCE_SCRIPT_NAME'):
                environ['SCRIPT_NAME'] = os.getenv('FORCE_SCRIPT_NAME')
            return self.app(environ, start_response)

app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix='/finans')
# ---------------------------------------

# Logger & DB
logger = setup_logger("WebAPI", logging.INFO)

# Veritabanı - Supabase (PostgreSQL) URL üzerinden çalışır
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
try:
    db = PortfolioDB()
except Exception as e:
    logger.error(f"Veritabanı başlatılamadı: {e}")
    db = None

# Chat geçmişi (session bazlı, basit in-memory)
chat_sessions = {}

# Fiyat alarmları (in-memory, JSON dosyasıyla persist)
ALERTS_FILE = os.path.join("/tmp", "alarmlar.json") if os.environ.get("VERCEL") or os.environ.get("VERCEL_REGION") else os.path.join(BASE_DIR, "alarmlar.json")
price_alerts = []

def load_alerts():
    global price_alerts
    try:
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, 'r', encoding='utf-8') as f:
                price_alerts = json.load(f)
    except Exception:
        price_alerts = []

def save_alerts():
    try:
        with open(ALERTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(price_alerts, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Alarm kayıt hatası: {e}")

load_alerts()


# ============================================================
# VERİ ÇEKME FONKSİYONLARI
# ============================================================

def get_tefas_price(code: str) -> dict:
    """TEFAS fon fiyatı"""
    try:
        crawler = Crawler()
        today = datetime.now()
        start = today - timedelta(days=5)
        
        data = crawler.fetch(
            start=start.strftime("%Y-%m-%d"),
            end=today.strftime("%Y-%m-%d"),
            name=code.upper()
        )
        
        if not data.empty:
            latest = data.iloc[-1]
            return {
                "success": True,
                "symbol": code.upper(),
                "name": latest.get("Fon Adı", code),
                "price": round(float(latest["Fiyat"]), 4),
                "date": str(latest.get("Tarih", today.strftime("%Y-%m-%d"))),
                "source": "TEFAS"
            }
    except Exception as e:
        logger.warning(f"TEFAS hatası: {e}")
    
    return {"success": False, "error": f"{code} bulunamadı"}


def get_stock_price(symbol: str) -> dict:
    """Hisse fiyatı"""
    try:
        bist_symbol = f"{symbol}.IS" if "." not in symbol else symbol
        
        old_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')
        
        ticker = yf.Ticker(bist_symbol)
        price = getattr(ticker.fast_info, 'last_price', None)
        
        sys.stderr = old_stderr
        
        if price:
            return {
                "success": True,
                "symbol": symbol.upper(),
                "price": round(float(price), 2),
                "currency": "TRY",
                "source": "Yahoo Finance"
            }
    except Exception as e:
        logger.warning(f"Hisse hatası: {e}")
    
    return {"success": False, "error": f"{symbol} bulunamadı"}


def get_currency_rate(currency: str) -> dict:
    """Döviz kuru"""
    mapping = {
        "USD": "USDTRY=X",
        "EUR": "EURTRY=X",
        "GBP": "GBPTRY=X"
    }
    
    names = {
        "USD": "Amerikan Doları",
        "EUR": "Euro",
        "GBP": "İngiliz Sterlini"
    }
    
    try:
        yahoo_symbol = mapping.get(currency.upper(), f"{currency.upper()}TRY=X")
        
        old_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')
        
        ticker = yf.Ticker(yahoo_symbol)
        price = getattr(ticker.fast_info, 'last_price', None)
        
        sys.stderr = old_stderr
        
        if price:
            return {
                "success": True,
                "symbol": currency.upper(),
                "name": names.get(currency.upper(), currency),
                "price": round(float(price), 4),
                "currency": "TRY",
                "source": "Yahoo Finance"
            }
    except Exception as e:
        logger.warning(f"Döviz hatası: {e}")
    
    return {"success": False, "error": f"{currency} bulunamadı"}


def get_gold_price() -> dict:
    """Gram altın fiyatı - Çoklu kaynak"""
    import requests
    from bs4 import BeautifulSoup
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # Kaynak 1: Bigpara (en güvenilir Türk kaynağı)
    try:
        r = requests.get("https://bigpara.hurriyet.com.tr/altin/gram-altin-fiyati/", 
                        headers=headers, timeout=8)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, "html.parser")
            price_elem = soup.find("span", class_="value")
            if price_elem:
                price_text = price_elem.text.strip().replace(".", "").replace(",", ".")
                price = float(price_text)
                if price > 0:
                    return {
                        "success": True,
                        "symbol": "ALTIN",
                        "name": "Gram Altın",
                        "price": round(price, 2),
                        "currency": "TRY",
                        "source": "Bigpara"
                    }
    except Exception as e:
        logger.debug(f"Bigpara altın hatası: {e}")
    
    # Kaynak 2: Doviz.com
    try:
        r = requests.get("https://www.doviz.com/altin/gram-altin", 
                        headers=headers, timeout=8)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, "html.parser")
            price_div = soup.find("div", class_="value")
            if price_div:
                price_text = price_div.text.strip().replace(".", "").replace(",", ".")
                price = float(price_text)
                if price > 0:
                    return {
                        "success": True,
                        "symbol": "ALTIN",
                        "name": "Gram Altın",
                        "price": round(price, 2),
                        "currency": "TRY",
                        "source": "Doviz.com"
                    }
    except Exception as e:
        logger.debug(f"Doviz.com altın hatası: {e}")
    
    # Kaynak 3: Yahoo Finance hesaplama (fallback)
    try:
        old_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')
        
        gold = yf.Ticker("GC=F")
        usd = yf.Ticker("USDTRY=X")
        
        gold_price = getattr(gold.fast_info, 'last_price', None)
        usd_price = getattr(usd.fast_info, 'last_price', None)
        
        sys.stderr = old_stderr
        
        if gold_price and usd_price:
            gram_try = (gold_price * usd_price) / 31.1035
            return {
                "success": True,
                "symbol": "ALTIN",
                "name": "Gram Altın",
                "price": round(gram_try, 2),
                "currency": "TRY",
                "source": "Hesaplanan (Yahoo Finance)"
            }
    except Exception as e:
        logger.warning(f"Yahoo altın hatası: {e}")
    
    return {"success": False, "error": "Altın fiyatı alınamadı"}

# ============================================================
# FİYAT ÖNBELLEĞİ (CACHE)
# ============================================================
#
# Amaç: Aynı sembol kısa sürede tekrar sorulduğunda dış API'ye
# gitmek yerine bellekteki sonucu döndürmek.
#
# Yapı:
#   price_cache = {
#       "USD": {"data": {...}, "timestamp": 1709100000},
#       "EUR": {"data": {...}, "timestamp": 1709100005},
#   }
#
# Her sembol için son çekilen veri ve zamanı tutulur.
# TTL (Time To Live) = 60 saniye. 60sn geçtiyse yeniden çekilir.

price_cache = {}          # Önbellek sözlüğü
CACHE_TTL = 60            # Önbellek süresi (saniye)


def get_price_for_symbol(symbol: str) -> dict:
    """
    Genel fiyat çekme fonksiyonu.
    Tüm fiyat sorguları bu fonksiyondan geçer.
    Cache mantığı:
      1. Önbellekte var mı ve süresi dolmamış mı? → Var: hemen döndür
      2. Yok veya süre dolmuş → Dış API'den çek, önbelleğe kaydet, döndür
    """
    symbol = symbol.upper().strip()

    # --- CACHE KONTROLÜ ---
    # time.time() = şu anki zamanı saniye cinsinden verir (Unix timestamp)
    # Eğer sembol önbellekte varsa VE son çekilme zamanı 60sn'den yakınsa → döndür
    cached = price_cache.get(symbol)
    if cached and (time.time() - cached["timestamp"]) < CACHE_TTL:
        logger.debug(f"Cache HIT: {symbol} ({CACHE_TTL}sn önbellek)")
        return cached["data"]

    # --- CACHE MISS: Dış API'den fiyatı çek ---
    logger.debug(f"Cache MISS: {symbol} → API'den çekiliyor")

    if symbol in ["ALTIN", "GOLD", "XAU"]:
        result = get_gold_price()

    elif symbol in ["USD", "EUR", "GBP", "DOLAR", "EURO"]:
        if symbol == "DOLAR": symbol = "USD"
        elif symbol == "EURO": symbol = "EUR"
        result = get_currency_rate(symbol)

    elif len(symbol) == 3:
        result = get_tefas_price(symbol)
        if not result.get("success"):
            result = get_stock_price(symbol)
    else:
        result = get_stock_price(symbol)

    # --- BAŞARILI SONUCU ÖNBELLEĞE KAYDET ---
    # Sadece başarılı sonuçları cache'liyoruz.
    # Hatalı sonuçları cache'lersek kullanıcı 60sn boyunca hata görür.
    if result.get("success"):
        price_cache[symbol] = {
            "data": result,
            "timestamp": time.time()    # Şu anki zamanı kaydet
        }

    return result


# ============================================================
# PAGE ROUTES
# ============================================================

@app.route('/')
def page_dashboard():
    """Dashboard sayfası"""
    return render_template('dashboard.html', active_page='dashboard')


@app.route('/portfolio')
def page_portfolio():
    """Portföy sayfası"""
    return render_template('portfolio.html', active_page='portfolio')


@app.route('/market')
def page_market():
    """Piyasa sayfası"""
    return render_template('market.html', active_page='market')


@app.route('/history')
def page_history():
    """İşlem geçmişi sayfası"""
    return render_template('history.html', active_page='history')


# ============================================================
# API ROUTES
# ============================================================

@app.route('/favicon.ico')
def favicon():
    """Favicon"""
    return '', 204


@app.errorhandler(500)
def internal_error(error):
    """500 hata yakalayıcı"""
    logger.error(f"500 Hatası: {error}")
    return jsonify({"success": False, "error": "Sunucu hatası oluştu"}), 500


@app.route('/api/price/<symbol>')
def api_price(symbol: str):
    """Fiyat sorgula"""
    try:
        return jsonify(get_price_for_symbol(symbol))
    except Exception as e:
        logger.error(f"Fiyat API hatası: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/portfolio', methods=['GET'])
def api_portfolio():
    """Portföy listesi"""
    try:
        return jsonify({
            "success": True,
            "data": db.getir(),
            "summary": db.ozet()
        })
    except Exception as e:
        logger.error(f"Portföy API hatası: {e}")
        return jsonify({"success": False, "error": str(e), "data": [], "summary": {}})


@app.route('/api/portfolio/add', methods=['POST'])
def api_portfolio_add():
    """Portföye ekle"""
    try:
        data = request.json
        sembol = data.get('symbol', '').upper()
        miktar = float(data.get('amount', 0))
        maliyet = float(data.get('cost', 0))
        
        if not sembol or miktar <= 0 or maliyet <= 0:
            return jsonify({"success": False, "error": "Geçersiz parametreler"})
        
        result = db.ekle(sembol, miktar, maliyet)
        return jsonify({"success": True, "message": result})
    except Exception as e:
        logger.error(f"Ekleme hatası: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/portfolio/sell', methods=['POST'])
def api_portfolio_sell():
    """Satış yap"""
    try:
        data = request.json
        sembol = data.get('symbol', '').upper()
        miktar = float(data.get('amount', 0))
        fiyat = float(data.get('price', 0))
        
        if not sembol or miktar <= 0 or fiyat <= 0:
            return jsonify({"success": False, "error": "Geçersiz parametreler"})
        
        result = db.sat(sembol, miktar, fiyat)
        return jsonify({"success": True, "message": result})
    except Exception as e:
        logger.error(f"Satış hatası: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/portfolio/delete/<symbol>', methods=['DELETE'])
def api_portfolio_delete(symbol: str):
    """Sembol sil"""
    try:
        result = db.sil(symbol.upper())
        return jsonify({"success": True, "message": result})
    except Exception as e:
        logger.error(f"Silme hatası: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/history')
def api_history():
    """İşlem geçmişi"""
    try:
        return jsonify({
            "success": True,
            "data": db.islem_gecmisi(limit=100)
        })
    except Exception as e:
        logger.error(f"Geçmiş API hatası: {e}")
        return jsonify({"success": False, "error": str(e), "data": []})


# ============================================================
# CSV DIŞA AKTARMA
# ============================================================
#
# Bu endpoint portföy verilerini CSV formatında döndürür.
# CSV (Comma-Separated Values) = virgülle ayrılmış değerler dosyası.
# Excel, Google Sheets gibi programlarla doğrudan açılabilir.
#
# Akış:
# 1. Veritabanından portföy ve işlem geçmişi verilerini çek
# 2. Python'un 'csv' modülü ile bellekte CSV dosyası oluştur
# 3. Response olarak dosya gönder (tarayıcı otomatik indirir)

@app.route('/api/export/csv')
def api_export_csv():
    """Portföy verilerini CSV olarak dışa aktar"""
    import csv       # CSV dosyası oluşturmak için Python standart modülü
    import io        # StringIO: bellekte dosya gibi davranan nesne

    try:
        # 1) StringIO: Gerçek dosya yazmak yerine bellekte string oluşturur
        #    Bu sayede diske yazmadan doğrudan tarayıcıya gönderebiliriz
        output = io.StringIO()

        # 2) BOM (Byte Order Mark): Excel'in Türkçe karakterleri doğru
        #    göstermesi için dosyanın başına özel bir işaret koyuyoruz
        #    Bu olmadan Excel'de "ş, ç, ö, ü" karakterleri bozuk görünür
        output.write('\ufeff')  # UTF-8 BOM

        # 3) CSV writer oluştur: her satırı otomatik virgülle ayırır
        writer = csv.writer(output)

        # === BÖLÜM 1: PORTFÖY VERİLERİ ===

        # 4) Başlık satırı yaz
        writer.writerow(['=== PORTFÖY ==='])
        writer.writerow(['Sembol', 'Adet', 'Ortalama Maliyet (TL)', 'Toplam Maliyet (TL)', 'İlk Alış Tarihi'])

        # 5) Veritabanından portföy verilerini çek
        portfolio = db.getir()

        if portfolio:
            for item in portfolio:
                # Her yatırım için bir satır yaz
                writer.writerow([
                    item.get('sembol', ''),
                    item.get('miktar', ''),
                    item.get('ort_maliyet', ''),
                    item.get('toplam_maliyet', ''),
                    item.get('tarih', '')
                ])
        else:
            writer.writerow(['Portföyde yatırım bulunamadı'])

        # 6) Bölümler arası boş satır bırak
        writer.writerow([])
        writer.writerow([])

        # === BÖLÜM 2: İŞLEM GEÇMİŞİ ===

        writer.writerow(['=== İŞLEM GEÇMİŞİ ==='])
        writer.writerow(['Tarih', 'İşlem', 'Sembol', 'Miktar', 'Fiyat (TL)', 'Kar/Zarar (TL)'])

        # 7) İşlem geçmişini çek (en son 500 işlem)
        history = db.islem_gecmisi(limit=500)

        if history:
            for item in history:
                writer.writerow([
                    item.get('tarih', ''),
                    item.get('islem', ''),
                    item.get('sembol', ''),
                    item.get('miktar', ''),
                    item.get('fiyat', ''),
                    item.get('kar_zarar', '')
                ])

        # 8) Dosya adını tarihe göre oluştur
        #    Örnek: "portfoy_2026-02-28.csv"
        filename = f"portfoy_{datetime.now().strftime('%Y-%m-%d')}.csv"

        # 9) Response oluştur:
        #    - Content-Type: text/csv → tarayıcıya "bu bir CSV dosyası" der
        #    - Content-Disposition: attachment → "bunu indir, gösterme" der
        #    - filename: indirilen dosyanın adını ayarlar
        from flask import Response
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )
        return response

    except Exception as e:
        logger.error(f"CSV export hatası: {e}")
        return jsonify({"success": False, "error": str(e)})

# ============================================================
# AI CHATBOT API
# ============================================================

CHAT_SYSTEM_PROMPT = """Sen Eren'in akıllı Finans Asistanısın. Web arayüzünden konuşuyorsun.

📌 Görevlerin:
1. Yatırım tavsiyeleri ver (genel bilgi, yatırım danışmanlığı değil)
2. Portföy analizi yap
3. Piyasa yorumları yap
4. Finansal kavramları açıkla

📌 Kurallar:
- Türkçe cevap ver
- Kısa ve öz ol (max 3-4 paragraf)
- Emoji kullan
- "Bu yatırım tavsiyesi değildir" uyarısını gerektiğinde ekle
- Portföy verileri sana gönderilecek, bunları analiz edebilirsin
- Markdown formatında cevap ver (kalın, liste vs.)

📌 Önemli:
- Kullanıcının portföy bilgileri context olarak verilecek
- Fiyat verileri de paylaşılacak
- Bunlara dayanarak analiz ve yorum yap
"""


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """AI Chatbot endpoint"""
    try:
        if not groq_client:
            return jsonify({
                "success": False, 
                "error": "AI servisi yapılandırılmamış. .env dosyasında GROQ_API_KEY olmalı."
            })
        
        data = request.json
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        
        if not user_message:
            return jsonify({"success": False, "error": "Mesaj boş olamaz"})
        
        # Portföy bilgilerini context olarak ekle
        portfolio_context = ""
        try:
            portfolio = db.getir()
            summary = db.ozet()
            if portfolio:
                portfolio_context = f"\n\n📊 Kullanıcının Portföyü:\n"
                portfolio_context += f"Toplam Maliyet: {summary.get('toplam_maliyet', 0)} TL\n"
                portfolio_context += f"Sembol Sayısı: {summary.get('sembol_sayisi', 0)}\n"
                for p in portfolio:
                    portfolio_context += f"- {p['sembol']}: {p['adet']} adet, ort. {p['alis_fiyati']} TL, toplam {p['toplam_maliyet']} TL\n"
        except Exception:
            pass
        
        # Chat geçmişini al veya oluştur
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        
        messages = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT + portfolio_context}
        ]
        
        # Son 10 mesajı ekle (context window'u aşmasın)
        messages.extend(chat_sessions[session_id][-10:])
        messages.append({"role": "user", "content": user_message})
        
        # Groq API çağrısı
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=1024,
            temperature=0.7
        )
        
        ai_reply = response.choices[0].message.content
        
        # Geçmişe kaydet
        chat_sessions[session_id].append({"role": "user", "content": user_message})
        chat_sessions[session_id].append({"role": "assistant", "content": ai_reply})
        
        # Max 20 mesaj tut
        if len(chat_sessions[session_id]) > 20:
            chat_sessions[session_id] = chat_sessions[session_id][-20:]
        
        return jsonify({
            "success": True,
            "reply": ai_reply
        })
    except Exception as e:
        logger.error(f"Chat API hatası: {e}")
        return jsonify({"success": False, "error": f"AI hatası: {str(e)}"})


@app.route('/api/chat/clear', methods=['POST'])
def api_chat_clear():
    """Chat geçmişini temizle"""
    session_id = request.json.get('session_id', 'default')
    chat_sessions[session_id] = []
    return jsonify({"success": True})


# ============================================================
# PORTFÖY PERFORMANS API
# ============================================================

@app.route('/api/portfolio/performance')
def api_portfolio_performance():
    """Portföy performans verileri - anlık fiyatlarla karşılaştırma"""
    try:
        portfolio = db.getir()
        if not portfolio:
            return jsonify({"success": True, "data": [], "total": {}})
        
        performance_data = []
        toplam_maliyet = 0
        toplam_guncel = 0
        
        for p in portfolio:
            item = {
                "sembol": p["sembol"],
                "adet": p["adet"],
                "alis_fiyati": p["alis_fiyati"],
                "toplam_maliyet": p["toplam_maliyet"],
                "guncel_fiyat": None,
                "guncel_deger": None,
                "kar_zarar": None,
                "kar_zarar_yuzde": None
            }
            
            # Anlık fiyat çek
            try:
                price_data = get_price_for_symbol(p["sembol"])
                if price_data.get("success"):
                    guncel = price_data["price"]
                    item["guncel_fiyat"] = guncel
                    item["guncel_deger"] = round(guncel * p["adet"], 2)
                    item["kar_zarar"] = round(item["guncel_deger"] - p["toplam_maliyet"], 2)
                    if p["toplam_maliyet"] > 0:
                        item["kar_zarar_yuzde"] = round((item["kar_zarar"] / p["toplam_maliyet"]) * 100, 2)
                    
                    toplam_guncel += item["guncel_deger"]
            except Exception:
                pass
            
            toplam_maliyet += p["toplam_maliyet"]
            performance_data.append(item)
        
        toplam_kar = round(toplam_guncel - toplam_maliyet, 2) if toplam_guncel > 0 else None
        toplam_yuzde = round((toplam_kar / toplam_maliyet) * 100, 2) if toplam_maliyet > 0 and toplam_kar is not None else None
        
        return jsonify({
            "success": True,
            "data": performance_data,
            "total": {
                "toplam_maliyet": round(toplam_maliyet, 2),
                "toplam_guncel": round(toplam_guncel, 2) if toplam_guncel > 0 else None,
                "toplam_kar_zarar": toplam_kar,
                "kar_zarar_yuzde": toplam_yuzde
            }
        })
    except Exception as e:
        logger.error(f"Performans API hatası: {e}")
        return jsonify({"success": False, "error": str(e)})


# ============================================================
# FİYAT ALARMLARI API
# ============================================================

@app.route('/api/alerts', methods=['GET'])
def api_alerts_list():
    """Alarmları listele"""
    return jsonify({"success": True, "data": price_alerts})


@app.route('/api/alerts', methods=['POST'])
def api_alerts_add():
    """Alarm ekle"""
    try:
        data = request.json
        alert = {
            "id": int(datetime.now().timestamp() * 1000),
            "symbol": data.get('symbol', '').upper(),
            "condition": data.get('condition', 'above'),  # 'above' veya 'below'
            "target_price": float(data.get('target_price', 0)),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "triggered": False
        }
        
        if not alert["symbol"] or alert["target_price"] <= 0:
            return jsonify({"success": False, "error": "Geçersiz parametreler"})
        
        price_alerts.append(alert)
        save_alerts()
        
        return jsonify({"success": True, "alert": alert})
    except Exception as e:
        logger.error(f"Alarm ekleme hatası: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/alerts/<int:alert_id>', methods=['DELETE'])
def api_alerts_delete(alert_id: int):
    """Alarm sil"""
    global price_alerts
    price_alerts = [a for a in price_alerts if a["id"] != alert_id]
    save_alerts()
    return jsonify({"success": True})


@app.route('/api/alerts/check')
def api_alerts_check():
    """Alarmları kontrol et"""
    try:
        triggered = []
        for alert in price_alerts:
            if alert["triggered"]:
                continue
            
            try:
                price_data = get_price_for_symbol(alert["symbol"])
                if price_data.get("success"):
                    current_price = price_data["price"]
                    
                    should_trigger = False
                    if alert["condition"] == "above" and current_price >= alert["target_price"]:
                        should_trigger = True
                    elif alert["condition"] == "below" and current_price <= alert["target_price"]:
                        should_trigger = True
                    
                    if should_trigger:
                        alert["triggered"] = True
                        alert["triggered_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        alert["current_price"] = current_price
                        triggered.append(alert)
            except Exception:
                pass
        
        if triggered:
            save_alerts()
        
        return jsonify({"success": True, "triggered": triggered})
    except Exception as e:
        logger.error(f"Alarm kontrol hatası: {e}")
        return jsonify({"success": False, "error": str(e)})


# ============================================================
# RUN
# ============================================================

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("  🚀 FİNANS ASİSTANI WEB ARAYÜZÜ v3")
    print("=" * 50)
    print("  📍 http://localhost:5000")
    print("  📄 Sayfalar:")
    print("     / ............ Dashboard")
    print("     /portfolio ... Portföy")
    print("     /market ...... Piyasa")
    print("     /history ..... İşlem Geçmişi")
    print("  🤖 AI Chatbot:  Aktif" if groq_client else "  🤖 AI Chatbot:  Pasif (GROQ_API_KEY yok)")
    print("=" * 50 + "\n")
    
    app.run(debug=True, port=5000, use_reloader=False)
