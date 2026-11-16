"""Launcher de Escritorio con Interfaz Gráfica Minimalista para Asistencia-NURR.

Inicia automáticamente el servidor de la aplicación (FastAPI/Uvicorn en HTTPS),
abre la aplicación en una pestaña del navegador predeterminado y mantiene un
registro exhaustivo de logs en el directorio dedicado 'logs/' del repositorio.
Diseñado y optimizado con compatibilidad nativa para Windows 10 (sin consola visible).
"""

import os
import sys
import time
import socket
import logging
from logging.handlers import RotatingFileHandler
import queue
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import ssl


# ==============================================================================
# CONFIGURACIÓN DE RUTAS Y ENTORNO
# ==============================================================================
def get_base_dir() -> str:
    """Obtiene el directorio base de la aplicación, ya sea en modo script o compilado."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
os.chdir(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Directorio dedicado de logs
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOGS_DIR, "asistencia.log")


# ==============================================================================
# SOPORTE DE ALTA RESOLUCIÓN (HIGH-DPI) EN WINDOWS 10
# ==============================================================================
def enable_high_dpi_windows():
    """Habilita escalado DPI nítido en Windows 10 para evitar fuentes borrosas."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                import ctypes
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


# ==============================================================================
# SISTEMA DE LOGS MULTI-DESTINO (ARCHIVO + COLA GUI + REDIRECCIÓN STDOUT/STDERR)
# ==============================================================================
log_queue = queue.Queue(maxsize=1000)


class QueueLogHandler(logging.Handler):
    """Handler que envía los registros de log a una cola para la interfaz gráfica."""
    def __init__(self, target_queue: queue.Queue):
        super().__init__()
        self.target_queue = target_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            self.target_queue.put_nowait((record.levelno, msg))
        except Exception:
            pass


class StreamToLogger:
    """Redirige stdout y stderr al sistema de logging sin fallar en modo noconsole."""
    def __init__(self, target_logger, level):
        self.target_logger = target_logger
        self.level = level
        self.buffer = ""

    def write(self, message):
        if not message:
            return
        self.buffer += message
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip()
            if line:
                self.target_logger.log(self.level, line)

    def flush(self):
        if self.buffer.strip():
            self.target_logger.log(self.level, self.buffer.strip())
            self.buffer = ""


# Configuración de Logging
logger = logging.getLogger("AsistenciaNURR")
logger.setLevel(logging.INFO)

