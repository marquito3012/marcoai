app.views['lifestyle'] = {
    async render(container) {
        container.innerHTML = `
            <div class="grid-2">
                <div class="card glass-panel fade-in" style="animation-delay: 0.1s">
                    <h3><i class="ph-fill ph-check-square text-gradient"></i> Hábitos (Hoy)</h3>
                    <div id="habitosList" class="item-list mt-16">
                        <div class="spinner"></div>
                    </div>
                </div>
                
                <div class="card glass-panel fade-in" style="animation-delay: 0.2s">
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
                .fade-in { animation: fadeIn 0.5s ease backwards; }
                .spinner { width: 24px; height: 24px; border: 3px solid rgba(255,255,255,0.1); border-top-color: var(--accent-primary); border-radius: 50%; animation: spin 1s linear infinite; }
                @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
                @keyframes spin { to { transform: rotate(360deg); } }
            </style>
        `;

        try {
            const [habitos, dietaData] = await Promise.all([
                API.get('/lifestyle/habitos'),
                API.get('/lifestyle/comidas')
            ]);
            
            const hl = document.getElementById('habitosList');
            if (habitos.length === 0) {
                 hl.innerHTML = `<p class="text-muted mt-16" style="font-size: 0.9rem;">Todavía no se ha establecido ningún hábito</p>`;
            } else {
                 hl.innerHTML = habitos.map(h => `
                    <div class="list-item habito-check ${h.completado ? 'done' : ''}" 
                         data-nombre="${h.nombre}"
                         onclick="app.views.lifestyle.toggleHabito(this)">
                        <strong>${h.nombre}</strong>
                        <i class="ph-fill ${h.completado ? 'ph-check-circle' : 'ph-circle'}"></i>
                    </div>
                 `).join('');
            }
            
            const cl = document.getElementById('comidasInfo');
            let comidasHTML = '';
            if (dietaData.comidas && dietaData.comidas.length > 0) {
                 comidasHTML = `<p><strong>Comidas Planeadas:</strong> ${dietaData.comidas.join(', ')}</p>`;
            } else {
                 comidasHTML = `<p class="text-muted" style="font-size: 0.9rem;">Todavía no se ha planeado ninguna comida</p>`;
            }
            
            let listaCompraHTML = '';
            if (dietaData.lista_compra && dietaData.lista_compra.length > 0) {
                 listaCompraHTML = `
                    <div class="mt-16">
                        <strong>Lista de Compra Generada:</strong>
                        <ul style="padding-left: 20px; color: var(--text-muted); margin-top: 8px;">
                            ${dietaData.lista_compra.map(i => `<li>${i}</li>`).join('')}
                        </ul>
                    </div>
                 `;
            } else {
                 listaCompraHTML = `<p class="text-muted mt-16" style="font-size: 0.9rem;">No hay elementos en la lista de la compra</p>`;
            }
            
            cl.innerHTML = comidasHTML + listaCompraHTML;
            
        } catch (e) {
            container.innerHTML += `<p class="text-error text-center mt-16">Error cargando Lifestyle: ${e.message}. Verifica que el backend esté ejecutándose.</p>`;
        }
    },

    async toggleHabito(element) {
        try {
            const nombre = element.getAttribute('data-nombre');
            const res = await API.post('/lifestyle/habitos/toggle', { nombre });
            if (res.success) {
                element.classList.toggle('done', res.completado);
                const icon = element.querySelector('i');
                icon.className = `ph-fill ${res.completado ? 'ph-check-circle' : 'ph-circle'}`;
            }
        } catch (e) {
            console.error("Error toggling habit:", e);
        }
    }
};
