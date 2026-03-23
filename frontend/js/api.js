// Cliente API Centralizado
const API = {
    async request(url, options = {}) {
        // Asume que la auth cookie (session_token) se envía automáticamente
        // si httponly=true o si configuramos include
        const config = { ...options };
        if (!config.headers) config.headers = {};

        // No poner Content-Type si es FormData (el navegador lo pondrá con el boundary)
        if (!(options.body instanceof FormData)) {
            config.headers['Content-Type'] = 'application/json';
        }
        
        try {
            const response = await fetch(`/api${url}`, config);
            
            if (response.status === 401) {
                // Redirigir a login si expira
                window.location.hash = '#login';
                throw new Error('No autorizado');
            }
            
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Error en la petición');
            }
            
            return await response.json();
            
        } catch (error) {
            console.error(`API Error (${url}):`, error);
            throw error;
        }
    },

    get(url) { return this.request(url, { method: 'GET' }); },
    post(url, body) { return this.request(url, { method: 'POST', body: JSON.stringify(body) }); },
    put(url, body) { return this.request(url, { method: 'PUT', body: JSON.stringify(body) }); },
    delete(url) { return this.request(url, { method: 'DELETE' }); }
};
