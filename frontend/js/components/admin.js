app.views['admin'] = {
    async render(container) {
        container.innerHTML = `
            <div class="grid-2">
                <div class="card glass-panel">
                    <h3><i class="ph-fill ph-wallet text-gradient"></i> Presupuesto del Mes</h3>
                    <div id="presupuestoVal" class="stat-value text-accent mt-16"><div class="spinner"></div></div>
                    <p class="text-muted">Restante para gastar</p>
                </div>
                
                <div class="card glass-panel">
                    <h3><i class="ph-fill ph-credit-card text-gradient"></i> Suscripciones Activas</h3>
                    <div id="subList" class="item-list mt-16">
                        <div class="spinner"></div>
                    </div>
                </div>
            </div>
        `;

        try {
            const dash = await API.get('/admin/dashboard');
            document.getElementById('presupuestoVal').textContent = `€${dash.presupuesto_restante.toFixed(2)}`;
            
            document.getElementById('subList').innerHTML = dash.suscripciones.map(s => `
                <div class="list-item" style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong>${s.nombre}</strong><br>
                        <span class="text-sm text-muted">Renueva: ${s.renovacion}</span>
                    </div>
                    <strong>€${s.costo}</strong>
                </div>
            `).join('');
            
        } catch (e) {
             container.innerHTML += `<p class="error-msg text-center mt-16">Error cargando Admin: ${e.message}</p>`;
        }
    }
};
