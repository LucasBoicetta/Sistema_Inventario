/**
 * Sistema de Carrito con AJAX y Progressive Enhancement
 * - Funciona sin JS (formularios tradicionales)
 * - Mejora UX cuando JS está habilitado
 */

document.addEventListener('DOMContentLoaded', () => {
    initializeCartSystem();
});

function initializeCartSystem() {
    console.log('🚀 Sistema de carrito inicializado');

    //Interceptar formularios de agregar.
    document.querySelectorAll('.ajax-add-form').forEach(form => {
        form.addEventListener('submit', handleAddSubmit);
    });

    //Interceptar formularios de eliminar.
    document.querySelectorAll('.ajax-delete-form').forEach(form => {
        form.addEventListener('submit', handleDeleteSubmit);
    });

}

async function handleAddSubmit(e){
    e.preventDefault();

    const form = e.target;
    const btn = form.querySelector('button[type="submit"]');
    const originalHTML = btn.innerHTML;
    const originalClass = btn.className;

    //UI feedback inmmediato.
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner">⏳</span> Agregando...';

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams(new FormData(form))
        });

        //Verificar si la respuesta es JSON.
        const contentType = response.headers.get('content-type');

        if (response.ok && contentType && contentType.includes('application/json')) {
            const data = await response.json();

            if (data.success) {
                //Actualizar el badge.
                updateCartBadge(data.cart_count);

                //Cambiar botón a estado "Agregado".
                btn.className = 'btn btn-secundary btn-small';
                btn.innerHTML = '✔ Agregado';

                //Mostrar notificación.
                showToast(data.messasge, data.category);


                //Restaurar botón después de 2 segundos (opcional).
                setTimeout(() => {
                    btn.className = originalClass;
                    btn.innerHTML = originalHTML;
                    btn.disabled = false;
                }, 2000);
            } else {
                showToast(data.message, data.category);
                btn.disabled = false;
                btn.innerHTML = originalHTML;
            }
        } else {
            //Fallback: Si no es JSON, recargar la página.
            window.location.reload();
        }        
    } catch (error) {
        console.error('Error', error);
        showToast('Error al agregar el insumo.', 'danger');
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }
}

async function handleDeleteSubmit(e){
    e.preventDefault();

    const form = e.target;
    const btn = form.querySelector('button[type="submit"]');
    const originalHTML = btn.innerHTML;

    //Confirmación (opcional).
    if (!confirm('¿Eliminar este insumo del carrito?')) {
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner">⏳</span>';

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams(new FormData(form))
        });

        const contentType = response.headers.get('content-type');

        if (response.ok && contentType && contentType.includes('application/json')) {
            const data = await response.json();

            if (data.success) {
                //Actualizar el badge.
                updateCartBadge(data.cart_count);

                //Animar y eliminar la fila.
                const row = form.closest('tr');
                if (row) {
                    row.classList.add('fade-out-row');

                    setTimeout(() => {
                        row.remove();

                        //Verificar si el carrito quedó vacío.
                        if (data.is_empty) {
                            showEmptyState();
                        } else {
                            renumberRows();
                        }
                    }, 500);
                }

                showToast(data.message, data.category);
            } else {
                showToast(data.message, data.category);
                btn.disabled = false;
                btn.innerHTML = originalHTML;
            }
        } else {
            //Fallback: Si no es JSON, recargar la página.
            window.location.reload();
        }
    } catch (error) {
        console.error('Error', error);
        showToast('Error al eliminar el insumo.', 'danger');
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }
}

function updateCartBadge(count) {
    const badge = document.getElementById('cart-badge');

    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline-block' : 'none';

        //Animación pop.
        badge.classList.remove('pop-anim');
        void badge.offsetWidth; // Reflow
        badge.classList.add('pop-anim');
    }    
}

function showEmptyState() {
    const cartContent = document.getElementById('cart-content');
    const emptyState = document.getElementById('empty-state');

    //Cambiar luego por clases CSS para animaciones más suaves.
    if (cartContent) {
        cartContent.style.transition = 'opacity 0.5s';
        cartContent.style.opacity = '0';
        setTimeout(() => {
            cartContent.style.display = 'none';
        } , 500);    
    }

    if (emptyState) {
        emptyState.style.display = 'block';
        emptyState.opacity = '0';
        setTimeout(() => {
            emptyState.style.transition = 'opacity 0.5s';
            emptyState.style.opacity = '1';
        }, 50);
    }
}

function renumberRows() {
    const rows = document.querySelectorAll('#cart-table tbody tr');
    rows.forEach((row, index) => {
        const firstCell = row.querySelector('td:first-child');
        if (firstCell) {
            firstCell.textContent = index + 1;
        }
    });
}

function showToast(message, category) {
    let container = document.getElementById('toast-container');

    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    //Iconos por categoria.
    const icons = {
        'success': '✔',
        'danger': '✖',
        'warning': '⚠',
        'info': 'ℹ'
    };
    const icon = icons[category] || 'ℹ';

    // Crear el toast.
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${category}`;
    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-message">${message}</div>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;
    container.appendChild(toast);

    //Animacion de entrada.
    requestAnimationFrame(() => {
        toast.classList.add('toast-visible');
    });

    //Auto-eliminar despues de 4 segundos.
    setTimeout(() => {
        toast.classList.remove('toast-visible');
        setTimeout(() => {
            toast.remove();
        }, 400);
    }, 4000);
}