// Objeto global de la App
const app = {
    auth: Auth,
    views: {}, // Almacena las funciones render de cada componente
    currentRoute: null,
    sidebarOpen: false,
    
    // Elementos del DOM base
    elements: {
        loader: document.getElementById('initialLoader'),
        routerView: document.getElementById('router-view'),
        layoutTemplate: document.getElementById('app-layout-template'),
        loginTemplate: document.getElementById('login-template')
    },

    async init() {
        console.log('Iniciando Marco AI...');
        
        // Manejar errores de OAuth en URL
        const urlParams = new URLSearchParams(window.location.search);
        const error = urlParams.get('error');
        if (error === 'max_users_reached') {
            window.location.hash = '#login?error=max_users_reached';
        }

        // Setup routing
        window.addEventListener('hashchange', () => this.handleRoute());
        
        // Verificar sesión inicial (simulamos delay para mostrar loader guapo)
        await new Promise(r => setTimeout(r, 800)); 
        const isAuth = await this.auth.checkSession();
        
        // Esconder loader
        this.elements.loader.classList.add('hidden');
        this.elements.routerView.classList.remove('hidden');

        // Disparar routing inicial
        if (!window.location.hash) {
            window.location.hash = isAuth ? '#dashboard' : '#login';
        } else {
            this.handleRoute();
        }
    },

    async handleRoute() {
        let hash = window.location.hash.slice(1).split('?')[0]; // Ej: 'dashboard'
        if (hash === '') hash = 'dashboard';
        
        this.currentRoute = hash;

        // Login Page check
        if (hash === 'login') {
            this.renderLogin();
            return;
        }

        // Si no es login, verificar auth
        if (!this.auth.user && !(await this.auth.checkSession())) {
            window.location.hash = '#login';
            return;
        }

        // Asegurar que el Layout base (Sidebar + Topbar) está montado
        this.ensureLayout();
        
        // Limpiar contenido anterior
        const contentArea = document.getElementById('pageContent');
        contentArea.innerHTML = '<div class="initial-loader"><div class="spinner"></div></div>';

        // Ocultar Chat al cambiar vista por defecto
        if (this.chat && this.chat.isOpen) this.chat.close();
        
        // Actualizar UI del Navbar
        this.updateNav(hash);
        
        // Renderizar vista específica
        try {
            if (this.views[hash]) {
                await this.views[hash].render(contentArea);
            } else {
                // Vista por defecto (Dashboard)
                if(this.views['dashboard']) await this.views['dashboard'].render(contentArea);
            }
        } catch (e) {
            contentArea.innerHTML = `<div class="card"><p class="error-msg">Error cargando ${hash}: ${e.message}</p></div>`;
        }
    },

    ensureLayout() {
        // Verificar si la layout ya está inyectada
        if (!document.querySelector('.app-layout')) {
            const clone = this.elements.layoutTemplate.content.cloneNode(true);
            this.elements.routerView.innerHTML = '';
            this.elements.routerView.appendChild(clone);
            this.auth.updateProfileUI(); // Poner nombre y foto
            this.chat.init(); // Inicializar el panel de chat
        }
    },

    toggleSidebar() {
        this.sidebarOpen = !this.sidebarOpen;
        const sidebar = document.querySelector('.sidebar');
        const backdrop = document.querySelector('.sidebar-backdrop');
        if (sidebar) {
            if (this.sidebarOpen) {
                sidebar.classList.add('open');
                if (backdrop) backdrop.classList.add('show');
            } else {
                sidebar.classList.remove('open');
                if (backdrop) backdrop.classList.remove('show');
            }
        }
    },

    renderLogin() {
        this.elements.routerView.innerHTML = '';
        const clone = this.elements.loginTemplate.content.cloneNode(true);
        this.elements.routerView.appendChild(clone);
        
        // Mostrar mensaje de error si existe en Hash
        const queryError = window.location.hash.split('?error=')[1];
        if (queryError === 'max_users_reached') {
            document.getElementById('loginError').textContent = 'Límite de usuarios (20) alcanzado en esta beta.';
        }
    },

    updateNav(hash) {
        document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
        const activeItem = document.querySelector(`.nav-item[data-path="${hash}"]`);
        if (activeItem) {
            activeItem.classList.add('active');
            let title = document.getElementById('pageTitle');
            if(title) title.textContent = activeItem.querySelector('span').textContent;
            
            // Auto close sidebar on mobile after clicking a link
            if (window.innerWidth <= 768 && this.sidebarOpen) {
                this.toggleSidebar();
            }
        }
    },

    // --- Módulo Chat ---
    chat: {
        isOpen: false,
        element: null,
        messagesArea: null,
        input: null,
        
        init() {
            this.element = document.getElementById('chatPanel');
            this.messagesArea = document.getElementById('chatMessages');
            this.input = document.getElementById('chatInput');
        },

        toggle() {
            if (!this.element) return;
            this.isOpen = !this.isOpen;
            if (this.isOpen) {
                this.element.classList.remove('closed');
                this.input.focus();
            } else {
                this.element.classList.add('closed');
            }
        },

        close() {
            this.isOpen = false;
            if(this.element) this.element.classList.add('closed');
        },

        async send() {
            if(!this.input) return;
            const text = this.input.value.trim();
            if (!text) return;

            // Optimistic UI
            this.input.value = '';
            this.addMessage(text, 'user');
            
            // Loading indicator
            const loadId = this.addMessage('...', 'system', true);

            try {
                const response = await API.post('/agente/chat', { message: text });
                this.removeMessage(loadId);
                this.addMessage(response.reply, 'system');
            } catch (error) {
                this.removeMessage(loadId);
                this.addMessage(`Error de red: ${error.message}`, 'system');
            }
        },

        addMessage(text, role, isLoading = false) {
            const id = 'msg-' + Date.now();
            const div = document.createElement('div');
            div.id = id;
            div.className = `message ${role}`;
            if(isLoading) div.classList.add('skeleton-text');
            div.textContent = text;
            this.messagesArea.appendChild(div);
            this.messagesArea.scrollTop = this.messagesArea.scrollHeight;
            return id;
        },

        removeMessage(id) {
            const el = document.getElementById(id);
            if(el) el.remove();
        }
    }
};

// Arranque
document.addEventListener('DOMContentLoaded', () => app.init());
