/**
 * Theme Toggle - Light/Dark Mode
 * Auto-detects system preference on first visit
 */

const Theme = {
    init() {
        // First check localStorage, then system preference
        let saved = localStorage.getItem('finans-theme');

        if (!saved) {
            // Auto-detect system preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            saved = prefersDark ? 'dark' : 'light';
        }

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

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('finans-theme')) {
                this.apply(e.matches ? 'dark' : 'light');
            }
        });
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
