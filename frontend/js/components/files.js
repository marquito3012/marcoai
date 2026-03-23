app.views['files'] = {
    files: [],
    loading: false,

    async render(container) {
        this.container = container;
        this.renderLayout();
        await this.loadFiles();
    },

    async loadFiles() {
        this.loading = true;
        this.updateContent();
        try {
            const response = await api.get('/files');
            this.files = response;
        } catch (error) {
            console.error('Error cargando archivos:', error);
        } finally {
            this.loading = false;
            this.updateContent();
        }
    },

    async uploadFile(event) {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            utils.showToast('Subiendo e indexando...', 'info');
            await api.post('/files/upload', formData, true);
            utils.showToast('Archivo listo en la bóveda', 'success');
            await this.loadFiles();
        } catch (error) {
            console.error('Error subiendo archivo:', error);
            utils.showToast('Error al subir archivo', 'error');
        }
    },

    async deleteFile(id) {
        if (!confirm('¿Seguro que quieres eliminar este archivo? Se borrará de la memoria de Marco.')) return;
        try {
            await api.delete(`/files/${id}`);
            utils.showToast('Archivo eliminado', 'success');
            await this.loadFiles();
        } catch (error) {
            console.error('Error eliminando archivo:', error);
        }
    },

    downloadFile(id) {
        window.open(`${api.baseUrl}/files/download/${id}`, '_blank');
    },

    renderLayout() {
        this.container.innerHTML = `
            <div class="animate-fade-in" style="padding: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;">
                    <div>
                        <h2 class="text-xl font-bold text-white">Bóveda Personal</h2>
                        <p class="text-muted text-sm">Tus documentos indexados para el RAG.</p>
                    </div>
                    <label class="btn btn-accent" style="cursor: pointer; display: flex; align-items: center; gap: 8px;">
                        <i class="ph ph-upload-simple"></i>
                        <span>Subir</span>
                        <input type="file" class="hidden" onchange="app.views.files.uploadFile(event)">
                    </label>
                </div>

                <div id="vaultContent">
                    <div class="flex-center py-20">
                        <div class="spinner"></div>
                    </div>
                </div>
            </div>
        `;
    },

    updateContent() {
        const content = document.getElementById('vaultContent');
        if (!content) return;

        if (this.loading) {
            content.innerHTML = `<div class="flex-center py-20"><div class="spinner"></div></div>`;
            return;
        }

        if (this.files.length === 0) {
            content.innerHTML = `
                <div class="card" style="text-align: center; padding: 60px 20px; border: 2px dashed rgba(255,255,255,0.1); background: transparent;">
                    <i class="ph ph-files" style="font-size: 48px; color: rgba(255,255,255,0.2); margin-bottom: 15px; display: block;"></i>
                    <p class="text-muted">La bóveda está vacía.</p>
                    <p class="text-muted text-xs mt-2">Sube archivos PDF o TXT para que Marco aprenda de ellos.</p>
                </div>
            `;
            return;
        }

        content.innerHTML = `
            <div class="grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px;">
                ${this.files.map(file => `
                    <div class="card hover-scale" style="padding: 15px; display: flex; flex-direction: column; gap: 12px;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.05);">
                                <i class="ph ${this.getFileIcon(file.filename)}" style="font-size: 20px; color: var(--accent);"></i>
                            </div>
                            <div style="flex: 1; min-width: 0;">
                                <h4 class="text-white text-sm font-semibold truncate" title="${file.filename}">${file.filename}</h4>
                                <p class="text-muted text-xs">${utils.formatSize(file.file_size)}</p>
                            </div>
                        </div>
                        <div style="display: flex; gap: 8px; margin-top: 5px;">
                            <button onclick="app.views.files.downloadFile(${file.id})" class="btn" style="flex: 1; padding: 6px; font-size: 12px; background: rgba(255,255,255,0.05);">
                                <i class="ph ph-download-simple"></i> Descargar
                            </button>
                            <button onclick="app.views.files.deleteFile(${file.id})" class="btn" style="padding: 6px; font-size: 12px; background: rgba(255,0,0,0.1); color: #ff6b6b; border: none;">
                                <i class="ph ph-trash"></i>
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    },

    getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        if (ext === 'pdf') return 'ph-file-pdf';
        if (ext === 'txt') return 'ph-file-text';
        return 'ph-file';
    }
};
