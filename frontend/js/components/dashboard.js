app.views['dashboard'] = {
    async render(container) {
        // Fetch resume data from different modules conceptually
        // For a true dashboard, we might have a specific /api/dashboard endpoint,
        // but here we'll mock a quick premium layout
        
        container.innerHTML = `
            <div class="grid-3 mb-24">
                <div class="card glass-panel fade-in" style="animation-delay: 0.1s">
                    <h3><i class="ph-fill ph-calendar-check text-gradient"></i> Próximo Evento</h3>
                    <div class="stat-value" id="dashEvent">--</div>
                    <p class="text-muted">Reunión de Equipo a las 15:00</p>
                </div>
                
                <div class="card glass-panel fade-in" style="animation-delay: 0.2s">
                    <h3><i class="ph-fill ph-envelope-simple text-gradient"></i> Correos sin leer</h3>
                    <div class="stat-value text-accent">3</div>
                    <p class="text-muted">2 de prioridad alta</p>
                </div>
                
                <div class="card glass-panel fade-in" style="animation-delay: 0.3s">
                    <h3><i class="ph-fill ph-lightning text-gradient"></i> Hábitos Hoy</h3>
                    <div class="stat-value text-success">2/4</div>
                    <p class="text-muted">Te falta beber agua</p>
                </div>
            </div>
            
            <div class="grid-2">
                <div class="card glass-panel fade-in" style="animation-delay: 0.4s">
                    <h3><i class="ph-fill ph-sparkle"></i> Resumen del Agente</h3>
                    <p>¡Buen día! Tienes la mañana libre para Deep Work. A la tarde tienes 1 reunión. He borrado 3 correos de spam por ti.</p>
                    <button class="btn-outline mt-16" onclick="app.chat.toggle()">Hablar detalladamente</button>
                </div>
                
                <div class="card glass-panel fade-in" style="animation-delay: 0.5s">
                    <h3><i class="ph-fill ph-game-controller"></i> Radar</h3>
                    <div class="item-list">
                        <div class="list-item">
                            👉 Oferta: Red Dead Redemption 2 (-60%)
                        </div>
                        <div class="list-item">
                            👉 Salida: Nueva temporada de The Bear (Mañana)
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Some simple CSS inline for specific dashboard items
        const style = document.createElement('style');
        style.innerHTML = `
            .mb-24 { margin-bottom: 24px; }
            .mt-16 { margin-top: 16px; }
            .text-accent { color: var(--accent-primary); }
            .text-success { color: var(--success); }
            .btn-outline { 
                background: transparent; border: 1px solid var(--accent-primary);
                color: var(--accent-primary); padding: 8px 16px; border-radius: 8px;
                cursor: pointer; transition: 0.2s; font-weight: 500;
            }
            .btn-outline:hover { background: var(--accent-glow); color: white; }
            .fade-in { animation: fadeIn 0.5s ease backwards; }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        `;
        container.appendChild(style);
    }
};
