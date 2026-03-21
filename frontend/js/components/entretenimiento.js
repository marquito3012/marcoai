app.views['entretenimiento'] = {
    async render(container) {
        container.innerHTML = `
            <div class="grid-2">
                <div class="card glass-panel">
                    <h3><i class="ph-fill ph-rocket-launch text-gradient"></i> Radar de Lanzamientos</h3>
                    <div id="radarList" class="item-list mt-16">
                        <div class="spinner"></div>
                    </div>
                </div>
                
                <div class="card glass-panel">
                    <h3><i class="ph-fill ph-tag text-gradient"></i> Ofertas Activas</h3>
                    <div id="ofertasList" class="item-list mt-16">
                        <div class="spinner"></div>
                    </div>
                </div>
            </div>
        `;

        try {
            const [radar, ofertas] = await Promise.all([
                API.get('/entretenimiento/radar'),
                API.get('/entretenimiento/ofertas')
            ]);
            
            document.getElementById('radarList').innerHTML = radar.map(r => `
                <div class="list-item">
                    <strong>${r.titulo}</strong> <span class="tag bg-accent">${r.tipo.toUpperCase()}</span><br>
                    <span class="text-sm text-muted">Sale el: ${r.fecha}</span>
                </div>
            `).join('');
            
            document.getElementById('ofertasList').innerHTML = ofertas.map(o => `
                <div class="list-item">
                    <strong>${o.juego}</strong> en ${o.tienda}<br>
                    <span class="text-success font-bold">${o.precio} (-${o.descuento})</span>
                </div>
            `).join('');
            
        } catch (e) {
             container.innerHTML += `<p class="error-msg text-center mt-16">Error cargando Entretenimiento: ${e.message}</p>`;
        }
    }
};
