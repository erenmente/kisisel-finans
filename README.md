# 🚀 Finans Asistanı v12 - Web UI & Bulut Sürümü

Yapay zeka detaylarına sahip, **gerçek tarayıcı otomasyonu** ve yepyeni **çoklu sayfa web arayüzü** ile çalışan kişisel finans asistanının Vercel ve Supabase altyapısına uyumlu en son hali.

🟢 **Canlı Demo (Yayında):** [https://kisisel-finans.vercel.app/](https://kisisel-finans.vercel.app/)

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-Web%20App-black?style=flat-square&logo=flask)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=flat-square&logo=supabase)
![Vercel](https://img.shields.io/badge/Vercel-Deployed-black?style=flat-square&logo=vercel)
![Groq](https://img.shields.io/badge/AI-Groq%20LLama%203.3-purple?style=flat-square)

---

## ✨ Özellikler

### 🌐 Browser Agent (Yeni!)
- **Gerçek tarayıcı ile veri çekimi** - JavaScript render'lı sayfaları okuyabilir
- Headless veya görünür modda çalışabilir
- TEFAS, Bloomberg HT, Yahoo Finance desteği

### 📊 Veri Kaynakları
| Kaynak | Desteklenen |
|--------|-------------|
| TEFAS Fonları | ✅ (TTE, YAS, vb.) |
| BIST Hisseleri | ✅ (THYAO, ASELS, vb.) |
| Döviz Kurları | ✅ (USD, EUR) |
| Altın | ✅ (Gram altın TL) |
| Global | ✅ (BTC, yabancı hisseler) |

### 💼 Portföy Yönetimi
- ➕ Yatırım ekleme
- 💰 **Kısmi satış** desteği (FIFO mantığı)
- 📈 Otomatik **kar/zarar hesaplama**
- 📜 İşlem geçmişi takibi
- 📊 Portföy özeti

### 🛡️ Teknik İyileştirmeler
- 📝 Profesyonel logging sistemi (dosya + konsol)
- ⏱️ Rate limiting (API koruması)
- 🔄 Fallback mekanizması (Browser → Requests)

---

## 📦 Kurulum

### 1. Gereksinimleri yükle
```bash
pip install -r requirements.txt
```

### 2. Playwright tarayıcılarını kur
```bash
playwright install chromium
```

### 3. API anahtarını ayarla
`.env` dosyası oluştur:
```env
GROQ_API_KEY=gsk_your_api_key_here
```

---

## 🚀 Kullanım

```bash
cd finans/src
python app.py
```

### 💬 Örnek Komutlar

| Komut | Açıklama |
|-------|----------|
| `TTE fiyatı nedir?` | TEFAS fon fiyatı |
| `THYAO ne kadar?` | BIST hisse fiyatı |
| `Dolar kaç TL?` | Döviz kuru |
| `Altın fiyatı?` | Gram altın TL |
| `100 adet ASELS ekle, maliyet 60.5` | Portföye ekle |
| `50 adet TTE sat, fiyat 1.20` | Kısmi satış |
| `Portföyümü göster` | Portföy listesi |
| `İşlem geçmişim` | Son işlemler |
| `Portföy özetim` | Özet bilgi |

---

## 🔧 Yapılandırma

`app.py` içinde:
```python
USE_BROWSER_AGENT = True   # Browser agent kullan
SHOW_BROWSER = False       # True = tarayıcı görünür açılır
```

---

## 📁 Proje Yapısı

```
finans/
├── src/
│   ├── app.py              # Ana uygulama
│   ├── browser_agent.py    # Playwright tabanlı browser otomasyon
│   ├── database.py         # SQLite portföy yönetimi
│   └── utils/
│       ├── logger.py       # Logging sistemi
│       └── rate_limiter.py # Rate limiting
├── logs/                   # Log dosyaları
├── portfoy.db              # SQLite veritabanı
├── requirements.txt
└── README.md
```

---

## 📝 Changelog

### v11 (Şu anki)
- ✅ Playwright browser agent eklendi
- ✅ Kısmi satış ve kar/zarar hesaplama
- ✅ İşlem geçmişi takibi
- ✅ Profesyonel logging
- ✅ Rate limiting

### v10
- İlk sürüm
- TEFAS, Yahoo, Bloomberg scraping
- Basit portföy yönetimi

---

## 📄 Lisans

MIT License - Kişisel kullanım için serbesttir.
