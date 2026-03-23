import { CartService } from './cart-service.js';
import { CartUI } from './cart-ui.js';
import { showToast } from '../../utils/toast.js';

document.addEventListener('DOMContentLoaded', () => {
    initCatalogEvents();
});

function initCatalogEvents() {
    // Usamos delegación de eventos en el body para capturar formularios AJAX
    document.body.addEventListener('submit', async (e) => {
        
        // 1. Verificamos si el formulario disparado tiene la clase 'ajax-add-form'
        // (Esta clase debes ponerla en tu <form> en solicitar_insumos.html)
        if (!e.target.matches('.ajax-add-form')) return;

        e.preventDefault(); // Evitamos recarga de página normal
        const form = e.target;
        const submitBtn = form.querySelector('button[type="submit"]');

        // 2. Estado de Carga (UI)
        CartUI.setButtonLoading(submitBtn, true);

        try {
            // 3. Llamada al Backend (Service)
            const formData = new FormData(form);
            const response = await CartService.addItem(form.action, formData);

            // 4. Respuesta Exitosa
            if (response.success) {
                showToast(response.message, 'success');
                CartUI.markAsAdded(submitBtn);
                const cartCount = response.cart_count || 0;
                CartUI.updateCartBadge(cartCount);
            } else {
                // Error de negocio (ej: no hay stock real)
                showToast(response.message, 'warning');
                CartUI.setButtonLoading(submitBtn, false); // Restaurar botón
            }

        } catch (error) {
            // 5. Error de Red/Servidor
            console.error(error);
            showToast('Error de conexión con el servidor', 'danger');
            CartUI.setButtonLoading(submitBtn, false); // Restaurar botón
        }
    });
}