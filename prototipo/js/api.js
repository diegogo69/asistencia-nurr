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
        this.initAdminServerControls();
    },

    isAdmin() {
        const u = this.getUser();
        if (!u) return false;
        const rol = (u.rol || '').toLowerCase();
        return Boolean(u.requiere_password || rol.includes('admin') || rol.includes('coordinador'));
    },

    async getServerStatus() {
        return await this.request('/sistema/estado');
    },

    async getServerLogs(lineas = 100) {
        return await this.request(`/sistema/logs?lineas=${encodeURIComponent(lineas)}`);
    },

    async shutdownServer() {
        return await this.request('/sistema/detener', { method: 'POST' });
    },

    initAdminServerControls() {
        if (!this.getToken() || !this.isAdmin()) return;
        const currentPath = window.location.pathname;
        if (currentPath.includes('login.html') || currentPath.includes('marcacion.html')) return;

        const userInfo = document.querySelector('.top-bar .user-info');
        if (userInfo && !document.getElementById('btn-admin-stop-server')) {
            const stopBtn = document.createElement('button');
            stopBtn.id = 'btn-admin-stop-server';
            stopBtn.type = 'button';
            stopBtn.className = 'btn btn-danger';
            stopBtn.title = 'Detener la ejecución del servidor (Perfil Administrador)';
            stopBtn.style.display = 'inline-flex';
            stopBtn.style.alignItems = 'center';
            stopBtn.style.gap = '6px';
            stopBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"></path><line x1="12" y1="2" x2="12" y2="12"></line></svg> Detener Servidor`;
            stopBtn.addEventListener('click', () => this.openShutdownModal());
            userInfo.appendChild(stopBtn);
        }
    },

    openShutdownModal() {
        let overlay = document.getElementById('admin-shutdown-modal-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'admin-shutdown-modal-overlay';
            overlay.className = 'modal-overlay';
            overlay.style.zIndex = '10000';
            overlay.innerHTML = `
                <div class="modal" role="dialog" aria-modal="true" aria-labelledby="shutdown-modal-title">
                    <div class="modal-header">
                        <h3 id="shutdown-modal-title" style="color: var(--danger-color); display: flex; align-items: center; gap: 8px;">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"></path><line x1="12" y1="2" x2="12" y2="12"></line></svg>
                            Detener Ejecución del Servidor
                        </h3>
                        <button type="button" class="close-btn" id="shutdown-modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <p style="margin-bottom: 12px; font-weight: 500;">¿Está seguro de que desea detener el servidor de la aplicación <strong>Asistencia-NURR</strong>?</p>
                        <p style="font-size: 13.5px; color: var(--text-light); line-height: 1.5;">
                            La consola de comandos se ejecuta en segundo plano. Al confirmar esta acción, se finalizará el servidor web de forma segura, se guardarán todos los registros en la carpeta <code>logs/</code> y la aplicación dejará de estar accesible hasta que vuelva a iniciarse el ejecutable.
                        </p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" id="shutdown-modal-cancel">Cancelar</button>
                        <button type="button" class="btn btn-danger" id="shutdown-modal-confirm">Sí, Detener Servidor</button>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);

            const closeFn = () => {
                overlay.style.display = 'none';
            };
            overlay.querySelector('#shutdown-modal-close').addEventListener('click', closeFn);
            overlay.querySelector('#shutdown-modal-cancel').addEventListener('click', closeFn);
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) closeFn();
            });

            overlay.querySelector('#shutdown-modal-confirm').addEventListener('click', async () => {
                const confirmBtn = overlay.querySelector('#shutdown-modal-confirm');
                confirmBtn.disabled = true;
                confirmBtn.textContent = 'Deteniendo...';
                try {
                    const res = await this.shutdownServer();
                    overlay.style.display = 'none';
                    this.showServerStoppedScreen(res);
                } catch (err) {
                    confirmBtn.disabled = false;
                    confirmBtn.textContent = 'Sí, Detener Servidor';
                    this.showToast(err.message || 'No se pudo detener el servidor.', 'error');
                }
            });
        }
        overlay.style.display = 'flex';
    },

    showServerStoppedScreen(res) {
        const stoppedOverlay = document.createElement('div');
        stoppedOverlay.id = 'server-stopped-overlay';
        stoppedOverlay.style.cssText = 'position:fixed;inset:0;background:rgba(15,23,42,0.94);z-index:20000;display:flex;justify-content:center;align-items:center;padding:24px;';
        stoppedOverlay.innerHTML = `
            <div style="background:#ffffff;max-width:480px;width:100%;border-radius:10px;padding:32px;text-align:center;box-shadow:0 20px 50px rgba(0,0,0,0.4);">
                <div style="width:60px;height:60px;border-radius:50%;background:#fde8e8;color:#c62828;display:flex;align-items:center;justify-content:center;margin:0 auto 18px auto;">
                    <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"></path><line x1="12" y1="2" x2="12" y2="12"></line></svg>
                </div>
                <h2 style="color:#1e293b;margin-bottom:10px;font-size:1.4rem;">Servidor Detenido</h2>
                <p style="color:#475569;font-size:14.5px;margin-bottom:16px;line-height:1.5;">
                    El servidor de <strong>Asistencia-NURR</strong> se ha detenido de forma ordenada. Los registros de operación han sido guardados en el directorio <code>logs/</code>.
                </p>
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px;font-size:12.5px;color:#64748b;margin-bottom:20px;">
                    Detenido por: <strong>${(res && res.detenido_por) ? res.detenido_por : 'Administrador'}</strong>
                </div>
                <p style="color:#64748b;font-size:13px;">Ya puede cerrar esta pestaña o ventana del navegador de forma segura.</p>
            </div>
        `;
        document.body.appendChild(stoppedOverlay);
    },

    async openLogsModal() {
        let overlay = document.getElementById('admin-logs-modal-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'admin-logs-modal-overlay';
            overlay.className = 'modal-overlay';
            overlay.style.zIndex = '10000';
            overlay.innerHTML = `
                <div class="modal large" role="dialog" aria-modal="true" aria-labelledby="logs-modal-title">
                    <div class="modal-header">
                        <h3 id="logs-modal-title">Registros del Sistema (Logs)</h3>
                        <button type="button" class="close-btn" id="logs-modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;gap:10px;flex-wrap:wrap;">
                            <span id="logs-file-path" style="font-size:12.5px;color:var(--text-light);font-family:monospace;">Ruta: logs/asistencia.log</span>
                            <button type="button" class="btn btn-secondary btn-icon" id="logs-refresh-btn">Actualizar</button>
                        </div>
                        <pre id="logs-viewer-content" style="background:#0f172a;color:#e2e8f0;padding:14px;border-radius:6px;font-size:12px;line-height:1.45;max-height:420px;overflow:auto;white-space:pre-wrap;word-break:break-word;">Cargando registros...</pre>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary" id="logs-modal-ok">Cerrar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);

            const closeFn = () => {
                overlay.style.display = 'none';
            };
            overlay.querySelector('#logs-modal-close').addEventListener('click', closeFn);
            overlay.querySelector('#logs-modal-ok').addEventListener('click', closeFn);
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) closeFn();
            });
            overlay.querySelector('#logs-refresh-btn').addEventListener('click', () => this.refreshLogsContent());
        }
        overlay.style.display = 'flex';
        await this.refreshLogsContent();
    },

    async refreshLogsContent() {
        const pre = document.getElementById('logs-viewer-content');
        const pathEl = document.getElementById('logs-file-path');
        if (!pre) return;
        pre.textContent = 'Cargando registros...';
        try {
            const data = await this.getServerLogs(120);
            if (pathEl && data.logs_path) {
                pathEl.textContent = `Archivo: ${data.logs_path}`;
            }
            if (data.logs && data.logs.length > 0) {
                pre.textContent = data.logs.join('\n');
                pre.scrollTop = pre.scrollHeight;
            } else {
                pre.textContent = 'No hay registros disponibles aún.';
            }
        } catch (err) {
            pre.textContent = `Error al cargar registros: ${err.message}`;
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
