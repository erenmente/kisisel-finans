# 🚀 Finans Asistanı v13 - Web UI & Bulut Sürümü

Yapay zeka destekli, **çoklu sayfa web arayüzü** ile çalışan kişisel finans asistanının Vercel ve Supabase altyapısına uyumlu en son hali.

🟢 **Canlı Demo (Yayında):** [https://kisisel-finans.vercel.app/](https://kisisel-finans.vercel.app/)

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-Web%20App-black?style=flat-square&logo=flask)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=flat-square&logo=supabase)
![Vercel](https://img.shields.io/badge/Vercel-Deployed-black?style=flat-square&logo=vercel)
![Groq](https://img.shields.io/badge/AI-Groq%20LLama%203.3-purple?style=flat-square)
![Keep-Alive](https://img.shields.io/badge/Keep--Alive-GitHub%20Actions-2088FF?style=flat-square&logo=github-actions)

---

## ✨ Özellikler

### 📊 Veri Kaynakları

| Kaynak | Desteklenen |
|--------|-------------|
| TEFAS Fonları | ✅ (TTE, YAS, vb.) |
| BIST Hisseleri | ✅ (THYAO, ASELS, vb.) |
| Döviz Kurları | ✅ (USD, EUR, GBP) |
| Altın | ✅ (Gram altın TL) |
| Global | ✅ (BTC, yabancı hisseler) |

### 💼 Portföy Yönetimi

- ➕ Yatırım ekleme & kısmi satış (FIFO mantığı)
- 📈 Otomatik kar/zarar hesaplama
- 📊 Pasta grafiği ve Kar/Zarar çubuk grafiği
- 📜 İşlem geçmişi takibi
- 📤 CSV dışa aktarma (Excel uyumlu)

### 🌐 Piyasa & Araçlar

- 💱 Döviz çevirici (USD, EUR, GBP, Altın → TRY)
- 🔔 Fiyat alarmları (tarayıcı bildirimi)
- 🔄 Otomatik fiyat yenileme (60sn)
- ⚡ API önbelleği (60sn cache)

### 🤖 AI & UX

- 💬 Groq LLama 3.3 entegrasyonu (AI chatbot)
- 🌙 Koyu/açık tema (sistem teması otomatik algılama)
- 📱 Mobil uyumlu tasarım (hamburger menü)
- 🍞 Toast bildirimleri

---

## 🔄 Keep-Alive (Supabase Aktif Tutma)

Supabase ücretsiz plan, **7 gün boyunca hiç istek gelmezse** veritabanını duraklatır.

Bu projeye **GitHub Actions** ile keep-alive çözümü eklenmiştir:

- Her **5 günde bir** otomatik olarak siteye ping atar
- Supabase veritabanını aktif tutar
- Tamamen ücretsizdir

Workflow dosyası: [`.github/workflows/keepalive.yml`](.github/workflows/keepalive.yml)

Manuel test için GitHub'da **Actions → Supabase Keep-Alive → Run workflow** butonunu kullan.

---

## 📦 Kurulum (Yerel Geliştirme)

### 1. Gereksinimleri yükle

```bash
pip install -r requirements.txt
```

### 2. Ortam değişkenlerini ayarla

`.env` dosyası oluştur (`.env.example`'dan kopyala):

```env
DATABASE_URL=postgresql://postgres:[SIFRE]@db.[SUPABASE-ID].supabase.co:5432/postgres
GROQ_API_KEY=gsk_your_api_key_here
```

### 3. Uygulamayı başlat

```bash
cd src
python web_app.py
```

Tarayıcıda `http://localhost:5000` adresini aç.

---

## 🚀 Deployment (Vercel + Supabase)

1. [Supabase](https://supabase.com) üzerinde yeni proje oluştur
2. `DATABASE_URL`'yi Supabase → Settings → Database → Connection String'den kopyala
3. [Vercel](https://vercel.com)'e deploy et
4. Vercel → Settings → Environment Variables'a `DATABASE_URL` ve `GROQ_API_KEY` ekle
5. GitHub Actions keep-alive otomatik devreye girer

---

## 📁 Proje Yapısı

```
finans/
├── .github/
│   └── workflows/
│       └── keepalive.yml   # Supabase keep-alive (her 5 günde bir)
├── src/
│   ├── web_app.py          # Ana Flask uygulaması & API
│   ├── database.py         # PostgreSQL (Supabase) portföy yönetimi
│   └── utils/
│       └── logger.py       # Logging sistemi
├── web/
│   ├── templates/          # HTML sayfaları
│   └── static/
│       ├── css/style.css   # Stil dosyası
│       └── js/             # JavaScript dosyaları
├── vercel.json             # Vercel deployment yapılandırması
├── requirements.txt
└── README.md
```

---

## 📝 Changelog

### v13 (Şu anki)

- ✅ Mobil uyumluluk & hamburger menü
- ✅ Kar/zarar çubuk grafiği (bar chart)
- ✅ Döviz çevirici widget
- ✅ CSV dışa aktarma (Excel uyumlu)
- ✅ API önbelleği (60sn cache)
- ✅ Supabase keep-alive (GitHub Actions)
- ✅ Sistem tema otomatik algılama

### v12

- ✅ Vercel + Supabase deployment
- ✅ AI chatbot entegrasyonu
- ✅ Fiyat alarmları
- ✅ Portföy performans grafiği

### v11

- ✅ Kısmi satış ve kar/zarar hesaplama
- ✅ İşlem geçmişi takibi

---

## 📄 Lisans

MIT License - Kişisel kullanım için serbesttir.