log_formatter = logging.Formatter(
    fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Handler rotativo en archivo: 5 MB por archivo, hasta 5 archivos de respaldo
file_handler = RotatingFileHandler(
    LOG_FILE_PATH,
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8"
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Handler hacia la GUI
gui_handler = QueueLogHandler(log_queue)
gui_handler.setFormatter(log_formatter)
gui_handler.setLevel(logging.INFO)

# Configurar el logger raíz
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(gui_handler)

# Redirigir stdout y stderr para PyInstaller --noconsole
sys.stdout = StreamToLogger(logging.getLogger("STDOUT"), logging.INFO)
sys.stderr = StreamToLogger(logging.getLogger("STDERR"), logging.ERROR)


# ==============================================================================
# FUNCIONES AUXILIARES DE RED Y PRE-COMPROBACIÓN
# ==============================================================================
def get_local_ip() -> str:
    """Detecta la dirección IP de la interfaz de red local principal."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def ensure_prerequisites():
    """Verifica certificados SSL y base de datos antes de arrancar el servidor."""
    # 1. Certificados SSL
    cert_file = os.path.join(BASE_DIR, "certs", "cert.pem")
    key_file = os.path.join(BASE_DIR, "certs", "key.pem")
    if not (os.path.exists(cert_file) and os.path.exists(key_file)):
        logger.info("Certificados SSL no encontrados. Generando certificados locales...")
        try:
            from generate_certs import generate_self_signed_cert
            generate_self_signed_cert()
            logger.info("Certificados SSL generados exitosamente.")
        except Exception as e:
            logger.error(f"Error generando certificados SSL: {e}")

    # 2. Base de datos
    db_file = os.path.join(BASE_DIR, "asistencia_nurr.db")
    if not os.path.exists(db_file) or os.path.getsize(db_file) == 0:
        logger.info("Base de datos no inicializada. Creando esquema y sembrando datos maestros...")
        try:
            from reset_db import reset_database
            reset_database()
            logger.info("Base de datos inicializada y sembrada con éxito.")
        except Exception as e:
            logger.error(f"Error inicializando base de datos: {e}")


# ==============================================================================
# CONTROLADOR DEL SERVIDOR UVICORN
# ==============================================================================
class ServerController:
    """Gestiona el ciclo de vida del servidor web Uvicorn en un hilo en segundo plano."""
    def __init__(self, host="0.0.0.0", port=8000):
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.is_running = False
        self.start_time = None
        self._stopping = False

    def start(self, on_ready_callback=None):
        """Inicia el servidor Uvicorn en un hilo secundario."""
        if self.is_running:
            return

        ensure_prerequisites()

        import uvicorn
        from app.main import app

        ssl_cert = os.path.join(BASE_DIR, "certs", "cert.pem")
        ssl_key = os.path.join(BASE_DIR, "certs", "key.pem")

        use_ssl = os.path.exists(ssl_cert) and os.path.exists(ssl_key)

        config_kwargs = {
            "app": app,
            "host": self.host,
            "port": self.port,
            "log_config": None,  # Mantiene nuestros handlers de logging configurados
            "access_log": True,
            "log_level": "info",
        }

        if use_ssl:
            config_kwargs["ssl_certfile"] = ssl_cert
            config_kwargs["ssl_keyfile"] = ssl_key

        config = uvicorn.Config(**config_kwargs)
        self.server = uvicorn.Server(config)
        self._stopping = False

        def worker():
            protocol = "https" if use_ssl else "http"
            logger.info(f"Iniciando servidor {protocol.upper()} en {self.host}:{self.port}...")
            self.start_time = time.time()
            self.is_running = True

            if on_ready_callback:
                threading.Thread(target=self._wait_and_callback, args=(on_ready_callback, use_ssl), daemon=True).start()

            try:
                self.server.run()
            except Exception as e:
                logger.error(f"Excepción en la ejecución del servidor: {e}")
            finally:
                self.is_running = False
                self.start_time = None
                logger.info("El servidor web se ha detenido.")

        self.server_thread = threading.Thread(target=worker, daemon=True)
        self.server_thread.start()

    def _wait_and_callback(self, callback, use_ssl):
        """Espera a que el servidor responda a peticiones de salud y ejecuta el callback."""
        url = f"{'https' if use_ssl else 'http'}://127.0.0.1:{self.port}/api/health"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        # Esperar hasta 6 segundos a que el servidor esté activo
        for _ in range(30):
            if not self.is_running or self._stopping:
                return
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "AsistenciaNURR-Launcher"})
                with urllib.request.urlopen(req, context=ctx, timeout=1.0) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                time.sleep(0.2)
        else:
            time.sleep(1.0)

        if self.is_running and not self._stopping:
            callback()

    def stop(self):
        """Detiene el servidor de forma segura."""
        if not self.is_running or not self.server:
            return

        self._stopping = True
        logger.info("Deteniendo servidor web...")
        self.server.should_exit = True

        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=3.0)

        self.is_running = False
        self.start_time = None
        self._stopping = False


# ==============================================================================
# INTERFAZ GRÁFICA DE USUARIO (GUI MINIMALISTA)
# ==============================================================================
class LauncherApp:
    """Ventana de control simple y minimalista para Windows 10."""
    def __init__(self, root: tk.Tk):
        self.root = root
        self.controller = ServerController(host="0.0.0.0", port=8000)
        self.local_ip = get_local_ip()
        self.auto_scroll = tk.BooleanVar(value=True)

        self.setup_window()
        self.apply_styles()
        self.create_widgets()

        # Iniciar ciclo de actualización de logs y estado
        self.poll_log_queue()
        self.update_status_display()

        # Iniciar automáticamente el servidor y abrir navegador
        logger.info("Iniciando aplicación Asistencia-NURR...")
        self.root.after(300, self.start_server_and_open_browser)

    def setup_window(self):
        """Configuración básica de dimensiones, título e icono de la ventana."""
        self.root.title("Asistencia-NURR — Panel de Control del Servidor")
        self.root.geometry("720x580")
        self.root.minsize(680, 520)
        self.root.configure(bg="#f8fafc")

        # Configurar icono si existe
        icon_path = os.path.join(BASE_DIR, "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # Protocolo de cierre controlado de ventana
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_requested)

    def apply_styles(self):
        """Configura el estilo visual ttk para una estética moderna y limpia."""
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Colores de la paleta institucional moderna
        self.style.configure(".", font=("Segoe UI", 9))
        self.style.configure("TFrame", background="#f8fafc")

        # Botón primario de acción (Iniciar/Detener)
        self.style.configure(
            "Primary.TButton",
            font=("Segoe UI", 9, "bold"),
            background="#0284c7",
            foreground="#ffffff",
            borderwidth=0,
            padding=6
        )
        self.style.map("Primary.TButton", background=[("active", "#0369a1"), ("disabled", "#94a3b8")])

        # Botón secundario
        self.style.configure(
            "Secondary.TButton",
            font=("Segoe UI", 9),
            background="#e2e8f0",
            foreground="#0f172a",
            borderwidth=0,
            padding=6
        )
        self.style.map("Secondary.TButton", background=[("active", "#cbd5e1"), ("disabled", "#f1f5f9")])

        # Botón de peligro (Detener)
        self.style.configure(
            "Danger.TButton",
            font=("Segoe UI", 9, "bold"),
            background="#dc2626",
            foreground="#ffffff",
            borderwidth=0,
            padding=6
        )
        self.style.map("Danger.TButton", background=[("active", "#b91c1c"), ("disabled", "#94a3b8")])

        # Botón de éxito (Abrir en navegador)
        self.style.configure(
            "Success.TButton",
            font=("Segoe UI", 9, "bold"),
            background="#059669",
            foreground="#ffffff",
            borderwidth=0,
            padding=6
        )
        self.style.map("Success.TButton", background=[("active", "#047857"), ("disabled", "#94a3b8")])

    def create_widgets(self):
        """Construye los componentes de la interfaz gráfica."""
        # -------------------------------------------------------------
        # CABECERA INSTITUCIONAL
        # -------------------------------------------------------------
        header_frame = tk.Frame(self.root, bg="#0f172a", height=70)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)

        header_content = tk.Frame(header_frame, bg="#0f172a")
        header_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        title_label = tk.Label(
            header_content,
            text="SISTEMA DE ASISTENCIA AUTOMATIZADA",
            font=("Segoe UI", 12, "bold"),
            fg="#f8fafc",
            bg="#0f172a"
        )
        title_label.pack(anchor="w")

        subtitle_label = tk.Label(
            header_content,
            text="Unidad de Soporte Técnico — Universidad de Los Andes (ULA-NURR)",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#0f172a"
        )
        subtitle_label.pack(anchor="w")

        # -------------------------------------------------------------
        # CONTENEDOR PRINCIPAL
        # -------------------------------------------------------------
        main_container = tk.Frame(self.root, bg="#f8fafc")
        main_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        # -------------------------------------------------------------
        # TARJETA 1: ESTADO DEL SERVIDOR Y ENLACES
        # -------------------------------------------------------------
        status_card = tk.LabelFrame(
            main_container,
            text="  Estado del Sistema  ",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#334155",
            bd=1,
            relief=tk.SOLID
        )
        status_card.pack(fill=tk.X, pady=(0, 10), ipady=4)

        status_grid = tk.Frame(status_card, bg="#ffffff")
        status_grid.pack(fill=tk.X, padx=14, pady=8)

        # Fila 1: Indicador de estado y tiempo activo
        self.status_badge = tk.Label(
            status_grid,
            text="● DETENIDO",
            font=("Segoe UI", 10, "bold"),
            fg="#dc2626",
            bg="#fee2e2",
            padx=10,
            pady=3,
            relief=tk.FLAT
        )
        self.status_badge.grid(row=0, column=0, sticky="w", padx=(0, 15))

        self.uptime_label = tk.Label(
            status_grid,
            text="Tiempo activo: 00:00:00",
            font=("Segoe UI", 9),
            fg="#64748b",
            bg="#ffffff"
        )
        self.uptime_label.grid(row=0, column=1, sticky="w")

        # Separador sutil
        sep1 = tk.Frame(status_card, bg="#f1f5f9", height=1)
        sep1.pack(fill=tk.X, padx=14, pady=4)

        # Fila 2: Enlaces de Acceso
        links_frame = tk.Frame(status_card, bg="#ffffff")
        links_frame.pack(fill=tk.X, padx=14, pady=(2, 6))

        tk.Label(
            links_frame,
            text="Acceso Local:",
            font=("Segoe UI", 8, "bold"),
            fg="#475569",
            bg="#ffffff",
            width=14,
            anchor="w"
        ).grid(row=0, column=0, sticky="w")

        self.local_url_label = tk.Label(
            links_frame,
            text="https://localhost:8000",
            font=("Segoe UI", 8, "underline"),
            fg="#0284c7",
            bg="#ffffff",
            cursor="hand2"
        )
        self.local_url_label.grid(row=0, column=1, sticky="w")
        self.local_url_label.bind("<Button-1>", lambda e: self.open_browser())

        tk.Label(
            links_frame,
            text="Acceso LAN:",
            font=("Segoe UI", 8, "bold"),
            fg="#475569",
            bg="#ffffff",
            width=14,
            anchor="w"
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        lan_url = f"https://{self.local_ip}:8000"
        self.lan_url_label = tk.Label(
            links_frame,
            text=lan_url,
            font=("Segoe UI", 8),
            fg="#0f172a",
            bg="#ffffff"
        )
        self.lan_url_label.grid(row=1, column=1, sticky="w", pady=(3, 0))

        # -------------------------------------------------------------
        # TARJETA 2: BOTONES DE CONTROL DE EJECUCIÓN
        # -------------------------------------------------------------
        actions_frame = tk.Frame(main_container, bg="#f8fafc")
        actions_frame.pack(fill=tk.X, pady=(0, 10))

        self.btn_toggle_server = ttk.Button(
            actions_frame,
            text="⏹ Detener Servidor",
            style="Danger.TButton",
            command=self.toggle_server
        )
        self.btn_toggle_server.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_open_browser = ttk.Button(
            actions_frame,
            text="🌐 Abrir en Navegador",
            style="Success.TButton",
            command=self.open_browser
        )
        self.btn_open_browser.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_restart_server = ttk.Button(
            actions_frame,
            text="🔄 Reiniciar",
            style="Secondary.TButton",
            command=self.restart_server
        )
        self.btn_restart_server.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_open_logs = ttk.Button(
            actions_frame,
            text="📁 Ver Carpeta de Logs",
            style="Secondary.TButton",
            command=self.open_logs_dir
        )
        self.btn_open_logs.pack(side=tk.LEFT)

        # -------------------------------------------------------------
        # TARJETA 3: VISOR DE LOGS EN TIEMPO REAL
        # -------------------------------------------------------------
        logs_card = tk.LabelFrame(
            main_container,
            text="  Registro de Actividad (logs/asistencia.log)  ",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#334155",
            bd=1,
            relief=tk.SOLID
        )
        logs_card.pack(fill=tk.BOTH, expand=True)

        logs_header = tk.Frame(logs_card, bg="#ffffff")
        logs_header.pack(fill=tk.X, padx=10, pady=4)

        autoscroll_check = tk.Checkbutton(
            logs_header,
            text="Auto-desplazamiento",
            variable=self.auto_scroll,
            font=("Segoe UI", 8),
            bg="#ffffff",
            activebackground="#ffffff"
        )
        autoscroll_check.pack(side=tk.LEFT)

        btn_clear_view = tk.Button(
            logs_header,
            text="Limpiar pantalla",
            font=("Segoe UI", 8),
            bg="#f1f5f9",
            fg="#475569",
            relief=tk.FLAT,
            padx=8,
            pady=1,
            cursor="hand2",
            command=self.clear_logs_view
        )
        btn_clear_view.pack(side=tk.RIGHT)

        # Área de texto con scrollbar
        text_container = tk.Frame(logs_card, bg="#090d16")
        text_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.log_text = tk.Text(
            text_container,
            font=("Consolas", 8),
            bg="#090d16",
            fg="#cbd5e1",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            wrap=tk.WORD,
            state=tk.NORMAL
        )
        scrollbar = ttk.Scrollbar(text_container, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configurar colores de tags de log
        self.log_text.tag_config("INFO", foreground="#38bdf8")
        self.log_text.tag_config("WARNING", foreground="#facc15")
        self.log_text.tag_config("ERROR", foreground="#f87171")
        self.log_text.tag_config("TIMESTAMP", foreground="#64748b")

        # -------------------------------------------------------------
        # BARRA DE ESTADO INFERIOR / PIE
        # -------------------------------------------------------------
        footer_frame = tk.Frame(self.root, bg="#e2e8f0", height=28)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        footer_frame.pack_propagate(False)

        footer_label = tk.Label(
            footer_frame,
            text=f"Directorio de logs: {LOG_FILE_PATH}",
            font=("Segoe UI", 7),
            fg="#64748b",
            bg="#e2e8f0"
        )
        footer_label.pack(side=tk.LEFT, padx=12, pady=4)

        btn_exit = tk.Button(
            footer_frame,
            text="Salir",
            font=("Segoe UI", 8, "bold"),
            bg="#cbd5e1",
            fg="#0f172a",
            relief=tk.FLAT,
            padx=10,
            command=self.on_close_requested
        )
        btn_exit.pack(side=tk.RIGHT, padx=8, pady=2)

    # -----------------------------------------------------------------
    # ACCIONES Y EVENTOS
    # -----------------------------------------------------------------
    def start_server_and_open_browser(self):
        """Inicia el servidor y programa la apertura del navegador."""
        self.controller.start(on_ready_callback=self.on_server_ready)

    def on_server_ready(self):
        """Callback invocado en hilo cuando el servidor ya responde a peticiones."""
        logger.info("El servidor está listo. Abriendo navegador predeterminado...")
        self.open_browser()

    def open_browser(self):
        """Abre la URL de la aplicación en el navegador predeterminado."""
        url = "https://localhost:8000"
        try:
            webbrowser.open_new_tab(url)
        except Exception as e:
            logger.error(f"No se pudo abrir el navegador: {e}")

    def toggle_server(self):
        """Alterna entre iniciar o detener el servidor."""
        if self.controller.is_running:
            self.controller.stop()
        else:
            self.start_server_and_open_browser()

    def restart_server(self):
        """Reinicia el servidor web."""
        logger.info("Reiniciando servidor web...")
        self.controller.stop()
        self.root.after(500, self.start_server_and_open_browser)

    def open_logs_dir(self):
        """Abre la carpeta de logs en el Explorador de archivos de Windows."""
        try:
            if sys.platform == "win32":
                os.startfile(LOGS_DIR)
            else:
                webbrowser.open(f"file://{LOGS_DIR}")
        except Exception as e:
            logger.error(f"No se pudo abrir la carpeta de logs: {e}")

    def clear_logs_view(self):
        """Limpia el área de texto de logs en la interfaz gráfica."""
        self.log_text.delete("1.0", tk.END)

    def poll_log_queue(self):
        """Drena la cola de logs y los escribe en la interfaz gráfica de forma segura."""
        while not log_queue.empty():
            try:
                levelno, message = log_queue.get_nowait()
                tag = "INFO"
                if levelno >= logging.ERROR:
                    tag = "ERROR"
                elif levelno >= logging.WARNING:
                    tag = "WARNING"

                self.log_text.insert(tk.END, message + "\n", tag)
                if self.auto_scroll.get():
                    self.log_text.see(tk.END)
            except queue.Empty:
                break
        self.root.after(100, self.poll_log_queue)

    def update_status_display(self):
        """Actualiza el indicador visual de estado y el contador de tiempo activo."""
        if self.controller.is_running:
            self.status_badge.configure(
                text="● EN LÍNEA",
                fg="#059669",
                bg="#d1fae5"
            )
            self.btn_toggle_server.configure(
                text="⏹ Detener Servidor",
                style="Danger.TButton"
            )

            if self.controller.start_time:
                elapsed = int(time.time() - self.controller.start_time)
                hrs = elapsed // 3600
                mins = (elapsed % 3600) // 60
                secs = elapsed % 60
                self.uptime_label.configure(text=f"Tiempo activo: {hrs:02d}:{mins:02d}:{secs:02d}")
        else:
            self.status_badge.configure(
                text="● DETENIDO",
                fg="#dc2626",
                bg="#fee2e2"
            )
            self.btn_toggle_server.configure(
                text="▶ Iniciar Servidor",
                style="Primary.TButton"
            )
            self.uptime_label.configure(text="Tiempo activo: 00:00:00")

        self.root.after(1000, self.update_status_display)

    def on_close_requested(self):
        """Maneja el evento de cierre de ventana garantizando detención limpia."""
        if self.controller.is_running:
            should_close = messagebox.askyesno(
                "Confirmar salida",
                "El servidor de Asistencia-NURR está activo.\n\n"
                "¿Desea detener el servidor y cerrar la aplicación?",
                parent=self.root
            )
            if not should_close:
                return

            logger.info("Cerrando aplicación y deteniendo servicios...")
            self.controller.stop()

        self.root.destroy()


# ==============================================================================
# PUNTO DE ENTRADA PRINCIPAL
# ==============================================================================
def main():
    enable_high_dpi_windows()
    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
