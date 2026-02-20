/**
 * Portfolio Page JavaScript
 */

// Modal functions
function openAddModal() {
    document.getElementById('addModal').classList.add('active');
}

function closeAddModal() {
    document.getElementById('addModal').classList.remove('active');
}

function openSellModal(symbol, maxAmount) {
    document.getElementById('sellSymbol').value = symbol;
    document.getElementById('sellSymbolDisplay').value = symbol;
    document.getElementById('sellAmount').max = maxAmount;
    document.getElementById('sellAmount').placeholder = `Max: ${maxAmount}`;
    document.getElementById('sellModal').classList.add('active');
}

function closeSellModal() {
    document.getElementById('sellModal').classList.remove('active');
}

// Load portfolio data
async function loadPortfolio() {
    const tbody = document.getElementById('portfolioBody');
    if (!tbody) return;

    try {
        const data = await API.get('/api/portfolio');

        if (data.success) {
            const portfolio = data.data || [];
            const summary = data.summary || {};

            // Update summary
            document.getElementById('totalCost').textContent = UI.formatCurrency(summary.toplam_maliyet || 0);
            document.getElementById('symbolCount').textContent = summary.sembol_sayisi || 0;

            if (portfolio.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="6" class="loading-row">
                            <div class="empty-state">
                                <div class="empty-state-icon">💼</div>
                                <div class="empty-state-text">Portföyün henüz boş</div>
                                <div class="empty-state-hint">"Yatırım Ekle" butonuna tıklayarak başla</div>
                            </div>
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = portfolio.map(p => `
                <tr>
                    <td><span class="symbol-badge">${p.sembol}</span></td>
                    <td>${UI.formatNumber(p.adet, 4)}</td>
                    <td>${UI.formatNumber(p.alis_fiyati, 4)} ₺</td>
                    <td><strong>${UI.formatCurrency(p.toplam_maliyet)}</strong></td>
                    <td>${p.ilk_alis || '-'}</td>
                    <td class="action-buttons">
                        <button class="btn btn-sm btn-success" onclick="openSellModal('${p.sembol}', ${p.adet})">💰 Sat</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteInvestment('${p.sembol}')">🗑️</button>
                    </td>
                </tr>
            `).join('');
        } else {
            document.getElementById('totalCost').textContent = '0,00 ₺';
            document.getElementById('symbolCount').textContent = '0';
            tbody.innerHTML = '<tr><td colspan="6" class="loading-row">Veri yüklenemedi</td></tr>';
        }
    } catch (e) {
        console.error('Portfolio load error:', e);
        document.getElementById('totalCost').textContent = '—';
        document.getElementById('symbolCount').textContent = '—';
        tbody.innerHTML = '<tr><td colspan="6" class="loading-row">Bağlantı hatası</td></tr>';
    }
}

// Add investment
async function addInvestment(e) {
    e.preventDefault();

    const symbol = document.getElementById('formSymbol').value.trim().toUpperCase();
    const amount = parseFloat(document.getElementById('formAmount').value);
    const cost = parseFloat(document.getElementById('formCost').value);

    if (!symbol || !amount || !cost) {
        UI.showToast('Tüm alanları doldurun', 'error');
        return;
    }

    const data = await API.post('/api/portfolio/add', { symbol, amount, cost });

    if (data.success) {
        UI.showToast('✅ Yatırım eklendi!');
        closeAddModal();
        loadPortfolio();

        // Clear form
        document.getElementById('formSymbol').value = '';
        document.getElementById('formAmount').value = '';
        document.getElementById('formCost').value = '';
    } else {
        UI.showToast(data.error || 'Hata oluştu', 'error');
    }
}

// Sell investment
async function sellInvestment(e) {
    e.preventDefault();

    const symbol = document.getElementById('sellSymbol').value;
    const amount = parseFloat(document.getElementById('sellAmount').value);
    const price = parseFloat(document.getElementById('sellPrice').value);

    if (!symbol || !amount || !price) {
        UI.showToast('Tüm alanları doldurun', 'error');
        return;
    }

    const data = await API.post('/api/portfolio/sell', { symbol, amount, price });

    if (data.success) {
        UI.showToast('💰 Satış tamamlandı!');
        closeSellModal();
        loadPortfolio();

        // Clear form
        document.getElementById('sellAmount').value = '';
        document.getElementById('sellPrice').value = '';
    } else {
        UI.showToast(data.error || 'Hata oluştu', 'error');
    }
}

// Delete investment
async function deleteInvestment(symbol) {
    if (!confirm(`${symbol} silinsin mi? Bu işlem geri alınamaz.`)) return;

    const data = await API.delete(`/api/portfolio/delete/${symbol}`);

    if (data.success) {
        UI.showToast(`🗑️ ${symbol} silindi`);
        loadPortfolio();
    } else {
        UI.showToast(data.error || 'Hata oluştu', 'error');
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadPortfolio();

    // Add modal events
    document.getElementById('addInvestmentBtn')?.addEventListener('click', openAddModal);
    document.getElementById('closeModal')?.addEventListener('click', closeAddModal);
    document.getElementById('cancelModal')?.addEventListener('click', closeAddModal);
    document.getElementById('addForm')?.addEventListener('submit', addInvestment);

    // Sell modal events
    document.getElementById('closeSellModal')?.addEventListener('click', closeSellModal);
    document.getElementById('cancelSellModal')?.addEventListener('click', closeSellModal);
    document.getElementById('sellForm')?.addEventListener('submit', sellInvestment);

    // Backdrop clicks
    document.querySelectorAll('.modal-backdrop').forEach(el => {
        el.addEventListener('click', () => {
            closeAddModal();
            closeSellModal();
        });
    });
});

// Global functions for inline handlers
window.openSellModal = openSellModal;
window.deleteInvestment = deleteInvestment;
