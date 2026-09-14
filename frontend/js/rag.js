/**
 * Offline GPT — RAG Educational Knowledge Base & Search Manager
 */

document.addEventListener('DOMContentLoaded', () => {
    const docsTableBody = document.getElementById('docs-table-body');
    const refreshDocsBtn = document.getElementById('refresh-docs-btn');
    
    const ragSearchInput = document.getElementById('rag-search-input');
    const ragSearchBtn = document.getElementById('rag-search-btn');
    const ragSearchResultsArea = document.getElementById('rag-search-results-area');

    async function loadDocumentsList() {
        try {
            const docs = await ApiClient.listDocuments();
            if (!docs || docs.length === 0) {
                docsTableBody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-muted);">No educational documents found on server.</td></tr>`;
                return;
            }

            docsTableBody.innerHTML = docs.map(d => `
                <tr>
                    <td>#${d.id}</td>
                    <td><strong>${escapeHtml(d.filename)}</strong></td>
                    <td><span class="pill pill-success">${d.file_type.toUpperCase()}</span></td>
                    <td>${formatBytes(d.file_size)}</td>
                    <td>${d.chunk_count} chunks</td>
                    <td><span class="pill pill-success" style="background: rgba(168,85,247,0.2); color: var(--accent-pink);">Server Locked 🔒</span></td>
                </tr>
            `).join('');
        } catch (e) {
            console.error("Error loading docs list:", e);
        }
    }

    refreshDocsBtn.addEventListener('click', loadDocumentsList);

    // Vector Search Test Execution
    async function performRagSearch() {
        const q = ragSearchInput.value.trim();
        if (!q) return;

        try {
            const res = await ApiClient.searchDocuments(q);
            ragSearchResultsArea.classList.remove('hidden');
            
            if (!res.results || res.results.length === 0) {
                ragSearchResultsArea.innerHTML = `<p style="color: var(--accent-pink);">No educational RAG matches found for: "${escapeHtml(q)}"</p>`;
            } else {
                ragSearchResultsArea.innerHTML = `
                    <h4 style="color: var(--accent-purple); margin-bottom: 0.5rem;"><i class="fa-solid fa-magnifying-glass"></i> Educational Curriculum Matches for "${escapeHtml(q)}":</h4>
                    ${res.results.map((r, i) => `
                        <div style="background: rgba(168,85,247,0.06); padding: 0.6rem; margin-bottom: 0.4rem; border-radius: 6px; border: 1px solid var(--border-color); font-size: 0.825rem;">
                            <strong>[${i+1}] ${escapeHtml(r.filename)} (Relevance Score: ${r.score})</strong>
                            <p style="color: var(--text-primary); margin-top: 0.25rem;">"${escapeHtml(r.content)}..."</p>
                        </div>
                    `).join('')}
                `;
            }
        } catch (err) {
            showToast(`Search error: ${err.message}`, 'error');
        }
    }

    ragSearchBtn.addEventListener('click', performRagSearch);
    ragSearchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') performRagSearch();
    });

    loadDocumentsList();
});

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
