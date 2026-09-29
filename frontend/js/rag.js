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
                docsTableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; color: var(--text-muted);">No educational documents found on server.</td></tr>`;
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
                    <td>
                        <button class="btn btn-sm btn-primary generate-quiz-btn" data-id="${d.id}" title="Generate Quiz">
                            <i class="fa-solid fa-wand-magic-sparkles"></i> Quiz
                        </button>
                    </td>
                </tr>
            `).join('');

            // Bind events for Quiz generation
            document.querySelectorAll('.generate-quiz-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const docId = e.currentTarget.getAttribute('data-id');
                    openQuizModal(docId);
                });
            });
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

let currentQuizData = null;

async function openQuizModal(docId) {
    const modal = document.getElementById('quiz-modal');
    const contentArea = document.getElementById('quiz-content');
    const evaluationArea = document.getElementById('quiz-evaluation');
    const submitBtn = document.getElementById('submit-quiz-btn');
    
    modal.classList.remove('hidden');
    contentArea.innerHTML = '<p><i class="fa-solid fa-spinner fa-spin"></i> Generating quiz using AI... This may take a minute.</p>';
    evaluationArea.classList.add('hidden');
    submitBtn.style.display = 'none';
    currentQuizData = null;

    try {
        const res = await ApiClient.generateQuiz(docId);
        if (!res.quiz || res.quiz.length === 0) {
            contentArea.innerHTML = '<p style="color: var(--accent-pink);">Failed to generate quiz from this document.</p>';
            return;
        }

        currentQuizData = res.quiz;
        renderQuiz(res.quiz);
        submitBtn.style.display = 'block';
    } catch (err) {
        contentArea.innerHTML = `<p style="color: var(--accent-pink);">Error: ${escapeHtml(err.message)}</p>`;
    }
}

function renderQuiz(quizArray) {
    const contentArea = document.getElementById('quiz-content');
    let html = '';
    quizArray.forEach((q, qIndex) => {
        html += `
            <div class="quiz-question" style="margin-bottom: 1.5rem; background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px;">
                <h4 style="margin-bottom: 0.8rem; color: var(--text-primary);">${qIndex + 1}. ${escapeHtml(q.question)}</h4>
                <div class="quiz-options" style="display: flex; flex-direction: column; gap: 0.5rem;">
        `;
        q.options.forEach((opt, optIndex) => {
            html += `
                <label style="display: flex; align-items: center; cursor: pointer;">
                    <input type="radio" name="q${qIndex}" value="${optIndex}" style="margin-right: 0.5rem;">
                    <span>${escapeHtml(opt)}</span>
                </label>
            `;
        });
        html += `</div>
            <div id="q-eval-${qIndex}" class="hidden" style="margin-top: 0.8rem; font-size: 0.9rem;"></div>
        </div>`;
    });
    contentArea.innerHTML = html;
}

document.getElementById('submit-quiz-btn')?.addEventListener('click', () => {
    if (!currentQuizData) return;
    
    let score = 0;
    currentQuizData.forEach((q, qIndex) => {
        const selected = document.querySelector(`input[name="q${qIndex}"]:checked`);
        const evalBox = document.getElementById(`q-eval-${qIndex}`);
        evalBox.classList.remove('hidden');
        
        if (!selected) {
            evalBox.innerHTML = `<span style="color: #ef4444;">❌ Not answered. Correct: ${escapeHtml(q.options[q.correct_answer_index])}</span><br><small style="color: var(--text-muted);">${escapeHtml(q.explanation)}</small>`;
            return;
        }
        
        const selectedVal = parseInt(selected.value);
        if (selectedVal === q.correct_answer_index) {
            score++;
            evalBox.innerHTML = `<span style="color: #10b981;">✅ Correct!</span><br><small style="color: var(--text-muted);">${escapeHtml(q.explanation)}</small>`;
        } else {
            evalBox.innerHTML = `<span style="color: #ef4444;">❌ Incorrect. Correct answer: ${escapeHtml(q.options[q.correct_answer_index])}</span><br><small style="color: var(--text-muted);">${escapeHtml(q.explanation)}</small>`;
        }
    });

    const evaluationArea = document.getElementById('quiz-evaluation');
    evaluationArea.classList.remove('hidden');
    evaluationArea.innerHTML = `<h4 style="color: var(--text-primary);">Your Score: ${score} / ${currentQuizData.length}</h4>`;
    document.getElementById('submit-quiz-btn').style.display = 'none';
});

document.getElementById('close-quiz-modal')?.addEventListener('click', () => {
    document.getElementById('quiz-modal').classList.add('hidden');
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
