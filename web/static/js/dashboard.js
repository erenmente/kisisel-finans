/**
 * Dashboard Page JavaScript v3
 * Charts, Performance, Alerts, Auto-refresh
 */

let portfolioChart = null;
let autoRefreshInterval = null;

// ============================================================
// DASHBOARD STATS
// ============================================================

async function loadDashboardStats() {
    try {
        const data = await API.get('/api/portfolio');
        if (data.success) {
            const summary = data.summary || {};
            document.getElementById('totalValue').textContent = UI.formatCurrency(summary.toplam_maliyet || 0);
            document.getElementById('positionCount').textContent = `${summary.sembol_sayisi || 0} Yatırım`;
        } else {
            document.getElementById('totalValue').textContent = '0,00 ₺';
            document.getElementById('positionCount').textContent = '0 Yatırım';
        }
    } catch (e) {
        console.error('Dashboard stats error:', e);
    }

    try {
        const history = await API.get('/api/history');
        if (history.success) {
            document.getElementById('transactionCount').textContent = `${history.data?.length || 0} İşlem`;
        }
    } catch (e) {
        document.getElementById('transactionCount').textContent = '0 İşlem';
    }
}

// ============================================================
// PORTFOLIO CHART (Pasta Grafiği)
// ============================================================

async function loadPortfolioChart() {
    try {
        const data = await API.get('/api/portfolio');
        const chartCanvas = document.getElementById('portfolioChart');
        const chartEmpty = document.getElementById('chartEmpty');

        if (!data.success || !data.data?.length) {
            if (chartCanvas) chartCanvas.classList.add('hidden');
            if (chartEmpty) chartEmpty.classList.remove('hidden');
            return;
        }

        if (chartCanvas) chartCanvas.classList.remove('hidden');
        if (chartEmpty) chartEmpty.classList.add('hidden');

        const portfolio = data.data;
        const labels = portfolio.map(p => p.sembol);
        const values = portfolio.map(p => p.toplam_maliyet);

        const colors = [
            '#6366f1', '#8b5cf6', '#a855f7', '#ec4899',
            '#f43f5e', '#f97316', '#eab308', '#22c55e',
            '#14b8a6', '#06b6d4', '#3b82f6', '#6366f1'
        ];

        if (portfolioChart) {
            portfolioChart.destroy();
        }

        const ctx = chartCanvas.getContext('2d');
        portfolioChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors.slice(0, labels.length),
                    borderColor: 'rgba(10, 10, 15, 0.8)',
                    borderWidth: 2,
                    hoverBorderWidth: 3,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: getComputedStyle(document.documentElement)
                                .getPropertyValue('--color-text-secondary').trim() || '#a0a0b0',
                            font: { family: 'Inter', size: 12 },
                            padding: 15,
                            usePointStyle: true,
                            pointStyleWidth: 10
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(18, 18, 26, 0.95)',
                        titleColor: '#fff',
                        bodyColor: '#a0a0b0',
                        borderColor: 'rgba(99, 102, 241, 0.3)',
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 12,
                        callbacks: {
                            label: function (context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const pct = ((context.parsed / total) * 100).toFixed(1);
                                return ` ${context.label}: ${UI.formatCurrency(context.parsed)} (${pct}%)`;
                            }
                        }
                    }
                },
                animation: {
                    animateRotate: true,
                    duration: 800
                }
            }
        });
    } catch (e) {
        console.error('Chart error:', e);
    }
}

// ============================================================
// PORTFOLIO PERFORMANCE (Kar/Zarar)
// ============================================================

