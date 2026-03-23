/**
 * Obtiene el token CSRF del meta tag o del DOM.
 * @returns {string} El token CSRF.
 */
export function getCSRFToken() {
    // Opción 1: Desde meta tag (común en Flask)
    const metaToken = document.querySelector('meta[name="csrf-token"]');
    if (metaToken) {
        return metaToken.getAttribute('content');
    }

    // Opción 2: Desde input hidden en formularios
    const inputToken = document.querySelector('input[name="csrf_token"]');
    if (inputToken) {
        return inputToken.value;
    }

    // Opción 3: Desde cookie (si usás flask-wtf con cookie)
    const cookieMatch = document.cookie.match(/csrf_token=([^;]+)/);
    if (cookieMatch) {
        return cookieMatch[1];
    }

    console.warn('CSRF token not found');
    return '';
}