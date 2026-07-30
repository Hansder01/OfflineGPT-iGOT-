/**
 * Offline GPT — RAG Knowledge Base & Document Search Manager
 */

document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadProgressCard = document.getElementById('upload-progress-card');
    const uploadFilename = document.getElementById('upload-filename');
    const uploadPercent = document.getElementById('upload-percent');
    const uploadBarFill = document.getElementById('upload-bar-fill');
    
    const docsTableBody = document.getElementById('docs-table-body');
    const refreshDocsBtn = document.getElementById('refresh-docs-btn');
    
    const ragSearchInput = document.getElementById('rag-search-input');
    const ragSearchBtn = document.getElementById('rag-search-btn');
    const ragSearchResultsArea = document.getElementById('rag-search-results-area');

    async function loadDocumentsList() {
        try {
            const docs = await ApiClient.listDocuments();
            if (!docs || docs.length === 0) {
                docsTableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; color: var(--text-muted);">No documents uploaded yet. Drag & drop a file above!</td></tr>`;
                return;
            }

            docsTableBody.innerHTML = docs.map(d => `
                <tr>
                    <td>#${d.id}</td>
                    <td><strong>${escapeHtml(d.filename)}</strong></td>
                    <td><span class="pill pill-success">${d.file_type.toUpperCase()}</span></td>
                    <td>${formatBytes(d.file_size)}</td>
                    <td>${d.chunk_count} chunks</td>
                    <td>${new Date(d.upload_date).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-danger btn-sm delete-doc-btn" data-id="${d.id}" title="Delete Document">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');

            // Attach delete handlers
            document.querySelectorAll('.delete-doc-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const id = btn.getAttribute('data-id');
                    if (confirm(`Delete document #${id}?`)) {
                        try {
                            await ApiClient.deleteDocument(id);
                            showToast("Document deleted successfully.");
                            loadDocumentsList();
                        } catch (err) {
                            showToast(`Delete failed: ${err.message}`, 'error');
                        }
                    }
                });
            });
        } catch (e) {
            console.error("Error loading docs list:", e);
        }
    }

    async function handleFileUpload(file) {
        if (!file) return;

        uploadFilename.innerText = file.name;
        uploadPercent.innerText = "0%";
        uploadBarFill.style.width = "0%";
        uploadProgressCard.classList.remove('hidden');

        try {
            uploadPercent.innerText = "50%";
            uploadBarFill.style.width = "50%";

            const res = await ApiClient.uploadDocument(file);
            
            uploadPercent.innerText = "100%";
            uploadBarFill.style.width = "100%";
            showToast(`File '${file.name}' indexed into ${res.chunk_count} RAG chunks!`);
            
            setTimeout(() => {
                uploadProgressCard.classList.add('hidden');
            }, 1200);

            loadDocumentsList();
        } catch (err) {
            showToast(`Upload failed: ${err.message}`, 'error');
            uploadProgressCard.classList.add('hidden');
        }
    }

    // Dropzone event handlers
    dropZone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    refreshDocsBtn.addEventListener('click', loadDocumentsList);

    // Vector Search Test Execution
    async function performRagSearch() {
        const q = ragSearchInput.value.strip ? ragSearchInput.value.strip() : ragSearchInput.value.trim();
        if (!q) return;

        try {
            const res = await ApiClient.searchDocuments(q);
            ragSearchResultsArea.classList.remove('hidden');
            
            if (!res.results || res.results.length === 0) {
                ragSearchResultsArea.innerHTML = `<p style="color: var(--accent-rose);">No RAG matches found for query: "${escapeHtml(q)}"</p>`;
            } else {
                ragSearchResultsArea.innerHTML = `
                    <h4 style="color: var(--accent-cyan); margin-bottom: 0.5rem;"><i class="fa-solid fa-magnifying-glass"></i> Top RAG Matches for "${escapeHtml(q)}":</h4>
                    ${res.results.map((r, i) => `
                        <div style="background: rgba(255,255,255,0.03); padding: 0.5rem; margin-bottom: 0.4rem; border-radius: 4px; font-size: 0.8rem;">
                            <strong>[${i+1}] ${escapeHtml(r.filename)} (Similarity Score: ${r.score})</strong>
                            <p style="color: var(--text-secondary); margin-top: 0.2rem;">"${escapeHtml(r.content)}..."</p>
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
