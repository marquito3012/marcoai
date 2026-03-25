app.views['admin'] = {
    async render(container) {
        container.innerHTML = `
            <div class="finance-dashboard animate-fade-in" style="padding: 20px;">
                <!-- Card Principal: Presupuesto Balanceado -->
                <div class="card glass-panel mb-24 text-center" style="max-width: 400px; margin-left: auto; margin-right: auto; padding: 30px;">
                    <h3 class="text-muted text-sm font-medium mb-8"><i class="ph-fill ph-wallet"></i> Presupuesto del Mes</h3>
                    <div id="presupuestoVal" class="stat-value text-accent" style="font-size: 2.5rem; font-weight: 700;">€0.00</div>
                    <p class="text-xs text-muted mt-8">Balance real (Ingresos - Gastos)</p>
                </div>

                <!-- Rejilla de Secciones Detalladas -->
                <div class="grid-3 finance-sections">
                    <div class="card glass-panel">
                        <h4 class="text-success flex-center-start gap-8 mb-16"><i class="ph-fill ph-trend-up"></i> Ingresos</h4>
                        <div id="ingresosList" class="item-list custom-scrollbar"></div>
                        <div class="section-footer mt-16 pt-12">
                            <div class="flex-between">
                                <span class="text-muted text-sm">Total:</span> 
                                <strong id="totalIngresos" class="text-success">€0.00</strong>
                            </div>
                        </div>
                    </div>

                    <div class="card glass-panel">
                        <h4 class="text-warning flex-center-start gap-8 mb-16"><i class="ph-fill ph-calendar-check"></i> Gastos Mensuales</h4>
                        <div id="gastosMensualesList" class="item-list custom-scrollbar"></div>
                        <div class="section-footer mt-16 pt-12">
                            <div class="flex-between">
                                <span class="text-muted text-sm">Total:</span> 
                                <strong id="totalGastosMensuales" class="text-warning">€0.00</strong>
                            </div>
                        </div>
                    </div>

                    <div class="card glass-panel">
                        <h4 class="text-danger flex-center-start gap-8 mb-16"><i class="ph-fill ph-shopping-cart-simple"></i> Gastos Puntuales</h4>
                        <div id="gastosPuntualesList" class="item-list custom-scrollbar"></div>
                        <div class="section-footer mt-16 pt-12">
                            <div class="flex-between">
                                <span class="text-muted text-sm">Total:</span> 
                                <strong id="totalGastosPuntuales" class="text-danger">€0.00</strong>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <style>
                .finance-dashboard .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
                .item-list { min-height: 120px; max-height: 320px; overflow-y: auto; padding-right: 5px; }
                .list-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
                .list-item:last-child { border-bottom: none; }
                .section-footer { border-top: 1px solid rgba(255,255,255,0.1); }
                .text-success { color: #10b981 !important; }
                .text-warning { color: #f59e0b !important; }
                .text-danger { color: #ef4444 !important; }
                .flex-between { display: flex; justify-content: space-between; align-items: center; }
                .flex-center-start { display: flex; align-items: center; justify-content: flex-start; }
            </style>
        `;

        try {
            const data = await API.get('/admin/dashboard');
            
            // Render Presupuesto
            const presVal = document.getElementById('presupuestoVal');
            const pres = data.presupuesto_restante || 0;
            presVal.textContent = `€${parseFloat(pres).toFixed(2)}`;
            if (pres < 0) presVal.style.color = '#ef4444';

            // Llenar Secciones
            this.renderSection('ingresosList', 'totalIngresos', data.detalles.ingresos);
            this.renderSection('gastosMensualesList', 'totalGastosMensuales', data.detalles.gastos_mensuales);
            this.renderSection('gastosPuntualesList', 'totalGastosPuntuales', data.detalles.gastos_puntuales);

        } catch (e) {
            app.utils.showToast('Error cargando balance: ' + e.message, 'error');
        }
    },

    renderSection(listId, totalId, data) {
        const list = document.getElementById(listId);
        const total = document.getElementById(totalId);
        
        total.textContent = `€${parseFloat(data.total).toFixed(2)}`;
        
        if (!data.items || data.items.length === 0) {
            list.innerHTML = `
                <div class="flex-center py-40" style="flex-direction: column; gap: 10px;">
                    <i class="ph ph-receipt" style="font-size: 24px; opacity: 0.1;"></i>
                    <p class="text-muted text-xs">Sin registros todavía</p>
                </div>
            `;
        } else {
            list.innerHTML = data.items.map(item => `
                <div class="list-item">
                    <span class="text-sm text-white truncate" style="max-width: 180px;" title="${item.content}">${item.content}</span>
                    <span class="text-sm font-semibold">€${parseFloat(item.amount).toFixed(2)}</span>
                </div>
            `).join('');
        }
    }
};
