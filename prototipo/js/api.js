// Cliente API para Asistencia-NURR
const API_BASE = '/api/v1';

const API = {
    // Manejo de Tokens
    getToken() {
        return localStorage.getItem('asistencia_jwt_token');
    },
    setToken(token) {
        localStorage.setItem('asistencia_jwt_token', token);
    },
    clearAuth() {
        localStorage.removeItem('asistencia_jwt_token');
        localStorage.removeItem('asistencia_user_profile');
    },
    getUser() {
        const u = localStorage.getItem('asistencia_user_profile');
        return u ? JSON.parse(u) : null;
    },
    setUser(user) {
        localStorage.setItem('asistencia_user_profile', JSON.stringify(user));
    },

    // Notificaciones Toast
    showToast(message, type = 'info') {
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.style.position = 'fixed';
            toastContainer.style.top = '20px';
            toastContainer.style.right = '20px';
            toastContainer.style.zIndex = '9999';
            toastContainer.style.display = 'flex';
            toastContainer.style.flexDirection = 'column';
            toastContainer.style.gap = '10px';
            document.body.appendChild(toastContainer);
        }

        const toast = document.createElement('div');
        const bgColors = {
            success: '#2e7d32',
            error: '#c62828',
            warning: '#ef6c00',
            info: '#0d47a1'
        };
        toast.style.backgroundColor = bgColors[type] || '#333';
        toast.style.color = '#fff';
        toast.style.padding = '12px 20px';
        toast.style.borderRadius = '6px';
        toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
        toast.style.fontSize = '14px';
        toast.style.maxWidth = '350px';
        toast.style.transition = 'opacity 0.3s ease';
        toast.textContent = message;

        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },

    // Petición HTTP autenticada
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const headers = options.headers || {};
        const token = this.getToken();

        if (token && !headers['Authorization']) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        if (!(options.body instanceof FormData) && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }

        options.headers = headers;

        try {
            const response = await fetch(url, options);

            if (response.status === 401) {
                this.clearAuth();
                if (!window.location.pathname.includes('login.html') && !window.location.pathname.includes('marcacion.html')) {
                    window.location.href = 'login.html';
                }
                throw new Error('Sesión expirada o no autorizada.');
            }

            if (response.status === 403) {
                const errData = await response.json().catch(() => ({}));
                const msg = errData.detail || 'Acceso restringido.';
                this.showToast(msg, 'error');
                throw new Error(msg);
            }

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                let msg = `Error en la solicitud (${response.status})`;
                if (Array.isArray(errData.detail)) {
                    msg = errData.detail.map(d => {
                        const loc = d.loc ? d.loc.filter(l => l !== 'body').join('.') : '';
                        return loc ? `${loc}: ${d.msg}` : d.msg;
                    }).join(' | ');
                } else if (typeof errData.detail === 'string') {
                    msg = errData.detail;
                }
                this.showToast(msg, 'error');
                throw new Error(msg);
            }

            // Descarga de archivos binarios
            const contentType = response.headers.get('content-type') || '';
            if (contentType.includes('application/pdf') || contentType.includes('text/csv') || contentType.includes('image/')) {
                return await response.blob();
            }

            return await response.json();
        } catch (err) {
            console.error('API Error:', err);
            throw err;
        }
    },

    // Métodos de Autenticación
    async login(documento, password) {
        const data = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ documento_identidad: documento, password: password })
        });
        this.setToken(data.access_token);
        this.setUser(data.user);
        return data;
    },

    async logout() {
        try {
            await this.request('/auth/logout', { method: 'POST' });
        } catch (_) {}
        this.clearAuth();
        window.location.href = 'login.html';
    },

    async getMe() {
        return await this.request('/auth/me');
    },

    // Punto de Marcación Kiosco (No requiere JWT)
    async verificarUsuarioMarcacion(documento) {
        return await this.request('/marcacion/verificar-usuario', {
            method: 'POST',
            body: JSON.stringify({ documento_identidad: documento })
        });
    },

    async registrarMarcacion(payload) {
        return await this.request('/marcacion/registrar', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },
    requireAuth() {
        const token = this.getToken();
        const currentPath = window.location.pathname;
        if (!token && !currentPath.includes('login.html') && !currentPath.includes('marcacion.html')) {
            window.location.href = 'login.html';
            return false;
        }
        return true;
    },

    initUserDisplay() {
        const u = this.getUser();
        const el = document.getElementById('user-display');
        if (el && u) {
            const name = u.nombre_completo || `${u.nombres || u.nombre || ''} ${u.apellidos || u.apellido || ''}`.trim() || u.documento_identidad;
            el.textContent = `${name} (${u.rol || 'Admin'})`;
        }
    },

    // Utilidades para Documento de Identidad Venezolano (Cédula)
    formatDocumento(tipo, numero) {
        const cleanTipo = (tipo || 'V').toString().trim().toLowerCase();
        const cleanNum = (numero || '').toString().replace(/\D/g, '');
        if (!cleanNum) return '';
        const numVal = parseInt(cleanNum, 10);
        if (numVal === 0) {
            return `${cleanTipo}-00000000`;
        }
        return `${cleanTipo}-${numVal}`;
    },

    parseDocumento(docStr) {
        if (!docStr) return { tipo: 'V', numero: '' };
        const str = docStr.toString().trim();
        let tipo = 'V';
        let numPart = str;
        const match = str.match(/^([veVE])\s*[-]?\s*(.*)$/);
        if (match) {
            tipo = match[1].toUpperCase();
            numPart = match[2];
        }
        const numero = numPart.replace(/\D/g, '');
        return { tipo, numero };
    },

    validateDocumento(tipo, numero, allowAdminZero = false) {
        if (!numero || numero.toString().trim() === '') {
            return { valid: false, message: 'El número de documento de identidad es requerido.' };
        }
        const cleanNum = numero.toString().replace(/\D/g, '');
        if (!cleanNum) {
            return { valid: false, message: 'El documento debe contener únicamente caracteres numéricos.' };
        }
        const val = parseInt(cleanNum, 10);
        if (val === 0) {
            if (allowAdminZero) {
                return { valid: true };
            }
            return { valid: false, message: 'El número de documento debe estar comprendido entre 1000000 y 99999999.' };
        }
        if (val < 1000000 || val > 99999999) {
            return { valid: false, message: 'El número de documento debe estar comprendido entre 1000000 y 99999999.' };
        }
        return { valid: true };
    },

    initCedulaInput({ selectId, inputId, errorId = null, allowAdminZero = false, onChange = null }) {
        const selEl = typeof selectId === 'string' ? document.getElementById(selectId) : selectId;
        const inpEl = typeof inputId === 'string' ? document.getElementById(inputId) : inputId;
        const errEl = errorId ? (typeof errorId === 'string' ? document.getElementById(errorId) : errorId) : null;

        if (!selEl || !inpEl) {
            console.warn('initCedulaInput: No se encontraron los elementos select o input especificados.');
            return null;
        }

        // Restringir a sólo dígitos en keypress
        inpEl.addEventListener('keypress', (e) => {
            // Permitir teclas de control
            if (e.ctrlKey || e.altKey || e.metaKey) return;
            if (e.charCode < 48 || e.charCode > 57) {
                e.preventDefault();
            }
        });

        // Filtrar y limitar longitud en evento input
        inpEl.addEventListener('input', () => {
            const raw = inpEl.value;
            const digits = raw.replace(/\D/g, '').slice(0, 8);
            if (raw !== digits) {
                inpEl.value = digits;
            }
            if (errEl) {
                errEl.style.display = 'none';
                errEl.textContent = '';
                inpEl.style.borderColor = '';
            }
            if (typeof onChange === 'function') {
                onChange(ctrl.getFormatted());
            }
        });

        // Soporte inteligente para pegado (paste)
        inpEl.addEventListener('paste', (e) => {
            e.preventDefault();
            const text = (e.clipboardData || window.clipboardData).getData('text') || '';
            const parsed = API.parseDocumento(text);
            if (parsed.tipo) {
                selEl.value = parsed.tipo;
            }
            inpEl.value = (parsed.numero || '').slice(0, 8);
            if (errEl) {
                errEl.style.display = 'none';
                inpEl.style.borderColor = '';
            }
            if (typeof onChange === 'function') {
                onChange(ctrl.getFormatted());
            }
        });

        const ctrl = {
            selectElement: selEl,
            inputElement: inpEl,
            errorElement: errEl,
            getTipo() {
                return selEl.value || 'V';
            },
            getNumero() {
                return (inpEl.value || '').replace(/\D/g, '');
            },
            getValue() {
                return {
                    tipo: this.getTipo(),
                    numero: this.getNumero(),
                    formatted: this.getFormatted()
                };
            },
            setValue(docStr) {
                const parsed = API.parseDocumento(docStr);
                selEl.value = parsed.tipo || 'V';
                inpEl.value = parsed.numero || '';
                if (errEl) errEl.style.display = 'none';
                inpEl.style.borderColor = '';
            },
            validate(customAllowZero = allowAdminZero) {
                const res = API.validateDocumento(this.getTipo(), this.getNumero(), customAllowZero);
                if (!res.valid) {
                    if (errEl) {
                        errEl.textContent = res.message;
                        errEl.style.display = 'block';
                    }
                    inpEl.style.borderColor = 'var(--danger-color)';
                    return false;
                }
                if (errEl) {
                    errEl.style.display = 'none';
                    errEl.textContent = '';
                }
                inpEl.style.borderColor = '';
                return true;
            },
            getFormatted(customAllowZero = allowAdminZero) {
                const numero = this.getNumero();
                if (!numero) return '';
                return API.formatDocumento(this.getTipo(), numero);
            },
            clear() {
                selEl.value = 'V';
                inpEl.value = '';
                if (errEl) {
                    errEl.style.display = 'none';
                    errEl.textContent = '';
                }
                inpEl.style.borderColor = '';
            },
            setDisabled(disabled) {
                selEl.disabled = disabled;
                inpEl.disabled = disabled;
            }
        };

        return ctrl;
    }
};

document.addEventListener('DOMContentLoaded', () => {
    API.requireAuth();
    API.initUserDisplay();
});

window.API = API;
