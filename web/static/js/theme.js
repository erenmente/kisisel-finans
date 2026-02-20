/**
 * Theme Toggle - Light/Dark Mode
 */

const Theme = {
    init() {
        const saved = localStorage.getItem('finans-theme') || 'dark';
        this.apply(saved);

        const toggle = document.getElementById('themeToggle');
        if (toggle) {
            toggle.addEventListener('click', () => {
                const current = document.documentElement.getAttribute('data-theme');
                const next = current === 'dark' ? 'light' : 'dark';
                this.apply(next);
                localStorage.setItem('finans-theme', next);
            });
        }
    },

    apply(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        const icon = document.getElementById('themeIcon');
        if (icon) {
            icon.textContent = theme === 'dark' ? '☀️' : '🌙';
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    Theme.init();
});
