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
            } else if (target === 'profile-tab') {
                loadUserProfile();
            } else if (target === 'analytics-tab') {
                loadAnalytics();
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

    // Profile Logic
    const profileForm = document.getElementById('profile-form');
    if (profileForm) {
        profileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const profData = {
                designation: document.getElementById('prof-designation').value,
                department: document.getElementById('prof-department').value,
                work_experience_years: parseFloat(document.getElementById('prof-experience').value) || 0,
                educational_qualification: document.getElementById('prof-education').value,
                current_skills: document.getElementById('prof-skills').value.split(',').map(s => s.trim()).filter(s => s),
                completed_trainings: document.getElementById('prof-trainings').value.split(',').map(s => s.trim()).filter(s => s)
            };
            
            try {
                await ApiClient.updateProfileData(profData);
                showToast("Profile saved successfully!", "success");
            } catch (err) {
                showToast(`Failed to save profile: ${err.message}`, "error");
            }
        });
    }

    async function loadUserProfile() {
        try {
            const data = await ApiClient.getProfileData();
            if (data && Object.keys(data).length > 0) {
                document.getElementById('prof-designation').value = data.designation || '';
                document.getElementById('prof-department').value = data.department || '';
                document.getElementById('prof-experience').value = data.work_experience_years || '';
                document.getElementById('prof-education').value = data.educational_qualification || '';
                document.getElementById('prof-skills').value = (data.current_skills || []).join(', ');
                document.getElementById('prof-trainings').value = (data.completed_trainings || []).join(', ');
            }
        } catch (err) {
            console.error("Error loading profile data:", err);
        }
    }

    let radarChartInstance = null;
    let barChartInstance = null;

    async function loadAnalytics() {
        try {
            const res = await ApiClient.getAnalyticsDashboard();
            
            // Update Stat numbers
            document.getElementById('stat-skills').innerText = res.stats.skills || 0;
            document.getElementById('stat-trainings').innerText = res.stats.trainings || 0;
            document.getElementById('stat-docs').innerText = res.stats.documents || 0;

            // Render Radar Chart
            const skillsLabels = res.skills_data.length > 0 ? res.skills_data : ['No Skills Logged'];
            const skillsValues = res.skills_data.length > 0 ? res.skills_data.map(() => 100) : [0]; // default visual max
            
            const radarCtx = document.getElementById('skillsRadarChart').getContext('2d');
            if (radarChartInstance) radarChartInstance.destroy();
            radarChartInstance = new Chart(radarCtx, {
                type: 'radar',
                data: {
                    labels: skillsLabels,
                    datasets: [{
                        label: 'Competency Alignment (%)',
                        data: skillsValues,
                        backgroundColor: 'rgba(168, 85, 247, 0.2)',
                        borderColor: 'rgba(168, 85, 247, 1)',
                        pointBackgroundColor: 'rgba(168, 85, 247, 1)',
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: 'rgba(168, 85, 247, 1)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        r: {
                            angleLines: { color: 'rgba(255, 255, 255, 0.1)' },
                            grid: { color: 'rgba(255, 255, 255, 0.1)' },
                            pointLabels: { color: 'rgba(255, 255, 255, 0.7)', font: { size: 12 } },
                            ticks: { display: false }
                        }
                    },
                    plugins: { legend: { labels: { color: 'rgba(255, 255, 255, 0.8)' } } }
                }
            });

            // Render Bar Chart
            const barCtx = document.getElementById('engagementBarChart').getContext('2d');
            if (barChartInstance) barChartInstance.destroy();
            barChartInstance = new Chart(barCtx, {
                type: 'bar',
                data: {
                    labels: res.engagement_data.labels,
                    datasets: [{
                        label: 'Interactions',
                        data: res.engagement_data.data,
                        backgroundColor: ['rgba(56, 189, 248, 0.7)', 'rgba(16, 185, 129, 0.7)', 'rgba(244, 63, 94, 0.7)'],
                        borderColor: ['rgba(56, 189, 248, 1)', 'rgba(16, 185, 129, 1)', 'rgba(244, 63, 94, 1)'],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255, 255, 255, 0.1)' },
                            ticks: { color: 'rgba(255, 255, 255, 0.7)' }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: 'rgba(255, 255, 255, 0.7)' }
                        }
                    },
                    plugins: { legend: { display: false } }
                }
            });

            // Fetch iGOT Recommendations
            try {
                // Pick a skill gap to query (default to 'data' if none)
                const skillGapQuery = (res.skills_data.length > 0) ? res.skills_data[0] : "data";
                const igotRes = await ApiClient.getIgotRecommendations(skillGapQuery);
                const container = document.getElementById('igot-courses-container');
                container.innerHTML = '';
                
                if (igotRes.recommended_courses && igotRes.recommended_courses.length > 0) {
                    igotRes.recommended_courses.forEach(course => {
                        container.innerHTML += `
                            <div style="flex: 1; min-width: 250px; background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 8px; border-left: 4px solid var(--accent-emerald);">
                                <h5 style="color: var(--accent-cyan); font-size: 1.1rem; margin-bottom: 0.5rem;">${course.title}</h5>
                                <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 0.5rem;"><i class="fa-solid fa-building-columns"></i> ${course.provider}</p>
                                <p style="color: var(--text-muted); font-size: 0.9rem;"><i class="fa-regular fa-clock"></i> ${course.duration}</p>
                                <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem; flex-wrap: wrap;">
                                    ${course.tags.map(t => `<span style="background: rgba(168,85,247,0.2); padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; color: var(--accent-pink);">${t}</span>`).join('')}
                                </div>
                                <button class="btn btn-outline" style="margin-top: 1rem; width: 100%; border-color: var(--accent-emerald); color: var(--accent-emerald);" onclick="window.open('https://igot.karmayogi.gov.in', '_blank')">View on iGOT</button>
                            </div>
                        `;
                    });
                } else {
                    container.innerHTML = '<p style="color: var(--text-muted);">No recommendations at this time.</p>';
                }
            } catch (e) {
                console.error("iGOT Fetch Error:", e);
                document.getElementById('igot-courses-container').innerHTML = '<p style="color: var(--accent-pink);">Failed to connect to iGOT Karmayogi Mock API.</p>';
            }

        } catch (err) {
            console.error("Error loading analytics:", err);
            showToast("Failed to load Analytics dashboard", "error");
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
