/**
 * AI Chatbot Widget
 */

const Chatbot = {
    sessionId: 'session_' + Date.now(),
    isOpen: false,

    init() {
        const fab = document.getElementById('chatbotFab');
        const panel = document.getElementById('chatbotPanel');
        const closeBtn = document.getElementById('chatClose');
        const clearBtn = document.getElementById('chatClear');
        const sendBtn = document.getElementById('chatSend');
        const input = document.getElementById('chatInput');

        if (!fab || !panel) return;

        fab.addEventListener('click', () => this.toggle());
        closeBtn?.addEventListener('click', () => this.close());
        clearBtn?.addEventListener('click', () => this.clearChat());
        sendBtn?.addEventListener('click', () => this.sendMessage());

        input?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    },

    toggle() {
        this.isOpen = !this.isOpen;
        const panel = document.getElementById('chatbotPanel');
        const fab = document.getElementById('chatbotFab');

        if (this.isOpen) {
            panel.classList.add('active');
            fab.classList.add('hidden');
            document.getElementById('chatInput')?.focus();
        } else {
            this.close();
        }
    },

    close() {
        this.isOpen = false;
        document.getElementById('chatbotPanel')?.classList.remove('active');
        document.getElementById('chatbotFab')?.classList.remove('hidden');
    },

    async sendMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        if (!message) return;

        input.value = '';
        this.addMessage(message, 'user');
        this.showTyping();

        try {
            const response = await API.post('/api/chat', {
                message: message,
                session_id: this.sessionId
            });

            this.removeTyping();

            if (response.success) {
                this.addMessage(response.reply, 'bot');
            } else {
                this.addMessage('❌ ' + (response.error || 'Bir hata oluştu'), 'bot');
            }
        } catch (e) {
            this.removeTyping();
            this.addMessage('❌ Bağlantı hatası oluştu', 'bot');
        }
    },

    addMessage(text, sender) {
        const container = document.getElementById('chatMessages');
        const div = document.createElement('div');
        div.className = `chat-message ${sender}`;

        // Markdown-like formatting for bot messages
        let formattedText = text;
        if (sender === 'bot') {
            formattedText = this.formatMarkdown(text);
        }

        div.innerHTML = `<div class="chat-bubble">${formattedText}</div>`;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    },

    formatMarkdown(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    },

    showTyping() {
        const container = document.getElementById('chatMessages');
        const div = document.createElement('div');
        div.className = 'chat-message bot typing-indicator';
        div.innerHTML = `
            <div class="chat-bubble">
                <div class="typing-dots">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    },

    removeTyping() {
        const typing = document.querySelector('.typing-indicator');
        if (typing) typing.remove();
    },

    async clearChat() {
        const container = document.getElementById('chatMessages');
        container.innerHTML = `
            <div class="chat-message bot">
                <div class="chat-bubble">
                    Sohbet temizlendi! 🧹 Yeniden başlayalım. Nasıl yardımcı olabilirim?
                </div>
            </div>
        `;

        try {
            await API.post('/api/chat/clear', { session_id: this.sessionId });
        } catch (e) {
            console.error('Chat clear error:', e);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    Chatbot.init();
});
