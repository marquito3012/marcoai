app.views['entretenimiento'] = {
    async render(container) {
        container.innerHTML = `
            <div class="grid-2">
                <div class="card glass-panel fade-in" style="animation-delay: 0.1s">
                    <h3><i class="ph-fill ph-rocket-launch text-gradient"></i> Radar de Lanzamientos</h3>
                    <div id="radarList" class="item-list mt-16">
                        <div class="spinner"></div>
                    </div>
                </div>
                
                <div class="card glass-panel fade-in" style="animation-delay: 0.2s">
                    <h3><i class="ph-fill ph-tag text-gradient"></i> Ofertas Guardadas</h3>
                    <div id="ofertasList" class="item-list mt-16">
                        <div class="spinner"></div>
                    </div>
                </div>
            </div>
            <style>
                .fade-in { animation: fadeIn 0.5s ease backwards; }
                .spinner { width: 24px; height: 24px; border: 3px solid rgba(255,255,255,0.1); border-top-color: var(--accent-primary); border-radius: 50%; animation: spin 1s linear infinite; }
                @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
                @keyframes spin { to { transform: rotate(360deg); } }
            </style>
        `;

        try {
            const [radar, ofertas] = await Promise.all([
                API.get('/entretenimiento/radar'),
                API.get('/entretenimiento/ofertas')
            ]);
            
            const rList = document.getElementById('radarList');
            if (radar.length === 0) {
                 rList.innerHTML = `<p class="text-muted mt-16" style="font-size: 0.9rem;">Todavía no se ha establecido ningún elemento en el radar</p>`;
            } else {
                 rList.innerHTML = radar.map(r => `
                    <div class="list-item">
                        <strong>${r.titulo}</strong> <span class="tag bg-accent">${r.tipo.toUpperCase()}</span><br>
                        <span class="text-sm text-muted">Aviso: ${r.fecha}</span>
                    </div>
                 `).join('');
            }
            
            const oList = document.getElementById('ofertasList');
            if (ofertas.length === 0) {
                 oList.innerHTML = `<p class="text-muted mt-16" style="font-size: 0.9rem;">No hay ninguna oferta guardada en tu radar</p>`;
            } else {
                 oList.innerHTML = ofertas.map(o => `
                    <div class="list-item">
                        <strong>${o.juego}</strong> en ${o.tienda}<br>
                        <span class="text-success font-bold">${o.precio} ${o.descuento ? `(-${o.descuento})` : ''}</span>
                    </div>
                 `).join('');
            }
            
        } catch (e) {
             container.innerHTML += `<p class="text-error text-center mt-16">Error cargando Ocio: ${e.message}. Verifica que el backend esté ejecutándose.</p>`;
        }
    }
};
