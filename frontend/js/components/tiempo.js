app.views['tiempo'] = {
    async render(container) {
        container.innerHTML = `
            <div class="grid-2">
                <div class="card glass-panel">
                    <h3><i class="ph-fill ph-calendar text-gradient"></i> Próximos Eventos</h3>
                    <div id="calendarList" class="item-list">
                        <div class="skeleton-text">Cargando eventos...</div>
                        <div class="skeleton-text">Cargando eventos...</div>
                    </div>
                </div>
                
                <div class="card glass-panel">
                    <h3><i class="ph-fill ph-envelope text-gradient"></i> Bandeja de Entrada</h3>
                    <div id="emailList" class="item-list">
                        <div class="skeleton-text">Cargando correos...</div>
                        <div class="skeleton-text">Cargando correos...</div>
                    </div>
                </div>
            </div>
        `;

        try {
            // Cargar datos en paralelo
            const [agenda, correos] = await Promise.all([
                API.get('/tiempo/agenda'),
                API.get('/tiempo/correos')
            ]);
            
            const calEl = document.getElementById('calendarList');
            if (agenda.length === 0) {
                calEl.innerHTML = '<p class="text-muted">No hay eventos próximos.</p>';
            } else {
                calEl.innerHTML = agenda.map(e => `
                    <div class="list-item">
                        <strong>${e.summary}</strong><br>
                        <span class="text-muted text-sm">${new Date(e.start.dateTime || e.start.date).toLocaleString()}</span>
                    </div>
                `).join('');
            }
            
            const mailEl = document.getElementById('emailList');
            if (correos.length === 0) {
                mailEl.innerHTML = '<p class="text-muted">Sin correos nuevos.</p>';
            } else {
                mailEl.innerHTML = correos.map(m => `
                    <div class="list-item">
                        <strong>${m.subject}</strong><br>
                        <span class="text-muted text-sm">De: ${m.from.split('<')[0]}</span>
                    </div>
                `).join('');
            }
        } catch (error) {
            container.innerHTML += `<p class="error-msg text-center mt-16">Error cargando Time & Mail: ${error.message}</p>`;
        }
    }
};
