// ColorPlastic - Filtros dinámicos y búsqueda
document.addEventListener('DOMContentLoaded', function() {
    // Filtro de tabla en tiempo real
    function setupTableFilter(tableId, inputId) {
        const table = document.getElementById(tableId);
        const input = document.getElementById(inputId);
        
        if (table && input) {
            input.addEventListener('keyup', function() {
                const filter = this.value.toUpperCase();
                const rows = table.getElementsByTagName('tr');
                
                for (let i = 1; i < rows.length; i++) {
                    let row = rows[i];
                    let textContent = row.textContent || row.innerText;
                    
                    if (textContent.toUpperCase().indexOf(filter) > -1) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                }
            });
        }
    }

    // Auto-completar para lotes
    function setupLoteAutocomplete() {
        const loteInputs = document.querySelectorAll('[data-autocomplete="lotes"]');
        
        loteInputs.forEach(input => {
            input.addEventListener('input', async function() {
                const query = this.value;
                if (query.length >= 2) {
                    try {
                        const response = await fetch(`/api/lotes/search/?q=${encodeURIComponent(query)}`);
                        const lotes = await response.json();
                        
                        // Crear dropdown de sugerencias
                        showAutocompleteDropdown(this, lotes);
                    } catch (error) {
                        console.error('Error en búsqueda de lotes:', error);
                    }
                }
            });
        });
    }

    function showAutocompleteDropdown(input, items) {
        // Remover dropdown existente
        const existingDropdown = input.parentNode.querySelector('.autocomplete-dropdown');
        if (existingDropdown) {
            existingDropdown.remove();
        }

        if (items.length === 0) return;

        // Crear nuevo dropdown
        const dropdown = document.createElement('div');
        dropdown.className = 'autocomplete-dropdown position-absolute bg-white border rounded shadow-sm w-100';
        dropdown.style.zIndex = '1000';
        dropdown.style.top = '100%';
        dropdown.style.left = '0';

        items.forEach(item => {
            const option = document.createElement('div');
            option.className = 'autocomplete-option p-2 border-bottom';
            option.style.cursor = 'pointer';
            option.innerHTML = `
                <strong>${item.numero_lote}</strong><br>
                <small class="text-muted">${item.material} - Stock: ${item.stock}kg</small>
            `;
            
            option.addEventListener('click', function() {
                input.value = item.numero_lote;
                dropdown.remove();
                
                // Disparar evento change
                input.dispatchEvent(new Event('change'));
            });

            option.addEventListener('mouseenter', function() {
                this.style.backgroundColor = '#f8f9fa';
            });

            option.addEventListener('mouseleave', function() {
                this.style.backgroundColor = '';
            });

            dropdown.appendChild(option);
        });

        // Posicionar dropdown
        input.parentNode.style.position = 'relative';
        input.parentNode.appendChild(dropdown);

        // Cerrar dropdown al hacer clic fuera
        document.addEventListener('click', function closeDropdown(e) {
            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.remove();
                document.removeEventListener('click', closeDropdown);
            }
        });
    }

    // Validación de formularios en tiempo real
    function setupFormValidation() {
        const forms = document.querySelectorAll('form[data-validate]');
        
        forms.forEach(form => {
            const inputs = form.querySelectorAll('input[required], select[required]');
            
            inputs.forEach(input => {
                input.addEventListener('blur', function() {
                    validateField(this);
                });

                input.addEventListener('input', function() {
                    clearFieldError(this);
                });
            });

            form.addEventListener('submit', function(e) {
                let isValid = true;
                
                inputs.forEach(input => {
                    if (!validateField(input)) {
                        isValid = false;
                    }
                });

                if (!isValid) {
                    e.preventDefault();
                }
            });
        });
    }

    function validateField(field) {
        const value = field.value.trim();
        const fieldGroup = field.closest('.mb-3') || field.closest('.form-group');
        
        // Limpiar errores previos
        clearFieldError(field);

        if (field.hasAttribute('required') && !value) {
            showFieldError(field, 'Este campo es obligatorio');
            return false;
        }

        if (field.type === 'number' && value) {
            const num = parseFloat(value);
            if (isNaN(num) || num < 0) {
                showFieldError(field, 'Debe ingresar un número válido mayor o igual a 0');
                return false;
            }
        }

        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                showFieldError(field, 'Ingrese un email válido');
                return false;
            }
        }

        return true;
    }

    function showFieldError(field, message) {
        field.classList.add('is-invalid');
        
        const fieldGroup = field.closest('.mb-3') || field.closest('.form-group');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        
        fieldGroup.appendChild(errorDiv);
    }

    function clearFieldError(field) {
        field.classList.remove('is-invalid');
        
        const fieldGroup = field.closest('.mb-3') || field.closest('.form-group');
        const errorDiv = fieldGroup.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    // Confirmación de acciones críticas
    function setupActionConfirmations() {
        document.addEventListener('click', function(e) {
            const target = e.target;
            
            if (target.hasAttribute('data-confirm')) {
                const message = target.getAttribute('data-confirm');
                if (!confirm(message)) {
                    e.preventDefault();
                    return false;
                }
            }

            // Confirmación especial para eliminaciones
            if (target.classList.contains('btn-danger') || 
                target.closest('.btn-danger')) {
                const action = target.textContent.toLowerCase();
                if (action.includes('eliminar') || action.includes('delete')) {
                    if (!confirm('¿Está seguro que desea eliminar este elemento? Esta acción no se puede deshacer.')) {
                        e.preventDefault();
                        return false;
                    }
                }
            }
        });
    }

    // Notificaciones toast
    function showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container') || createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi ${getToastIcon(type)} me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        // Remover del DOM después de que se oculte
        toast.addEventListener('hidden.bs.toast', function() {
            this.remove();
        });
    }

    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1055';
        document.body.appendChild(container);
        return container;
    }

    function getToastIcon(type) {
        const icons = {
            'success': 'bi-check-circle-fill',
            'danger': 'bi-exclamation-triangle-fill',
            'warning': 'bi-exclamation-circle-fill',
            'info': 'bi-info-circle-fill'
        };
        return icons[type] || icons.info;
    }

    // Inicializar funcionalidades
    setupFormValidation();
    setupActionConfirmations();
    setupLoteAutocomplete();

    // Hacer funciones disponibles globalmente
    window.ColorPlastic = {
        showToast: showToast,
        setupTableFilter: setupTableFilter
    };
});

// Utilidades para fechas
function formatDateForInput(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toISOString().split('T')[0];
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        minimumFractionDigits: 0
    }).format(amount);
}

function formatWeight(weight) {
    return `${parseFloat(weight).toLocaleString('es-CO')} kg`;
}