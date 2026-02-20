/**
 * History Page JavaScript
 */

let allHistory = [];

async function loadHistory() {
    const list = document.getElementById('historyList');
    if (!list) return;

    try {
        const data = await API.get('/api/history');

        if (data.success) {
            allHistory = data.data || [];

            // Update stats
            document.getElementById('totalTransactions').textContent = allHistory.length;
            document.getElementById('buyCount').textContent = allHistory.filter(h => h.islem === 'ALIS').length;
            document.getElementById('sellCount').textContent = allHistory.filter(h => h.islem === 'SATIS').length;

            renderHistory(allHistory);
        } else {
            // API returned success: false
            document.getElementById('totalTransactions').textContent = '0';
            document.getElementById('buyCount').textContent = '0';
            document.getElementById('sellCount').textContent = '0';
            renderHistory([]);
        }
    } catch (e) {
        console.error('History load error:', e);
        document.getElementById('totalTransactions').textContent = '0';
        document.getElementById('buyCount').textContent = '0';
        document.getElementById('sellCount').textContent = '0';
        renderHistory([]);
    }
}

function renderHistory(items) {
    const list = document.getElementById('historyList');

    if (items.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📜</div>
                <div class="empty-state-text">Henüz işlem geçmişi yok</div>
                <div class="empty-state-hint">Portföy sayfasından alış veya satış yaptığında burada görünecek</div>
            </div>
        `;
        return;
    }

    list.innerHTML = items.map(item => {
        let icon, iconClass;

        switch (item.islem) {
            case 'ALIS':
                icon = '📈';
                iconClass = 'buy';
                break;
            case 'SATIS':
                icon = '📉';
                iconClass = 'sell';
                break;
            default:
                icon = '🔄';
                iconClass = 'update';
        }

        const karZarar = item.kar_zarar !== 0 ? `
            <div class="history-profit ${item.kar_zarar >= 0 ? 'positive' : 'negative'}">
                ${item.kar_zarar >= 0 ? '+' : ''}${UI.formatNumber(item.kar_zarar)} ₺
            </div>
        ` : '';

        return `
            <div class="history-item">
                <div class="history-icon ${iconClass}">${icon}</div>
                <div class="history-info">
                    <div class="history-title">
                        <span class="history-symbol">${item.sembol}</span>
                        <span class="history-type">${item.islem}</span>
                    </div>
                    <div class="history-details">
                        ${item.miktar} adet @ ${UI.formatNumber(item.fiyat, 4)} ₺
                    </div>
                    <div class="history-date">${item.tarih}</div>
                </div>
                ${karZarar}
            </div>
        `;
    }).join('');
}

function filterHistory() {
    const symbolFilter = document.getElementById('filterSymbol').value.toUpperCase().trim();
    const typeFilter = document.getElementById('filterType').value;

    let filtered = allHistory;

    if (symbolFilter) {
        filtered = filtered.filter(h => h.sembol.includes(symbolFilter));
    }

    if (typeFilter) {
        filtered = filtered.filter(h => h.islem === typeFilter);
    }

    renderHistory(filtered);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();

    document.getElementById('filterSymbol')?.addEventListener('input', filterHistory);
    document.getElementById('filterType')?.addEventListener('change', filterHistory);
});
