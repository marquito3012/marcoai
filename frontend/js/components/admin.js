app.views['admin'] = {
    async render(container) {
        container.innerHTML = `
            <div class="admin-container animate-fade-in">
                <!-- Header / Budget Hero -->
                <div class="budget-hero glass-panel mb-24">
                    <div class="hero-content">
                        <div class="hero-label">
                            <i class="ph-fill ph-wallet"></i>
                            <span>Presupuesto del Mes</span>
                        </div>
                        <h2 id="presupuestoVal" class="hero-value"><div class="spinner-small"></div></h2>
                        <p class="hero-subtitle">Balance real: Ingresos - Gastos (Mensuales + Puntuales)</p>
                    </div>
                </div>

                <div class="finance-grid">
                    <!-- Sección 1: Ingresos -->
                    <div class="card glass-panel finance-card income-card">
                        <div class="card-header">
                            <i class="ph-fill ph-trend-up"></i>
                            <h3>Ingresos</h3>
                            <button class="icon-btn-small" onclick="app.views.admin.clearType('ingresos')" title="Borrar todo">
                                <i class="ph ph-trash"></i>
                            </button>
                            <span id="totalIngresos" class="badge">€0.00</span>
                        </div>
                        <div id="ingresosList" class="item-list scroll-shadow">
                            <div class="spinner-small"></div>
                        </div>
                    </div>

                    <!-- Sección 2: Gastos Mensuales -->
                    <div class="card glass-panel finance-card monthly-card">
                        <div class="card-header">
                            <i class="ph-fill ph-calendar-check"></i>
                            <h3>Gastos Mensuales</h3>
                            <button class="icon-btn-small" onclick="app.views.admin.clearType('gastos-mensuales')" title="Borrar todo">
                                <i class="ph ph-trash"></i>
                            </button>
                            <span id="totalMensuales" class="badge">€0.00</span>
                        </div>
                        <div id="mensualesList" class="item-list scroll-shadow">
                            <div class="spinner-small"></div>
                        </div>
                    </div>

                    <!-- Sección 3: Gastos Puntuales -->
                    <div class="card glass-panel finance-card punctual-card">
                        <div class="card-header">
                            <i class="ph-fill ph-receipt"></i>
                            <h3>Gastos Puntuales</h3>
                            <button class="icon-btn-small" onclick="app.views.admin.clearType('gastos-puntuales')" title="Borrar todo">
                                <i class="ph ph-trash"></i>
                            </button>
                            <span id="totalPuntuales" class="badge">€0.00</span>
                        </div>
                        <div id="puntualesList" class="item-list scroll-shadow">
                            <div class="spinner-small"></div>
                        </div>
                    </div>
                </div>
            </div>

            <style>
                .admin-container { padding: 20px; max-width: 1200px; margin: 0 auto; }
                .budget-hero {
                    background: linear-gradient(135deg, rgba(124, 58, 237, 0.2), rgba(139, 92, 246, 0.1));
                    border: 1px solid rgba(255,255,255,0.1);
                    padding: 40px;
                    text-align: center;
                    border-radius: 24px;
                }
                .hero-label { display: flex; align-items: center; justify-content: center; gap: 8px; color: var(--accent); font-weight: 600; text-transform: uppercase; letter-spacing: 1px; font-size: 0.8rem; margin-bottom: 12px; }
                .hero-value { font-size: 4rem; font-weight: 800; color: white; text-shadow: 0 4px 12px rgba(0,0,0,0.2); margin-bottom: 8px; }
                .hero-subtitle { color: var(--text-muted); font-size: 0.9rem; }

                .finance-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                    gap: 20px;
                }
                .finance-card { display: flex; flex-direction: column; height: 400px; border-radius: 20px; padding: 20px; }
                .card-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); }
                .card-header i { font-size: 24px; color: var(--accent); }
                .card-header h3 { flex: 1; font-size: 1.1rem; color: white; }
                .card-header .badge { background: rgba(255,255,255,0.05); color: white; padding: 4px 10px; border-radius: 8px; font-size: 0.85rem; font-weight: 600; }
                
                .icon-btn-small { background: transparent; border: none; color: var(--text-muted); cursor: pointer; padding: 5px; border-radius: 6px; transition: 0.2s; }
                .icon-btn-small:hover { color: #f43f5e; background: rgba(244, 63, 94, 0.1); }

                /* Variaciones de color */
                .income-card .card-header i { color: #10b981; }
                .monthly-card .card-header i { color: #3b82f6; }
                .punctual-card .card-header i { color: #f43f5e; }

                .item-list { flex: 1; overflow-y: auto; padding-right: 5px; }
                .list-item-finance { display: flex; justify-content: space-between; align-items: center; padding: 12px; border-radius: 12px; background: rgba(0,0,0,0.1); margin-bottom: 8px; transition: 0.2s; }
                .list-item-finance:hover { background: rgba(255,255,255,0.03); transform: translateX(2px); }
                .item-name { font-size: 0.9rem; color: #e2e8f0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px; }
                .item-val { font-weight: 600; font-size: 0.95rem; }
                
                .income-card .item-val { color: #34d399; }
                .monthly-card .item-val { color: #60a5fa; }
                .punctual-card .item-val { color: #fb7185; }

                .scroll-shadow { mask-image: linear-gradient(to bottom, black 90%, transparent 100%); }
                .spinner-small { width: 24px; height: 24px; border: 3px solid rgba(255,255,255,0.1); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; margin: 20px auto; }
                @keyframes spin { to { transform: rotate(360deg); } }
                
                @media (max-width: 768px) {
                    .hero-value { font-size: 2.5rem; }
                    .finance-grid { grid-template-columns: 1fr; }
                }
            </style>
        `;

        await this.loadData();
    },

    async loadData() {
        try {
            const data = await API.get('/admin/dashboard');
            
            // 1. Update Hero
            document.getElementById('presupuestoVal').textContent = `€${parseFloat(data.presupuesto_restante).toFixed(2)}`;
            
            // 2. Update Totals in Badges
            document.getElementById('totalIngresos').textContent = `€${data.detalles.ingresos.total.toFixed(2)}`;
            document.getElementById('totalMensuales').textContent = `€${data.detalles.gastos_mensuales.total.toFixed(2)}`;
            document.getElementById('totalPuntuales').textContent = `€${data.detalles.gastos_puntuales.total.toFixed(2)}`;

            // 3. Render Lists
            this.renderItemList('ingresosList', data.detalles.ingresos.items, 'monto');
            this.renderItemList('mensualesList', data.detalles.gastos_mensuales.items, 'costo');
            this.renderItemList('puntualesList', data.detalles.gastos_puntuales.items, 'costo');

        } catch (error) {
            console.error('Error dashboard:', error);
            app.utils.showToast('Error al cargar datos financieros', 'error');
        }
    },

    async clearType(tipo) {
        if (!confirm(`¿Estás seguro de que quieres borrar todos los registros de "${tipo.replace('-', ' ')}"?`)) return;
        
        try {
            await API.delete(`/admin/clear-type?tipo=${tipo}`);
            app.utils.showToast(`Registros de ${tipo} eliminados`, 'success');
            await this.loadData();
        } catch (error) {
            console.error('Error clearing:', error);
            app.utils.showToast('Error al eliminar registros', 'error');
        }
    },

    renderItemList(id, items, valKey) {
        const el = document.getElementById(id);
        if (!items || items.length === 0) {
            el.innerHTML = `<div class="flex-center py-20 opacity-40 text-sm">No hay registros</div>`;
            return;
        }
        el.innerHTML = items.map(item => `
            <div class="list-item-finance">
                <span class="item-name" title="${item.nombre}">${item.nombre}</span>
                <span class="item-val">€${parseFloat(item[valKey]).toFixed(2)}</span>
            </div>
        `).join('');
    }
};
