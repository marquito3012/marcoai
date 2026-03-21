app.views['lifestyle'] = {
    async render(container) {
        container.innerHTML = `
            <div class="grid-2">
                <div class="card glass-panel">
                    <h3><i class="ph-fill ph-check-square text-gradient"></i> Hábitos (Hoy)</h3>
                    <div id="habitosList" class="item-list mt-16">
                        <div class="spinner"></div>
                    </div>
                </div>
                
                <div class="card glass-panel">
                    <h3><i class="ph-fill ph-cooking-pot text-gradient"></i> Dieta & Comidas</h3>
                    <div id="comidasInfo" class="mt-16">
                        <div class="spinner"></div>
                    </div>
                </div>
            </div>
            <style>
                .habito-check { cursor: pointer; display: flex; align-items: center; justify-content: space-between; }
                .habito-check i { font-size: 1.5rem; color: var(--text-muted); transition: 0.2s;}
                .habito-check.done i { color: var(--success); }
                .habito-check:hover i { transform: scale(1.1); }
            </style>
        `;

        try {
            const [habitos, comidas] = await Promise.all([
                API.get('/lifestyle/habitos'),
                API.get('/lifestyle/comidas')
            ]);
            
            const hl = document.getElementById('habitosList');
            hl.innerHTML = habitos.map(h => `
                <div class="list-item habito-check ${h.completado ? 'done' : ''}" onclick="this.classList.toggle('done')">
                    <strong>${h.nombre}</strong>
                    <i class="ph-fill ${h.completado ? 'ph-check-circle' : 'ph-circle'}"></i>
                </div>
            `).join('');
            
            const cl = document.getElementById('comidasInfo');
            cl.innerHTML = `
                <p><strong>Comida de Hoy:</strong> ${comidas.lunes}</p>
                <div class="mt-16">
                    <strong>Lista de Compra Generada:</strong>
                    <ul style="padding-left: 20px; color: var(--text-muted); margin-top: 8px;">
                        ${comidas.lista_compra.map(i => `<li>${i}</li>`).join('')}
                    </ul>
                </div>
            `;
        } catch (e) {
            container.innerHTML += `<p class="error-msg text-center mt-16">Error cargando Lifestyle: ${e.message}</p>`;
        }
    }
};
