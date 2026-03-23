export const CartUI = {
    /**
     * Cambia el estado del botón a "Cargando..."
     */
    setButtonLoading(btn, isLoading) {
        if (isLoading) {
            // Guardamos el texto original en un atributo de datos
            btn.dataset.originalHtml = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<span class="material-symbols-outlined text-sm animate-spin">progress_activity</span> Agregando...'; // O un spinner <i class="fas fa-spinner fa-spin"></i>
            btn.style.opacity = '0.7';
        } else {
            // Restauramos texto original
            btn.innerHTML = btn.dataset.originalHtml || '<span class="material-symbols-outlined text-sm">add_shopping_cart</span> Agregar';
            btn.disabled = false;
            btn.style.opacity = '1';
        }
    },

    /**
     * Transforma el botón a estado "En Carrito" (Verde y bloqueado)
     */
    markAsAdded(btn) {
        const form = btn.closest('form');
        const row = form.closest('tr');

        if (form) {
            //Reemplazamos el form completo con el botón disabled.
            form.outerHTML = `
                <button disabled 
                        class="inline-flex items-center gap-2 px-4 py-2 bg-primary/20 border border-primary/40 text-primary rounded-lg text-xs font-bold transition-all uppercase tracking-wider cursor-not-allowed">
                    <span class="material-symbols-outlined text-sm">check</span>
                    En Carrito
                </button>
            `;
        }
        
        //Actualizamos el icono de la fila.
        if (row) {
            row.classList.add('bg-primary/5'); // Resalta la fila
            row.dataset.enCarrito = 'true'; // Marcar como agregado (opcional, para lógica futura)

            const icon = row.querySelector('.w-10 .material-symbols-outlined');
            if (icon) {
                icon.textContent = 'check_circle';
                icon.classList.remove('text-slate-400');
                icon.classList.add('text-primary');
            }
        }
    },

    /**
     * Actualiza el contador del carrito en el navbar (si existe)
     */
    updateCartBadge(count) {
        //Actualizar números simples.
        document.querySelectorAll('.cart-badge-count').forEach(badge => {
            //Si es un badge con texto (ej: "3 items"), actualizamos solo el número.
            if (badge.classList.contains('font-semibold')) {
                const plural = count === 1 ? 's' : '';
                badge.textContent = `${count} insumo${plural}`;
            } else {
                //Si es solo el número.
                badge.textContent = count;
            }
        });

        //Mostar/ocultar header indicator.
        const headerIndicator = document.getElementById('header-cart-indicator');
        if (headerIndicator) {
            if (count > 0 && !headerIndicator.querySelector('a')) {
                //Crear el indicador si no existe.
                headerIndicator.innerHTML = `<a href="/confirmar_solicitud_insumos" 
                       class="flex items-center gap-2 px-4 py-2 border border-primary/30 bg-primary/10 text-primary rounded-lg text-sm font-medium hover:bg-primary/20 transition-colors">
                        <span class="material-symbols-outlined text-lg">shopping_cart</span>
                        <span class="font-bold cart-badge-count">${count}</span>
                        <span>items</span>
                    </a>
                `;
            }      
        }
        //Mostrar panel flotante si hay items.
        const floatingPanel = document.getElementById('floating-cart-panel');
        if (floatingPanel) {
            if (count >0) {
                floatingPanel.classList.remove('opacity-0', 'translate-y-4');
            } else {
                floatingPanel.classList.add('opacity-0', 'translate-y-4', 'pointer-events-none');
            }
        }
        this.updateCartDropdown(count);
    },
    /*Nueva Funcipón: Actualiza el contenido interno del dropdown del carrito*/ 
    updateCartDropdown(count) {
        const dropdownContent = document.getElementById('cart-dropdown-content');
        if (!dropdownContent) {
            console.wawn('No se encontró el contenido del dropdown del carrito para actualizar.');
            return;
        }
        if (count === 0) {
            //Carrito vacio
            dropdownContent.innerHTML = `
                <div class="flex justify-between items-center">
                    <span class="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Items</span>
                    <span class="cart-badge-count text-lg font-bold text-white">0</span>
                </div>
                <div class="text-center py-3">
                    <span class="material-symbols-outlined text-3xl text-charcoal-600 mb-2 block">shopping_cart</span>
                    <p class="text-[10px] text-slate-500">Carrito vacío</p>
                </div>
            `;
        } else {
            //Carrito con items.
            dropdownContent.innerHTML = `
                <div class="flex justify-between items-center">
                    <span class="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Items</span>
                    <span class="cart-badge-count text-lg font-bold text-white">${count}</span>
                </div>
                <a href="/confirmar_solicitud_insumos" 
                   class="w-full py-2 bg-primary hover:bg-primary/90 text-charcoal-950 rounded-lg font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-md">
                    <span class="material-symbols-outlined text-sm">check_circle</span>
                    Confirmar Solicitud
                </a>
            `;
        }
    }
};