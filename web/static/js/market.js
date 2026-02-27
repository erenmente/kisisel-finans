/**
 * Market Page JavaScript
 */

async function loadCurrencies() {
    const grid = document.getElementById('currencyGrid');
    if (!grid) return;

    const currencies = [
        { symbol: 'USD', name: 'Amerikan Doları' },
        { symbol: 'EUR', name: 'Euro' }
    ];

    const results = [];

    for (const curr of currencies) {
        const data = await API.get(`/api/price/${curr.symbol}`);
        if (data.success) {
            data.display_name = curr.name;
            results.push(data);
        }
    }

    grid.innerHTML = results.length > 0
        ? results.map(createMarketCard).join('')
        : '<div class="market-card"><p>Veri yüklenemedi</p></div>';
}

async function loadCommodities() {
    const grid = document.getElementById('commodityGrid');
    if (!grid) return;

    const data = await API.get('/api/price/ALTIN');

    if (data.success) {
        data.display_name = 'Gram Altın';
        grid.innerHTML = createMarketCard(data);
    } else {
        grid.innerHTML = '<div class="market-card"><p>Veri yüklenemedi</p></div>';
    }
}

async function loadStocks() {
    const grid = document.getElementById('stockGrid');
    if (!grid) return;

    const stocks = [
        { symbol: 'THYAO', name: 'Türk Hava Yolları' },
        { symbol: 'ASELS', name: 'Aselsan' },
        { symbol: 'KCHOL', name: 'Koç Holding' },
        { symbol: 'SISE', name: 'Şişecam' }
    ];

    const results = [];

    for (const stock of stocks) {
        const data = await API.get(`/api/price/${stock.symbol}`);
        if (data.success) {
            data.display_name = stock.name;
            results.push(data);
        }
    }

    grid.innerHTML = results.length > 0
        ? results.map(createMarketCard).join('')
        : '<div class="market-card"><p>Veri yüklenemedi</p></div>';
}

async function refreshAll() {
    const btn = document.getElementById('refreshBtn');
    btn.disabled = true;
    btn.innerHTML = '<span>⏳</span> Yükleniyor...';

    await Promise.all([
        loadCurrencies(),
        loadCommodities(),
        loadStocks()
    ]);

    btn.disabled = false;
    btn.innerHTML = '<span>🔄</span> Yenile';
    UI.showToast('Veriler güncellendi!');
}

// ============================================================
// DÖVİZ ÇEVİRİCİ
// ============================================================
//
// Çevirici şu adımları izler:
// 1. Kullanıcı miktarı değiştirdiğinde veya birim seçtiğinde tetiklenir
// 2. Debounce: Kullanıcı yazmayı bitirene kadar bekler (500ms)
//    -> Bu sayede her tuş basışında API çağrısı yapılmaz (sunucu koruması)
// 3. Backend'den seçilen birimin güncel fiyatını çeker
// 4. Basit çarpma işlemi: miktar × birim_fiyatı = TL karşılığı
// 5. Sonucu ve kur bilgisini ekranda gösterir

let converterTimeout = null;  // Debounce zamanlayıcısı

async function convertCurrency() {
    // 1) Kullanıcının girdiği miktar ve seçtiği birimi al
    const amount = parseFloat(document.getElementById('converterAmount').value);
    const from = document.getElementById('converterFrom').value;
    const resultValue = document.querySelector('.converter-result-value');
    const info = document.getElementById('converterInfo');

    // 2) Miktar geçerli değilse (boş veya NaN) sonucu sıfırla
    if (!amount || isNaN(amount) || amount <= 0) {
        resultValue.textContent = '-';
        info.textContent = 'Geçerli bir miktar girin';
        return;
    }

    // 3) Yükleniyor göstergesi
    resultValue.textContent = '⏳';
    info.textContent = 'Fiyat çekiliyor...';

    try {
        // 4) Backend'den güncel fiyatı çek
        //    Mevcut /api/price/USD endpoint'ini kullanıyoruz
        //    Yani yeni bir backend endpoint'i yazmaya GEREK YOK!
        const data = await API.get(`/api/price/${from}`);

        if (data.success && data.price) {
            // 5) Çarpma işlemi: miktar × birim fiyatı = TL karşılığı
            //    Örnek: 100 USD × 32.50 = 3.250,00 ₺
            const result = amount * data.price;

            // 6) Sonucu formatlı olarak göster
            resultValue.textContent = UI.formatCurrency(result);

            // 7) Alt bilgi satırında kur oranını göster
            //    Örnek: "1 USD = 32,5000 ₺ • Kaynak: Yahoo Finance"
            info.textContent = `1 ${from} = ${UI.formatNumber(data.price, 4)} ₺ • ${data.source || 'Anlık'}`;
        } else {
            // Fiyat alınamadıysa hata mesajı göster
            resultValue.textContent = '❌';
            info.textContent = data.error || 'Fiyat alınamadı';
        }
    } catch (e) {
        console.error('Converter error:', e);
        resultValue.textContent = '❌';
        info.textContent = 'Bağlantı hatası';
    }
}

// Debounce: Kullanıcı her tuşa bastığında değil,
// yazmayı bitirdikten 500ms sonra API çağrısı yap
// Bu, gereksiz istekleri önler ve sunucuyu korur
function debouncedConvert() {
    clearTimeout(converterTimeout);                // Önceki zamanlayıcıyı iptal et
    converterTimeout = setTimeout(convertCurrency, 500); // 500ms bekle, sonra çevir
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadCurrencies();
    loadCommodities();
    loadStocks();

    document.getElementById('refreshBtn')?.addEventListener('click', refreshAll);

    // Çevirici: miktar değişince veya birim değişince otomatik hesapla
    document.getElementById('converterAmount')?.addEventListener('input', debouncedConvert);
    document.getElementById('converterFrom')?.addEventListener('change', convertCurrency);

    // Sayfa yüklenince varsayılan değerle ilk hesaplamayi yap
    convertCurrency();
});