async function loadPerformance() {
    const container = document.getElementById('performanceSummary');
    if (!container) return;

    container.innerHTML = `
        <div class="perf-loading">
            <div class="loading-spinner"></div>
            <span>Fiyatlar yükleniyor...</span>
        </div>
    `;

    try {
        const data = await API.get('/api/portfolio/performance');

        if (!data.success || !data.data?.length) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📈</div>
                    <div class="empty-state-text">Performans verisi yok</div>
                    <div class="empty-state-hint">Portföye yatırım ekledikten sonra burada görünecek</div>
                </div>
            `;
            return;
        }

        const total = data.total;
        let html = '';

        // Toplam özet
        if (total.toplam_kar_zarar !== null) {
            const isPositive = total.toplam_kar_zarar >= 0;
            html += `
                <div class="perf-total ${isPositive ? 'positive' : 'negative'}">
                    <div class="perf-total-label">Toplam Kar/Zarar</div>
                    <div class="perf-total-value">${isPositive ? '+' : ''}${UI.formatCurrency(total.toplam_kar_zarar)}</div>
                    <div class="perf-total-pct">${isPositive ? '↑' : '↓'} ${Math.abs(total.kar_zarar_yuzde || 0).toFixed(2)}%</div>
                </div>
                <div class="perf-row perf-summary-row">
                    <span>Toplam Maliyet</span>
                    <span>${UI.formatCurrency(total.toplam_maliyet)}</span>
                </div>
                <div class="perf-row perf-summary-row">
                    <span>Güncel Değer</span>
                    <span>${UI.formatCurrency(total.toplam_guncel)}</span>
                </div>
                <div class="perf-divider"></div>
            `;
        }

        // Her pozisyon
        for (const item of data.data) {
            const hasPrice = item.guncel_fiyat !== null;
            const isPositive = item.kar_zarar >= 0;

            html += `
                <div class="perf-row">
                    <div class="perf-symbol">
                        <span class="symbol-badge">${item.sembol}</span>
                        <span class="perf-amount">${UI.formatNumber(item.adet, 2)} adet</span>
                    </div>
                    <div class="perf-values">
                        ${hasPrice ? `
                            <span class="perf-current">${UI.formatCurrency(item.guncel_fiyat)}</span>
                            <span class="perf-change ${isPositive ? 'positive' : 'negative'}">
                                ${isPositive ? '+' : ''}${UI.formatNumber(item.kar_zarar)} ₺ 
                                (${isPositive ? '+' : ''}${item.kar_zarar_yuzde}%)
                            </span>
                        ` : `
                            <span class="perf-current" style="color: var(--color-text-muted);">Fiyat alınamadı</span>
                        `}
                    </div>
                </div>
            `;
        }

        container.innerHTML = html;
    } catch (e) {
        console.error('Performance error:', e);
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <div class="empty-state-text">Veri yüklenemedi</div>
            </div>
        `;
    }
}

// ============================================================
// QUICK MARKET (Canlı Fiyatlar)
// ============================================================

