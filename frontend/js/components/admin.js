app.views['admin'] = {
    async render(container) {
        container.innerHTML = `
            <div class="grid-2">
                <div class="card glass-panel fade-in" style="animation-delay: 0.1s">
                    <h3><i class="ph-fill ph-wallet text-gradient"></i> Presupuesto del Mes</h3>
                    <div id="presupuestoVal" class="stat-value text-accent mt-16"><div class="spinner"></div></div>
                    <p class="text-muted mt-8">Restante para gastar</p>
                </div>
                
                <div class="card glass-panel fade-in" style="animation-delay: 0.2s">
                    <h3><i class="ph-fill ph-credit-card text-gradient"></i> Suscripciones Activas</h3>
                    <div id="subList" class="item-list mt-16">
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
            const dash = await API.get('/admin/dashboard');
            
            const presUI = document.getElementById('presupuestoVal');
            if (dash.presupuesto_restante !== null && dash.presupuesto_restante !== undefined) {
                 presUI.innerHTML = `€${parseFloat(dash.presupuesto_restante).toFixed(2)}`;
            } else {
                 presUI.innerHTML = `<span style="font-size: 1rem; color: var(--text-muted);">Todavía no se ha establecido ningún presupuesto</span>`;
            }
            
            const subList = document.getElementById('subList');
            if (!dash.suscripciones || dash.suscripciones.length === 0) {
                 subList.innerHTML = `<p class="text-muted mt-16" style="font-size: 0.9rem;">Todavía no se ha establecido ninguna suscripción</p>`;
            } else {
                 subList.innerHTML = dash.suscripciones.map(s => `
                    <div class="list-item" style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <strong>${s.nombre}</strong><br>
                            <span class="text-sm text-muted">Renueva: ${s.renovacion}</span>
                        </div>
                        <strong>€${s.costo}</strong>
                    </div>
                 `).join('');
            }
            
        } catch (e) {
             container.innerHTML += `<p class="error-msg text-center mt-16">Error cargando Gestión de dinero: ${e.message}</p>`;
        }
    }
};
