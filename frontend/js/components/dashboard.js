app.views['dashboard'] = {
    async render(container) {
        container.innerHTML = `
            <div class="flex-center mt-24" style="display: flex; align-items: center; padding: 20px;">
                <div class="spinner"></div>
                <p class="text-muted ml-8">Sincronizando con tu Cerebro...</p>
            </div>
        `;
        
        let summary;
        try {
            summary = await API.get('/dashboard/summary');
        } catch (e) {
            console.error("Error cargando dashboard:", e);
            container.innerHTML = `<p class="text-error mb-24" style="padding: 20px;">Error cargando tus datos. Verifica tu conexión o asegúrate de que el backend ha sido reiniciado.</p>`;
            return;
        }

        // Formatear evento
        let eventoHTML = '';
        if (summary.evento) {
            const iso = summary.evento.hora;
            const dateObj = new Date(iso);
            const isAllDay = !iso.includes('T') && !iso.includes(':');
            
            // Formatear día (ej: "Lun 24 Mar" o "lunes, 24 de marzo" según locale)
            const dayStr = dateObj.toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short' });
            
            if (isAllDay) {
                eventoHTML = `
                    <div class="stat-value text-accent" style="font-size: 1.2rem; margin-top: 8px;">${dayStr}</div>
                    <p class="text-muted mt-8">${summary.evento.titulo} (Todo el día)</p>
                `;
            } else {
                const timeStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                eventoHTML = `
                    <div class="stat-value text-accent" style="font-size: 1.2rem; margin-top: 8px;">${timeStr}</div>
                    <p class="text-muted mt-8">📅 ${dayStr} • ${summary.evento.titulo}</p>
                `;
            }
        } else {
            eventoHTML = `
                <div class="stat-value text-muted" style="font-size: 1.2rem; margin-top: 8px;">--</div>
                <p class="text-muted mt-8">Sin eventos próximos</p>
            `;
        }

        // Formatear correos
        const correosHTML = `
            <div class="stat-value text-accent">${summary.correos.total}</div>
            <p class="text-muted">${summary.correos.alta_prioridad} de prioridad alta</p>
        `;

        // Formatear Hábitos
        const habitosCompletados = summary.habitos.filter(h => h.completado).length;
        const totalHabitos = summary.habitos.length;
        
        let habitosHTML = '';
        if (totalHabitos === 0) {
            habitosHTML = `<p class="text-muted mt-16" style="font-size: 0.9rem;">Todavía no se ha establecido ningún hábito</p>`;
        } else {
            habitosHTML = `
                <div class="stat-value text-success">${habitosCompletados}/${totalHabitos}</div>
                <p class="text-muted">Desempeño actual</p>
            `;
        }

        // Formatear Radar
        let radarHTML = '';
        if (summary.radar.length === 0) {
            radarHTML = `<p class="text-muted mt-16" style="font-size: 0.9rem;">Todavía no se ha establecido ningún elemento en el radar</p>`;
        } else {
            radarHTML = `<div class="item-list mt-16">`;
            summary.radar.forEach(r => {
                 radarHTML += `<div class="list-item">👉 ${r.titulo || r.nombre || "Elemento nuevo"}</div>`;
            });
            radarHTML += `</div>`;
        }

        container.innerHTML = `
            <div class="grid-3 mb-24">
                <div class="card glass-panel fade-in" style="animation-delay: 0.1s">
                    <h3><i class="ph-fill ph-calendar-check text-gradient"></i> Próximo Evento</h3>
                    ${eventoHTML}
                </div>
                
                <div class="card glass-panel fade-in" style="animation-delay: 0.2s">
                    <h3><i class="ph-fill ph-envelope-simple text-gradient"></i> Correos sin leer</h3>
                    ${correosHTML}
                </div>
                
                <div class="card glass-panel fade-in" style="animation-delay: 0.3s">
                    <h3><i class="ph-fill ph-lightning text-gradient"></i> Hábitos Hoy</h3>
                    ${habitosHTML}
                </div>
            </div>
            
            <div class="grid-2 mb-24">
                <div class="card glass-panel fade-in" style="animation-delay: 0.4s">
                    <h3><i class="ph-fill ph-sparkle text-gradient"></i> Resumen del Agente</h3>
                    <p class="mt-16" style="line-height: 1.6;">${summary.mensaje_agente}</p>
                    <button class="btn-outline mt-16" onclick="app.chat.toggle()">Hablar detalladamente</button>
                </div>
                
                <div class="card glass-panel fade-in" style="animation-delay: 0.5s">
                    <h3><i class="ph-fill ph-game-controller text-gradient"></i> Radar</h3>
                    ${radarHTML}
                </div>
            </div>
        `;
        
        // Some simple CSS inline for specific dashboard items
        const style = document.createElement('style');
        style.innerHTML = `
            .mb-24 { margin-bottom: 24px; }
            .mt-24 { margin-top: 24px; }
            .mt-16 { margin-top: 16px; }
            .mt-8 { margin-top: 8px; }
            .ml-8 { margin-left: 8px; }
            .text-gradient { background: var(--gradient-primary); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .text-accent { color: var(--accent-primary); }
            .text-success { color: var(--success); }
            .text-error { color: #f87171; }
            .btn-outline { 
                background: transparent; border: 1px solid var(--accent-primary);
                color: var(--accent-primary); padding: 8px 16px; border-radius: 8px;
                cursor: pointer; transition: 0.2s; font-weight: 500;
            }
            .btn-outline:hover { background: var(--accent-glow); color: white; box-shadow: 0 0 15px var(--accent-glow); }
            .fade-in { animation: fadeIn 0.5s ease backwards; }
            .spinner { width: 24px; height: 24px; border: 3px solid rgba(255,255,255,0.1); border-top-color: var(--accent-primary); border-radius: 50%; animation: spin 1s linear infinite; }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
            @keyframes spin { to { transform: rotate(360deg); } }
        `;
        container.appendChild(style);
    }
};
