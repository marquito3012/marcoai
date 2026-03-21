app.views['conocimiento'] = {
    async render(container) {
        container.innerHTML = `
            <div class="grid-2 mb-24">
                <div class="card glass-panel">
                    <h3><i class="ph-fill ph-brain text-gradient"></i> Capturar Nota RAG</h3>
                    <p class="text-sm text-muted mb-16">Escribe algo que quieras que recuerde a futuro.</p>
                    <textarea id="notaText" class="custom-input" rows="4" placeholder="Ej: La API de Groq es super rápida..."></textarea>
                    <button id="btnGuardarNota" class="btn-primary mt-16">Guardar en el Cerebro</button>
                    <p id="notaStatus" class="mt-8 text-sm" style="display:none;"></p>
                </div>
                
                <div class="card glass-panel">
                    <h3><i class="ph-fill ph-magnifying-glass text-gradient"></i> Buscar en Cerebro</h3>
                    <div class="search-bar mb-16">
                        <input type="text" id="searchInput" class="custom-input" placeholder="Pregunta algo guardado...">
                        <button id="btnBuscar" class="btn-icon"><i class="ph ph-arrow-right"></i></button>
                    </div>
                    <div id="searchResults" class="item-list mt-16">
                        <!-- Resultados -->
                    </div>
                </div>
            </div>
            <style>
                .mb-16 { margin-bottom: 16px; }
                .mt-8 { margin-top: 8px; }
                .text-sm { font-size: 0.85rem; }
                .custom-input {
                    background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border);
                    color: white; border-radius: 8px; padding: 12px; width: 100%;
                    font-family: inherit; resize: none;
                }
                .custom-input:focus { border-color: var(--accent-primary); outline:none; }
                .btn-primary {
                    background: var(--accent-primary); border: none; border-radius: 8px;
                    color: white; padding: 10px 16px; cursor: pointer; width: 100%; transition: 0.2s;
                    font-weight: 500;
                }
                .btn-primary:hover { background: #6d28d9; transform: translateY(-1px); }
                .search-bar { display: flex; gap: 8px; }
                .btn-icon { background: var(--glass-bg); border: 1px solid var(--glass-border); color: white; border-radius: 8px; width: 45px; cursor: pointer; }
                .btn-icon:hover { background: var(--accent-primary); }
                .tag { background: var(--accent-glow); color: #c4b5fd; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; margin-right: 4px;}
            </style>
        `;

        document.getElementById('btnGuardarNota').addEventListener('click', async () => {
            const txt = document.getElementById('notaText').value;
            if(!txt) return;
            const status = document.getElementById('notaStatus');
            status.style.display = 'block';
            status.textContent = 'Guardando e indexando vectores...';
            status.className = 'mt-8 text-sm text-accent';
            try {
                await API.post('/conocimiento/notas', { texto: txt, metadata: { source: 'web_ui' }});
                status.textContent = '¡Guardado correctamente!';
                status.className = 'mt-8 text-sm text-success';
                document.getElementById('notaText').value = '';
                setTimeout(() => status.style.display='none', 3000);
            } catch (error) {
                status.textContent = 'Error guardando nodo en RAG: ' + error.message;
                status.className = 'mt-8 text-sm text-danger';
            }
        });

        document.getElementById('btnBuscar').addEventListener('click', async () => {
            const q = document.getElementById('searchInput').value;
            if(!q) return;
            const resultsDiv = document.getElementById('searchResults');
            resultsDiv.innerHTML = '<div class="spinner" style="width:20px;height:20px;border-width:2px;margin: 0 auto;"></div>';
            try {
                const res = await API.get(`/conocimiento/buscar?q=${encodeURIComponent(q)}`);
                if(res.results.length === 0){
                    resultsDiv.innerHTML = '<p class="text-sm text-muted">No se encontró nada relacionado.</p>';
                    return;
                }
                resultsDiv.innerHTML = res.results.map(r => `
                    <div class="list-item">
                        <div class="text-sm">${r.content}</div>
                        <div class="mt-8"><span class="tag">Similitud Alta</span></div>
                    </div>
                `).join('');
            } catch (error) {
                resultsDiv.innerHTML = `<p class="text-sm text-danger">Error: ${error.message}</p>`;
            }
        });
    }
};
