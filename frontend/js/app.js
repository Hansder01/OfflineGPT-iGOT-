/**
 * Offline GPT — Main Application UI Orchestrator
 */

document.addEventListener('DOMContentLoaded', () => {
    // Tab Navigation Switcher
    const navTabs = document.querySelectorAll('.nav-tab');
    const tabPanels = document.querySelectorAll('.tab-panel');

    navTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.getAttribute('data-tab');
            
            navTabs.forEach(t => t.classList.remove('active'));
            tabPanels.forEach(p => p.classList.remove('active'));

            tab.classList.add('active');
            const targetPanel = document.getElementById(target);
            if (targetPanel) targetPanel.classList.add('active');

            if (target === 'about-tab') {
                loadSystemTelemetry();
            }
        });
    });

    // Language Selector Event
    const langSelect = document.getElementById('language-select');
    langSelect.addEventListener('change', (e) => {
        setLanguage(e.target.value);
        showToast(`Language set to ${e.target.options[e.target.selectedIndex].text}`);
    });

    // Chat Interface Logic
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendChatBtn = document.getElementById('send-chat-btn');
    const chatModeSelect = document.getElementById('chat-mode-select');
    const activeProviderLabel = document.getElementById('active-provider-label');
    const clearChatBtn = document.getElementById('clear-chat-btn');

    function appendChatMessage(role, text, meta = {}) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role === 'user' ? 'user-msg' : 'bot-msg'}`;

        const iconClass = role === 'user' ? 'fa-user' : 'fa-robot';
        
        let metaHtml = '';
        if (meta.provider) {
            metaHtml += `<span><i class="fa-solid fa-microchip"></i> ${escapeHtml(meta.provider)}</span>`;
        }
        if (meta.tools && meta.tools.length > 0) {
            metaHtml += `<span><i class="fa-solid fa-wrench"></i> Tools: ${meta.tools.join(', ')}</span>`;
        }

        let ragSourceHtml = '';
        if (meta.rag_sources && meta.rag_sources.length > 0) {
            ragSourceHtml = `
                <div style="margin-top: 0.6rem; padding-top: 0.4rem; border-top: 1px solid var(--border-color); font-size: 0.78rem;">
                    <strong style="color: var(--accent-cyan);"><i class="fa-solid fa-book"></i> Referenced RAG Sources:</strong>
                    <ul style="margin-left: 1.2rem; margin-top: 0.2rem;">
                        ${meta.rag_sources.map(s => `<li><code>${escapeHtml(s.filename)}</code> (Chunk #${s.chunk_index}, Score: ${s.score})</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        msgDiv.innerHTML = `
            <div class="msg-avatar"><i class="fa-solid ${iconClass}"></i></div>
            <div class="msg-body">
                <div>${formatMarkdown(text)}</div>
                ${ragSourceHtml}
                ${metaHtml ? `<div class="msg-meta">${metaHtml}</div>` : ''}
            </div>
        `;

        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async function sendPrompt() {
        const prompt = chatInput.value.trim();
        if (!prompt) return;

        appendChatMessage('user', prompt);
        chatInput.value = '';
        chatInput.style.height = 'auto';

        const selectedMode = chatModeSelect.value;

        // Add loading bot message
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message bot-msg loading';
        loadingDiv.innerHTML = `
            <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="msg-body"><i class="fa-solid fa-circle-notch fa-spin"></i> Offline GPT is thinking...</div>
        `;
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const data = await ApiClient.sendChat(prompt, selectedMode);
            chatMessages.removeChild(loadingDiv);

            if (data.provider_used) {
                activeProviderLabel.innerText = `Engine: ${data.provider_used}`;
            }

            appendChatMessage('bot', data.response, {
                provider: data.provider_used,
                tools: data.tools_executed,
                rag_sources: data.rag_sources
            });
        } catch (err) {
            chatMessages.removeChild(loadingDiv);
            appendChatMessage('bot', `⚠️ Request failed: ${err.message}`);
        }
    }

    sendChatBtn.addEventListener('click', sendPrompt);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendPrompt();
        }
    });

    clearChatBtn.addEventListener('click', () => {
        chatMessages.innerHTML = `
            <div class="message system-msg">
                <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="msg-body">
                    <h3>History Cleared</h3>
                    <p>Start a new conversation or query your documents.</p>
                </div>
            </div>
        `;
    });

    // Quick chip buttons listener
    document.querySelectorAll('.chip-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const prompt = btn.getAttribute('data-prompt');
            chatInput.value = prompt;
            sendPrompt();
        });
    });

    // Telemetry Loader
    async function loadSystemTelemetry() {
        try {
            const tele = await ApiClient.getSystemInfo();
            document.getElementById('tele-os').innerText = tele.os || 'N/A';
            document.getElementById('tele-py').innerText = tele.python_version || 'N/A';
            document.getElementById('tele-cpu').innerText = `${tele.cpu_usage_percent || 0}%`;
            document.getElementById('tele-ram').innerText = `${tele.memory_used_gb || 0} GB / ${tele.memory_total_gb || 0} GB (${tele.memory_percent || 0}%)`;
        } catch (e) {
            console.error("Error loading telemetry:", e);
        }
    }

    loadSystemTelemetry();
});

// Toast notification helper
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type === 'error' ? 'toast-error' : ''}`;
    toast.innerHTML = `<i class="fa-solid ${type === 'error' ? 'fa-triangle-exclamation' : 'fa-circle-check'}"></i> ${escapeHtml(message)}`;
    
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Lightweight Markdown Formatter
function formatMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);
    
    // Bold **text**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic *text*
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Code `code`
    html = html.replace(/`(.*?)`/g, '<code style="background: rgba(0,0,0,0.4); padding: 0.15rem 0.4rem; border-radius: 4px; font-family: var(--font-code); color: #38bdf8;">$1</code>');
    // Line breaks
    html = html.replace(/\n/g, '<br>');
    return html;
}
