// Cliente API Centralizado
const API = {
    async request(url, options = {}) {
        const config = { ...options };
        if (!config.headers) config.headers = {};

        if (!(options.body instanceof FormData)) {
            config.headers['Content-Type'] = 'application/json';
        }

        // Si hay onProgress, usamos XHR para trackear la subida
        if (options.onProgress) {
            return new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                xhr.open(options.method || 'GET', `/api${url}`);
                
                // Configurar headers
                Object.keys(config.headers).forEach(key => {
                    xhr.setRequestHeader(key, config.headers[key]);
                });

                xhr.upload.onprogress = (e) => {
                    if (e.lengthComputable) {
                        const percent = Math.round((e.loaded / e.total) * 100);
                        options.onProgress(percent);
                    }
                };

                xhr.onload = () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        try {
                            resolve(JSON.parse(xhr.responseText));
                        } catch (e) {
                            resolve(xhr.responseText);
                        }
                    } else if (xhr.status === 401) {
                        window.location.hash = '#login';
                        reject(new Error('No autorizado'));
                    } else {
                        reject(new Error(xhr.statusText || 'Error en la petición'));
                    }
                };

                xhr.onerror = () => reject(new Error('Error de red'));
                xhr.send(options.body);
            });
        }
        
        // Fallback a fetch normal para el resto
        try {
            const response = await fetch(`/api${url}`, config);
            
            if (response.status === 401) {
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
