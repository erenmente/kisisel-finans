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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadCurrencies();
    loadCommodities();
    loadStocks();

    document.getElementById('refreshBtn')?.addEventListener('click', refreshAll);
});
