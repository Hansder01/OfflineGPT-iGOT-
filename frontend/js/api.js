/**
 * Offline GPT — REST API Client & Rate Limit Interceptor
 */

const API_BASE = '/api';

class ApiClient {
    static getToken() {
        return localStorage.getItem('offline_gpt_token');
    }

    static setToken(token) {
        if (token) {
            localStorage.setItem('offline_gpt_token', token);
        } else {
            localStorage.removeItem('offline_gpt_token');
        }
    }

    static getHeaders(isJson = true) {
        const headers = {};
        if (isJson) {
            headers['Content-Type'] = 'application/json';
        }
        const token = this.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    }

    static async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        options.headers = { ...this.getHeaders(options.isJson !== false), ...options.headers };
        
        try {
            const response = await fetch(url, options);
            const data = await response.json().catch(() => ({}));
            
            if (response.status === 429) {
                // Rate limit hit
                if (window.handleRateLimitExceeded) {
                    window.handleRateLimitExceeded(data.detail || data);
                }
                throw new Error(data.detail?.message || "Rate limit reached. Please wait for cooldown.");
            }

            if (!response.ok) {
                throw new Error(data.detail || `HTTP Error ${response.status}`);
            }

            // Update rate limit info if present in response
            if (data.rate_limit && window.updateRateLimitUI) {
                window.updateRateLimitUI(data.rate_limit);
            }

            return data;
        } catch (error) {
            console.error(`API Error on ${endpoint}:`, error);
            throw error;
        }
    }

    // Auth API
    static async register(username, email, password) {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('email', email);
        formData.append('password', password);
        return this.request('/auth/register', { method: 'POST', body: formData, isJson: false });
    }

    static async login(username, password) {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        return this.request('/auth/login', { method: 'POST', body: formData, isJson: false });
    }

    static async getProfile() {
        return this.request('/auth/me', { method: 'GET' });
    }

    static async logout() {
        return this.request('/auth/logout', { method: 'POST' });
    }

    // Chat & CLI API
    static async sendChat(prompt, mode = 'auto') {
        return this.request('/chat', {
            method: 'POST',
            body: JSON.stringify({ prompt, mode })
        });
    }

    static async executeCli(command) {
        return this.request('/cli/execute', {
            method: 'POST',
            body: JSON.stringify({ command })
        });
    }

    // RAG Document API
    static async uploadDocument(file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.request('/documents/upload', { method: 'POST', body: formData, isJson: false });
    }

    static async listDocuments() {
        return this.request('/documents', { method: 'GET' });
    }

    static async deleteDocument(docId) {
        return this.request(`/documents/${docId}`, { method: 'DELETE' });
    }

    static async searchDocuments(query) {
        return this.request('/documents/search', {
            method: 'POST',
            body: JSON.stringify({ query })
        });
    }

    // Rate Limit Status
    static async getRateLimitStatus() {
        return this.request('/ratelimit/status', { method: 'GET' });
    }

    // System Telemetry
    static async getSystemInfo() {
        return this.request('/system/info', { method: 'GET' });
    }
}
