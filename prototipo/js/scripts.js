// Funciones comunes para todos los prototipos

document.addEventListener('DOMContentLoaded', () => {
    // Manejo de Modales
    const modalTriggers = document.querySelectorAll('[data-modal-target]');
    const modalCloseBtns = document.querySelectorAll('.close-btn, [data-modal-close]');
    const modals = document.querySelectorAll('.modal-overlay');

    // Abrir modal
    modalTriggers.forEach(trigger => {
        trigger.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = trigger.getAttribute('data-modal-target');
            const modal = document.getElementById(targetId);
            if (modal) {
                modal.style.display = 'flex';
            }
        });
    });

    // Cerrar modal
    modalCloseBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const modal = btn.closest('.modal-overlay');
            if (modal) {
                modal.style.display = 'none';
            }
        });
    });

    // Cerrar al hacer clic fuera del contenido del modal
    modals.forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    });

    // Simulador de guardado genérico
    const saveForms = document.querySelectorAll('.simulate-save');
    saveForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            alert('Acción completada exitosamente (Prototipo)');
            const modal = form.closest('.modal-overlay');
            if (modal) {
                modal.style.display = 'none';
            }
        });
    });

    // Simulador de redirección genérico
    const simLinks = document.querySelectorAll('.simulate-link');
    simLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const href = link.getAttribute('href');
            if(href && href !== '#') {
                window.location.href = href;
            } else {
                alert('Navegación simulada (Prototipo)');
            }
        });
    });

});
