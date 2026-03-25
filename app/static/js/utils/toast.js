/**
 * Muestra una notificación flotante.
 * @param {string} message - El texto a mostrar.
 * @param {string} category - 'success', 'danger', 'warning', 'info'.
 */
export function showToast(message, category = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) {
        console.warn('Toast container not found');
        return; 
    }

    // Mapeo de categorías a colores
    const colors = {
        'success': 'bg-primary hover:bg-primary/90 border-primary',
        'danger': 'bg-rose-500/90 border-rose-400',
        'warning': 'bg-amber-500/90 border-amber-400',
        'info': 'bg-blue-500/90 border-blue-400'
    };

    const textColors = {
        'success': 'text-charcoal-950',
        'danger': 'text-white',
        'warning': 'text-white',
        'info': 'text-white',

    }

    const icons = {
        'success': 'check_circle',
        'danger': 'error',
        'warning': 'warning',
        'info': 'info'
    };

    const colorClass = colors[category] || colors['info'];
    const icon = icons[category] || icons['info'];
    const textColor = textColors[category] || textColors['info'];

    // Crear elemento
    const toast = document.createElement('div');
    toast.className = `flex items-center gap-3 ${colorClass} ${textColor} px-4 py-3 rounded-lg shadow-xl border-2 pointer-events-auto transform transition-all duration-300 ease-out`;
    toast.style.minWidth = '300px';
    toast.innerHTML = `
        <span class="material-symbols-outlined text-xl">${icon}</span>
        <span class="flex-1 text-sm font-medium">${message}</span>
        <button class="toast-close ${textColor}/70 hover:${textColor} transition-colors">
            <span class="material-symbols-outlined text-lg">close</span>
        </button>
    `;

    // Agregar al DOM con animación
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    container.appendChild(toast);

    // Animar entrada
    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(0)';
    });

    // Botón cerrar
    toast.querySelector('.toast-close')?.addEventListener('click', () => {
        removeToast(toast);
    });

    // Auto eliminar a los 4 segundos
    setTimeout(() => {
        removeToast(toast);
    }, 4000);
}

function removeToast(toast) {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
}