async function loadQuickMarket() {
    const grid = document.getElementById('quickMarket');
    if (!grid) return;

    const symbols = ['USD', 'EUR', 'ALTIN'];
    const results = [];

    for (const symbol of symbols) {
        try {
            const data = await API.get(`/api/price/${symbol}`);
            if (data.success) {
                data.display_name = symbol === 'USD' ? 'Dolar' : symbol === 'EUR' ? 'Euro' : 'Gram Altın';
                results.push(data);
            }
        } catch (e) {
            console.error(`Market data error for ${symbol}:`, e);
        }
    }

    if (results.length > 0) {
        grid.innerHTML = results.map(createMarketCard).join('');
    } else {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📡</div>
                <div class="empty-state-text">Piyasa verileri yüklenemedi</div>
            </div>
        `;
    }
}

// ============================================================
// PRICE ALERTS (Fiyat Alarmları)
// ============================================================

async function loadAlerts() {
    const list = document.getElementById('alertsList');
    if (!list) return;

    try {
        const data = await API.get('/api/alerts');
        if (!data.success || !data.data?.length) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🔔</div>
                    <div class="empty-state-text">Henüz alarm yok</div>
                    <div class="empty-state-hint">"Alarm Ekle" butonuyla fiyat alarmı oluştur</div>
                </div>
            `;
            return;
        }

        list.innerHTML = data.data.map(alert => {
            const conditionText = alert.condition === 'above' ? '↑ üstüne çıkarsa' : '↓ altına düşerse';
            const statusClass = alert.triggered ? 'triggered' : 'active';
            const statusText = alert.triggered ? '✅ Tetiklendi!' : '⏳ Bekliyor';

            return `
                <div class="alert-item ${statusClass}">
                    <div class="alert-info">
                        <span class="symbol-badge">${alert.symbol}</span>
                        <span class="alert-condition">${UI.formatNumber(alert.target_price, 4)} ₺ ${conditionText}</span>
                    </div>
                    <div class="alert-meta">
                        <span class="alert-status">${statusText}</span>
                        <span class="alert-date">${alert.created_at}</span>
                        <button class="btn btn-sm btn-danger" onclick="deleteAlert(${alert.id})">🗑️</button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Alerts error:', e);
    }
}

async function addAlert(e) {
    e.preventDefault();

    const symbol = document.getElementById('alertSymbol').value.trim().toUpperCase();
    const condition = document.getElementById('alertCondition').value;
    const targetPrice = parseFloat(document.getElementById('alertPrice').value);

    if (!symbol || !targetPrice) {
        UI.showToast('Tüm alanları doldurun', 'error');
        return;
    }

    const data = await API.post('/api/alerts', { symbol, condition, target_price: targetPrice });

    if (data.success) {
        UI.showToast('🔔 Alarm oluşturuldu!');
        closeAlertModal();
        loadAlerts();
        document.getElementById('alertSymbol').value = '';
        document.getElementById('alertPrice').value = '';
    } else {
        UI.showToast(data.error || 'Hata oluştu', 'error');
    }
}

async function deleteAlert(id) {
    const data = await API.delete(`/api/alerts/${id}`);
    if (data.success) {
        UI.showToast('🗑️ Alarm silindi');
        loadAlerts();
    }
}

async function checkAlerts() {
    try {
        const data = await API.get('/api/alerts/check');
        if (data.success && data.triggered?.length > 0) {
            for (const alert of data.triggered) {
                UI.showToast(`🔔 ${alert.symbol} alarm tetiklendi! Fiyat: ${UI.formatNumber(alert.current_price, 4)} ₺`);

                // Browser notification
                if (Notification.permission === 'granted') {
                    new Notification('Fiyat Alarmı! 🔔', {
                        body: `${alert.symbol}: ${alert.current_price} ₺`,
                        icon: '📊'
                    });
                }
            }
            loadAlerts();
        }
    } catch (e) {
        console.error('Alert check error:', e);
    }
}

function openAlertModal() {
    document.getElementById('alertModal').classList.add('active');
}

function closeAlertModal() {
    document.getElementById('alertModal').classList.remove('active');
}

// ============================================================
// RECENT HISTORY
// ============================================================

async function loadRecentHistory() {
    const list = document.getElementById('recentHistory');
    if (!list) return;

    try {
        const data = await API.get('/api/history');

        if (data.success && data.data?.length > 0) {
            list.innerHTML = data.data.slice(0, 5).map(item => {
                const isBuy = item.islem === 'ALIS';
                const icon = isBuy ? '📈' : (item.islem === 'SATIS' ? '📉' : '🔄');
                const iconClass = isBuy ? 'buy' : 'sell';

                return `
                    <div class="history-item">
                        <div class="history-icon ${iconClass}">${icon}</div>
                        <div class="history-info">
                            <div class="history-title">${item.sembol} - ${item.islem}</div>
                            <div class="history-date">${item.tarih}</div>
                        </div>
                        <div class="history-amount">${item.miktar} adet</div>
                    </div>
                `;
            }).join('');
        } else {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📜</div>
                    <div class="empty-state-text">Henüz işlem yok</div>
                    <div class="empty-state-hint">Portföy sayfasından ilk yatırımını ekle</div>
                </div>
            `;
        }
    } catch (e) {
        console.error('Recent history error:', e);
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📜</div>
                <div class="empty-state-text">Henüz işlem yok</div>
            </div>
        `;
    }
}

// ============================================================
// AUTO-REFRESH
// ============================================================

function startAutoRefresh() {
    // Fiyatları 60 saniyede bir güncelle
    autoRefreshInterval = setInterval(() => {
        loadQuickMarket();
        checkAlerts();
    }, 60000);
}

// ============================================================
// INITIALIZE
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    // Load all sections
    loadDashboardStats();
    loadPortfolioChart();
    loadPerformance();
    loadQuickMarket();
    loadAlerts();
    loadRecentHistory();

    // Start auto-refresh
    startAutoRefresh();

    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }

    // Check alerts on load
    setTimeout(checkAlerts, 5000);

    // Alert modal events
    document.getElementById('addAlertBtn')?.addEventListener('click', openAlertModal);
    document.getElementById('closeAlertModal')?.addEventListener('click', closeAlertModal);
    document.getElementById('cancelAlertModal')?.addEventListener('click', closeAlertModal);
    document.getElementById('alertForm')?.addEventListener('submit', addAlert);

    // Performance refresh
    document.getElementById('refreshPerformance')?.addEventListener('click', () => {
        loadPerformance();
        loadPortfolioChart();
        UI.showToast('📊 Performans güncelleniyor...');
    });

    // Alert modal backdrop
    document.querySelector('#alertModal .modal-backdrop')?.addEventListener('click', closeAlertModal);
});

// Global functions
window.deleteAlert = deleteAlert;
