import { getCSRFToken } from '../../utils/csrf.js'

export const CartService = {
    async addItem(url, formData) {
        //Aseguramos que el CSRF token vaya en el header o body.
        formData.append('csrf_token', getCSRFToken());

        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData, 
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                    'Accept': 'application/json', // Esperamos JSON de respuesta.
                    'X-Requested-With': 'XMLHttpRequest' // Para que Flask reconozca como AJAX
                }
            });

            if (!response.ok) throw new Error('Error en la red');

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Respuesta no es JSON o respuesta no válida del servidor.');
            }

            return await response.json();
        } catch (error) {
            console.error('Cartservice error:', error);
            throw error;
        }
    },

    async removeItem(url, formData) {
        //Reutilizamos lógica si es igual o personalizamos.
        return this.addItem(url, formData);
    }
};