app.views['memoria'] = {
    files: [],
    searchResults: [],
    loading: false,
    activeTab: 'docs', // 'docs' o 'notes'

    async render(container) {
        this.container = container;
        this.renderLayout();
        await this.loadData();
    },

    async loadData() {
        if (this.activeTab === 'docs') {
            await this.loadFiles();
        }
    },

    async loadFiles() {
        this.loading = true;
        this.updateContent();
        try {
            const response = await API.get('/files/');
            this.files = response;
        } catch (error) {
            console.error('Error cargando archivos:', error);
            app.utils.showToast('Error cargando archivos', 'error');
        } finally {
            this.loading = false;
            this.updateContent();
        }
    },

    setTab(tab) {
        this.activeTab = tab;
        this.renderLayout();
        this.loadData();
    },

    // --- Lógica de Documentos ---
    async uploadFile(event) {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        const progContainer = document.getElementById('uploadProgress');
        const progBar = document.getElementById('uploadProgressBar');
        
        if (progContainer) progContainer.style.display = 'block';

        try {
            app.utils.showToast(`Subiendo ${file.name}...`, 'info');
            await API.request('/files/upload', { 
                method: 'POST', 
                body: formData,
                onProgress: (percent) => {
                    if (progBar) progBar.style.width = `${percent}%`;
                }
            });
            app.utils.showToast('¡Documento indexado!', 'success');
            setTimeout(() => { if (progContainer) progContainer.style.display = 'none'; }, 1000);
            await this.loadFiles();
        } catch (error) {
            app.utils.showToast('Error al subir', 'error');
            if (progContainer) progContainer.style.display = 'none';
        }
    },

    async deleteFile(id) {
        if (!confirm('¿Seguro? Marco olvidará este documento.')) return;
        try {
            await API.delete(`/files/${id}`);
            app.utils.showToast('Archivo eliminado', 'success');
            await this.loadFiles();
        } catch (error) {
            app.utils.showToast('Error al eliminar', 'error');
        }
    },

    // --- Lógica de Notas (Cerebro) ---
    async saveNote() {
        const txt = document.getElementById('notaText').value;
        if (!txt) return;
        
        const btn = document.getElementById('btnGuardarNota');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<div class="spinner" style="width:16px;height:16px;border-width:2px;display:inline-block"></div> Guardando...';

        try {
            await API.post('/conocimiento/notas', { texto: txt, metadata: { source: 'web_ui' }});
            app.utils.showToast('Nota guardada en el cerebro', 'success');
            document.getElementById('notaText').value = '';
        } catch (error) {
            app.utils.showToast('Error al guardar nota', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    },

    async searchNote() {
        const q = document.getElementById('searchInput').value;
        if (!q) return;
        
        const resultsDiv = document.getElementById('searchResults');
        resultsDiv.innerHTML = '<div class="flex-center py-20"><div class="spinner"></div></div>';
        
        try {
            const res = await API.get(`/conocimiento/buscar?q=${encodeURIComponent(q)}`);
            this.renderSearchResults(res.results);
        } catch (error) {
            resultsDiv.innerHTML = `<p class="text-danger text-sm">Error en la búsqueda</p>`;
        }
    },

    // --- Renderizado ---
    renderLayout() {
        this.container.innerHTML = `
            <div class="animate-fade-in" style="padding: 20px;">
                <div class="header-section mb-24">
                    <h2 class="text-2xl font-bold text-white mb-4">Memoria Digital</h2>
                    <p class="text-muted text-sm">Gestión centralizada del conocimiento y archivos de Marco.</p>
                </div>

                <!-- Sistema de Pestañas -->
                <div class="tabs-container mb-24">
                    <button class="tab-btn ${this.activeTab === 'docs' ? 'active' : ''}" onclick="app.views.memoria.setTab('docs')">
                        <i class="ph ph-folders"></i> Documentos
                    </button>
                    <button class="tab-btn ${this.activeTab === 'notes' ? 'active' : ''}" onclick="app.views.memoria.setTab('notes')">
                        <i class="ph ph-brain"></i> Cerebro
                    </button>
                </div>

                <div id="memoriaContent">
                    <!-- Contenido dinámico -->
                </div>
            </div>

            <style>
                .tabs-container {
                    display: flex;
                    gap: 12px;
                    border-bottom: 1px solid rgba(255,255,255,0.05);
                    padding-bottom: 2px;
                }
                .tab-btn {
                    background: transparent;
                    border: none;
                    color: var(--text-muted);
                    padding: 10px 20px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-weight: 500;
                    border-bottom: 2px solid transparent;
                    transition: 0.2s;
                }
                .tab-btn:hover { color: white; }
                .tab-btn.active {
                    color: var(--accent);
                    border-bottom-color: var(--accent);
                    background: rgba(124, 58, 237, 0.05);
                }
                .notes-grid {
                    display: grid;
                    grid-template-columns: 1fr 1.5fr;
                    gap: 20px;
                }
                @media (max-width: 768px) {
                    .notes-grid { grid-template-columns: 1fr; }
                }
            </style>
        `;
        this.updateContent();
    },

    updateContent() {
        const content = document.getElementById('memoriaContent');
        if (!content) return;

        if (this.activeTab === 'docs') {
            this.renderDocs(content);
        } else {
            this.renderNotes(content);
        }
    },

    renderDocs(container) {
        container.innerHTML = `
            <div class="animate-fade-in">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 class="text-white text-lg font-semibold">Bóveda de Archivos</h3>
                    <label class="btn btn-accent" style="cursor: pointer; display: flex; align-items: center; gap: 8px;">
                        <i class="ph ph-upload-simple"></i>
                        <span>Subir</span>
                        <input type="file" class="hidden" onchange="app.views.memoria.uploadFile(event)">
                    </label>
                </div>

                <div id="uploadProgress" class="progress-container" style="margin-top:0; margin-bottom:20px;">
                    <div class="progress-bar" id="uploadProgressBar"></div>
                </div>

                <div id="docsList">
                    ${this.loading ? '<div class="flex-center py-20"><div class="spinner"></div></div>' : this.generateFilesHtml()}
                </div>
            </div>
        `;
    },

    renderNotes(container) {
        container.innerHTML = `
            <div class="animate-fade-in notes-grid">
                <div class="card glass-panel" style="padding: 20px;">
                    <h3 class="text-white text-md font-semibold mb-12"><i class="ph ph-note-pencil"></i> Nueva Nota</h3>
                    <textarea id="notaText" class="custom-input" rows="5" style="background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); color:white; width:100%; border-radius:8px; padding:12px; margin-bottom:12px;" placeholder="Escribe algo para que Marco lo aprenda..."></textarea>
                    <button id="btnGuardarNota" onclick="app.views.memoria.saveNote()" class="btn btn-accent" style="width:100%">Guardar nota</button>
                </div>

                <div class="card glass-panel" style="padding: 20px;">
                    <h3 class="text-white text-md font-semibold mb-12"><i class="ph ph-magnifying-glass"></i> Buscar en Cerebro</h3>
                    <div style="display:flex; gap:8px; margin-bottom:20px;">
                        <input type="text" id="searchInput" class="custom-input" style="flex:1; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); color:white; border-radius:8px; padding:8px 12px;" placeholder="¿Qué nombre tenía mi novia?">
                        <button onclick="app.views.memoria.searchNote()" class="btn btn-accent" style="padding:8px 15px;"><i class="ph ph-arrow-right"></i></button>
                    </div>
                    <div id="searchResults" class="item-list">
                        <p class="text-muted text-xs text-center py-10">Los resultados de búsqueda semántica aparecerán aquí.</p>
                    </div>
                </div>
            </div>
        `;
    },

    generateFilesHtml() {
        if (this.files.length === 0) {
            return `
                <div class="card" style="text-align: center; padding: 40px 20px; border: 2px dashed rgba(255,255,255,0.05); background: transparent;">
                    <i class="ph ph-files" style="font-size: 32px; color: rgba(255,255,255,0.1); margin-bottom: 10px; display: block;"></i>
                    <p class="text-muted text-sm">No hay documentos en la bóveda todavía.</p>
                </div>
            `;
        }

        return `
            <div class="grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px;">
                ${this.files.map(file => `
                    <div class="card hover-scale" style="padding: 12px; display: flex; flex-direction: column; gap: 10px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div style="width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.05);">
                                <i class="ph ${this.getFileIcon(file.filename)}" style="font-size: 18px; color: var(--accent);"></i>
                            </div>
                            <div style="flex: 1; min-width: 0;">
                                <h4 class="text-white text-xs font-semibold truncate" title="${file.filename}">${file.filename}</h4>
                                <p class="text-muted" style="font-size: 10px;">${app.utils.formatSize(file.file_size)}</p>
                            </div>
                        </div>
                        <div style="display: flex; gap: 6px;">
                            <button onclick="app.views.memoria.downloadFile(${file.id})" class="btn" style="flex: 1; padding: 4px; font-size: 11px; background: rgba(255,255,255,0.05);">
                                <i class="ph ph-download-simple"></i>
                            </button>
                            <button onclick="app.views.memoria.deleteFile(${file.id})" class="btn" style="padding: 4px; font-size: 11px; background: rgba(255,0,0,0.05); color: #ff6b6b; border:none;">
                                <i class="ph ph-trash"></i>
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    },

    renderSearchResults(results) {
        const div = document.getElementById('searchResults');
        if (!div) return;

        if (results.length === 0) {
            div.innerHTML = '<p class="text-muted text-sm text-center">No encontré nada parecido en la memoria.</p>';
            return;
        }

        div.innerHTML = results.map(r => `
            <div class="list-item" style="padding:12px; background: rgba(255,255,255,0.02); border-radius:8px; margin-bottom:8px; border-left: 3px solid var(--accent);">
                <div class="text-sm text-white">${r.content}</div>
                <div style="margin-top:8px; display:flex; gap:5px;">
                    <span class="tag" style="background: var(--accent-glow); color: var(--accent); font-size: 10px; padding: 2px 6px; border-radius:4px;">Similitud Alta</span>
                </div>
            </div>
        `).join('');
    },

    downloadFile(id) {
        window.open(`/api/files/download/${id}`, '_blank');
    },

    getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        if (ext === 'pdf') return 'ph-file-pdf';
        if (ext === 'txt') return 'ph-file-text';
        return 'ph-file';
    }
};
