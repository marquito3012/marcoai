const Auth = {
    user: null,

    async checkSession() {
        try {
            // Intenta obtener perfil de usuario para validar sesión
            this.user = await API.get('/auth/me');
            return true;
        } catch (error) {
            this.user = null;
            return false;
        }
    },

    async logout() {
        try {
            await API.post('/auth/logout');
        } catch(e) {}
        this.user = null;
        window.location.hash = '#login';
    },

    // Actualiza UI del perfil en el sidebar
    updateProfileUI() {
        if (!this.user) return;
        
        const avatar = document.getElementById('userAvatar');
        const name = document.getElementById('userName');
        
        if (avatar && name) {
            avatar.src = this.user.picture || 'https://ui-avatars.com/api/?name=User&background=random';
            avatar.classList.remove('skeleton');
            name.textContent = this.user.name.split(' ')[0]; // Primer nombre
            name.classList.remove('skeleton-text');
        }
    }
};
