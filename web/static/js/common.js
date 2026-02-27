/**
 * Common JavaScript - Tüm sayfalarda ortak fonksiyonlar
 */

// ============================================================
// API Client
// ============================================================

const API = {
    // URL'yi prefix (SCRIPT_ROOT) ile birleştirme
    prepareUrl(endpoint) {
        // Eğer endpoint başında / varsa ve SCRIPT_ROOT varsa birleştir
        const prefix = typeof SCRIPT_ROOT !== 'undefined' ? SCRIPT_ROOT : '';
        // Endpoint zaten tam yolsa dokunma, değilse başına prefix ekle
        if (endpoint.startsWith('http')) return endpoint;
        const cleanEndpoint = endpoint.startsWith('/') ? endpoint : '/' + endpoint;
        return prefix + cleanEndpoint;
    },

    async get(endpoint) {
        try {
            const url = this.prepareUrl(endpoint);
            const res = await fetch(url);
            return await res.json();
        } catch (error) {
            console.error('API Error:', error);
            return { success: false, error: error.message };
        }
    },

    async post(endpoint, data) {
        try {
            const url = this.prepareUrl(endpoint);
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            return await res.json();
        } catch (error) {
            console.error('API Error:', error);
            return { success: false, error: error.message };
        }
    },

    async delete(endpoint) {
        try {
            const url = this.prepareUrl(endpoint);
            const res = await fetch(url, { method: 'DELETE' });
            return await res.json();
        } catch (error) {
            console.error('API Error:', error);
            return { success: false, error: error.message };
        }
    }
};

// ============================================================
// UI Utilities
// ============================================================

const UI = {
    showToast(message, type = 'success') {
        const toast = document.getElementById('toast');
        const toastMessage = document.getElementById('toastMessage');
        const toastIcon = toast.querySelector('.toast-icon');

        toastMessage.textContent = message;
        toastIcon.textContent = type === 'success' ? '✅' : '❌';

        toast.classList.add('active');
        setTimeout(() => toast.classList.remove('active'), 3000);
    },

    formatNumber(num, decimals = 2) {
        if (num === undefined || num === null) return '-';
        return new Intl.NumberFormat('tr-TR', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        }).format(num);
    },

    formatCurrency(num) {
        return `${this.formatNumber(num)} ₺`;
    },

    updateTime() {
        const el = document.getElementById('currentTime');
        if (el) {
            const now = new Date();
            el.textContent = now.toLocaleTimeString('tr-TR', {
                hour: '2-digit', minute: '2-digit'
            });
        }
    }
};

// ============================================================
// Search Functionality
// ============================================================

async function searchSymbol() {
    const input = document.getElementById('searchInput');
    const resultDiv = document.getElementById('searchResult');
    if (!input || !resultDiv) return;

    const symbol = input.value.trim().toUpperCase();

    if (!symbol) {
        resultDiv.classList.remove('active');
        return;
    }

    resultDiv.innerHTML = '<p style="color: var(--color-text-muted);">🔍 Aranıyor...</p>';
    resultDiv.classList.add('active');

    const data = await API.get(`/api/price/${symbol}`);

    if (data.success) {
        resultDiv.innerHTML = `
            <div class="search-result-content">
                <div class="search-result-info">
                    <h4>${data.name || data.symbol}</h4>
                    <p>${data.source} • ${data.date || 'Anlık'}</p>
                </div>
                <div class="search-result-price">${UI.formatNumber(data.price, 4)} ₺</div>
            </div>
        `;
    } else {
        resultDiv.innerHTML = `<p style="color: var(--color-danger);">❌ ${data.error || 'Bulunamadı'}</p>`;
    }
}

// ============================================================
// Market Card Generator
// ============================================================

function createMarketCard(item) {
    return `
        <div class="market-card">
            <div class="market-card-header">
                <span class="market-symbol">${item.symbol}</span>
                <span class="market-name">${item.display_name || item.name || ''}</span>
            </div>
            <div class="market-price">${UI.formatNumber(item.price, 4)} ₺</div>
            <div class="market-source">${item.source}</div>
        </div>
    `;
}

// ============================================================
// Initialization
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    // Update time
    UI.updateTime();
    setInterval(() => UI.updateTime(), 1000);

    // Footer year
    const footerYear = document.getElementById('footerYear');
    if (footerYear) {
        footerYear.textContent = new Date().getFullYear();
    }

    // Search event listeners
    const searchBtn = document.getElementById('searchBtn');
    const searchInput = document.getElementById('searchInput');

    if (searchBtn) {
        searchBtn.addEventListener('click', searchSymbol);
    }

    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchSymbol();
        });
    }

    // Hamburger menu
    const hamburger = document.getElementById('hamburgerBtn');
    const nav = document.querySelector('.nav');
    const navOverlay = document.getElementById('navOverlay');

    function toggleMobileMenu() {
        hamburger.classList.toggle('active');
        nav.classList.toggle('active');
        navOverlay.classList.toggle('active');
        document.body.style.overflow = nav.classList.contains('active') ? 'hidden' : '';
    }

    if (hamburger) {
        hamburger.addEventListener('click', toggleMobileMenu);
    }

    if (navOverlay) {
        navOverlay.addEventListener('click', toggleMobileMenu);
    }

    // Close mobile menu on nav link click
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            if (nav && nav.classList.contains('active')) {
                toggleMobileMenu();
            }
        });
    });
});
