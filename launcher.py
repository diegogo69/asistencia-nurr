"""Lanzador de servidor Asistencia-NURR con Interfaz de Administrador para Windows 10.

Inicia el servidor HTTPS en segundo plano (sin consola de comandos visible),
abre el navegador en la URL de localhost, registra logs en el directorio logs/
y provee una interfaz para que el administrador pueda detener la aplicación.
"""

import os
import sys
import time
import signal
import socket
import ssl
import urllib.request
import webbrowser
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox


# 1. Definir rutas base
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

os.chdir(BASE_DIR)
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LAUNCHER_LOG = LOGS_DIR / "launcher.log"
SERVER_LOG = LOGS_DIR / "servidor.log"


def log(msg: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [LAUNCHER] {msg}"
    try:
        with open(LAUNCHER_LOG, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass


def find_python_executable() -> str:
    """Localiza el ejecutable de Python apropiado (preferentemente en venv)."""
    venv_python = BASE_DIR / "venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)

    # Si estamos en un virtualenv activo
    if sys.prefix != sys.base_prefix:
        cand = Path(sys.prefix) / "Scripts" / "python.exe"
        if cand.exists():
            return str(cand)

    return sys.executable


def ensure_ssl_certs(python_exe: str):
    """Verifica y genera certificados SSL si no existen."""
    cert_file = BASE_DIR / "certs" / "cert.pem"
    key_file = BASE_DIR / "certs" / "key.pem"
    if not cert_file.exists() or not key_file.exists():
        log("Certificados SSL no encontrados. Generando certificados locales...")
        try:
            from generate_certs import generate_self_signed_cert
            generate_self_signed_cert(cert_dir=str(BASE_DIR / "certs"))
            log("Certificados generados con éxito.")
        except Exception as e:
            log(f"Generando certificados mediante proceso externo: {e}")
            subprocess.run(
                [python_exe, "generate_certs.py"],
                cwd=str(BASE_DIR),
                creationflags=0x08000000 if os.name == "nt" else 0,
                check=False
            )


def ensure_database(python_exe: str):
    """Verifica y prepara la base de datos si no existe."""
    db_file = BASE_DIR / "asistencia_nurr.db"
    needs_init = not db_file.exists() or db_file.stat().st_size == 0
    if needs_init:
        log("Base de datos no detectada. Inicializando con migraciones y sembrado...")
        try:
            from reset_db import reset_database
            reset_database()
            log("Base de datos inicializada satisfactoriamente.")
        except Exception as e:
            log(f"Inicializando base de datos mediante proceso externo: {e}")
            subprocess.run(
                [python_exe, "reset_db.py"],
                cwd=str(BASE_DIR),
                creationflags=0x08000000 if os.name == "nt" else 0,
                check=False
            )


def is_server_online(url: str = "https://127.0.0.1:8000/api/health") -> bool:
    """Comprueba si el servidor web responde al health check."""
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AsistenciaNURR-Launcher"})
        with urllib.request.urlopen(req, timeout=1.5, context=ctx) as response:
            return response.status == 200
    except Exception:
        return False


class ServerManagerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Asistencia-NURR - Servidor (Perfil Administrador)")
        self.root.geometry("520x360")
        self.root.resizable(False, False)

        # Centrar en pantalla
        self.center_window(520, 360)

        # Estilo visual Segoe UI nativo de Windows 10
        self.root.configure(bg="#f8fafc")
        self.server_process = None
        self.server_log_handle = None
        self.python_exe = find_python_executable()
        self.target_url = "https://localhost:8000"

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_request_close)

        # Iniciar servidor en segundo plano
        self.root.after(100, self.start_server_workflow)

    def center_window(self, width, height):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - width) // 2
        y = (sh - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def setup_ui(self):
        # Encabezado institucional
        header_frame = tk.Frame(self.root, bg="#0056b3", height=70)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)

        title_lbl = tk.Label(
            header_frame,
            text="SISTEMA DE ASISTENCIA AUTOMATIZADA - ULA-NURR",
            font=("Segoe UI", 12, "bold"),
            bg="#0056b3",
            fg="white"
        )
        title_lbl.pack(pady=(12, 2))

        subtitle_lbl = tk.Label(
            header_frame,
            text="Unidad de Soporte Técnico | Control de Ejecución (Sin Consola)",
            font=("Segoe UI", 9),
            bg="#0056b3",
            fg="#e0e7ff"
        )
        subtitle_lbl.pack()

        # Panel de Estado central
        content_frame = tk.Frame(self.root, bg="#f8fafc", padx=24, pady=18)
        content_frame.pack(fill=tk.BOTH, expand=True)

        status_box = tk.Frame(content_frame, bg="#ffffff", bd=1, relief=tk.SOLID, padx=16, pady=14)
        status_box.pack(fill=tk.X, pady=(0, 15))

        self.status_indicator = tk.Label(
            status_box,
            text="● Iniciando servidor...",
            font=("Segoe UI", 11, "bold"),
            bg="#ffffff",
            fg="#d97706"
        )
        self.status_indicator.pack(anchor=tk.W)

        self.url_lbl = tk.Label(
            status_box,
            text=f"Dirección local: {self.target_url}",
            font=("Segoe UI", 9.5),
            bg="#ffffff",
            fg="#475569"
        )
        self.url_lbl.pack(anchor=tk.W, pady=(4, 0))

        self.logs_lbl = tk.Label(
            status_box,
            text=f"Directorio de logs: {LOGS_DIR.resolve()}",
            font=("Segoe UI", 8.5),
            bg="#ffffff",
            fg="#64748b"
        )
        self.logs_lbl.pack(anchor=tk.W, pady=(4, 0))

        # Mensaje informativo
        info_lbl = tk.Label(
            content_frame,
            text="La consola de comandos está oculta. Utilice los botones inferiores para abrir la web,\ninspeccionar los logs o apagar el servidor de forma segura.",
            font=("Segoe UI", 8.5),
            bg="#f8fafc",
            fg="#64748b",
            justify=tk.LEFT
        )
        info_lbl.pack(anchor=tk.W, pady=(0, 16))

        # Botonera de acciones
        btn_frame = tk.Frame(content_frame, bg="#f8fafc")
        btn_frame.pack(fill=tk.X)

        self.btn_open_browser = tk.Button(
            btn_frame,
            text="🌐 Abrir Navegador",
            font=("Segoe UI", 9, "bold"),
            bg="#0056b3",
            fg="white",
            activebackground="#004494",
            activeforeground="white",
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.open_browser
        )
        self.btn_open_browser.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_open_logs = tk.Button(
            btn_frame,
            text="📂 Ver Logs",
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg="#1e293b",
            activebackground="#cbd5e1",
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.open_logs_folder
        )
        self.btn_open_logs.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_stop = tk.Button(
            btn_frame,
            text="🛑 Detener Servidor",
            font=("Segoe UI", 9, "bold"),
            bg="#dc2626",
            fg="white",
            activebackground="#b91c1c",
            activeforeground="white",
            relief=tk.FLAT,
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.on_request_close
        )
        self.btn_stop.pack(side=tk.RIGHT)

    def open_browser(self):
        log(f"Abriendo navegador en {self.target_url}")
        webbrowser.open(self.target_url)

    def open_logs_folder(self):
        try:
            if os.name == "nt":
                os.startfile(str(LOGS_DIR))
            else:
                subprocess.Popen(["xdg-open", str(LOGS_DIR)])
        except Exception as e:
            log(f"Error al abrir carpeta de logs: {e}")

    def start_server_workflow(self):
        log("Iniciando flujo de preparación del servidor...")
        # 1. Asegurar certificados y base de datos
        try:
            ensure_ssl_certs(self.python_exe)
            ensure_database(self.python_exe)
        except Exception as e:
            log(f"Advertencia en preparación inicial: {e}")

        # 2. Si ya está activo (por ejemplo otra instancia previa)
        if is_server_online():
            log("El servidor ya se encuentra respondiendo en el puerto 8000.")
            self.on_server_ready()
            return

        # 3. Lanzar proceso Uvicorn sin ventana de consola
        log(f"Lanzando servidor Uvicorn con {self.python_exe}...")
        self.server_log_handle = open(SERVER_LOG, "a", encoding="utf-8")

        cmd = [
            self.python_exe,
            "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--ssl-keyfile", "certs/key.pem",
            "--ssl-certfile", "certs/cert.pem"
        ]

        creationflags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW en Windows
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            self.server_process = subprocess.Popen(
                cmd,
                cwd=str(BASE_DIR),
                env=env,
                stdout=self.server_log_handle,
                stderr=subprocess.STDOUT,
                creationflags=creationflags
            )
            log(f"Proceso de servidor iniciado con PID: {self.server_process.pid}")
        except Exception as e:
            log(f"Error crítico al iniciar Uvicorn: {e}")
            messagebox.showerror("Error", f"No se pudo iniciar el servidor web:\n{e}")
            self.root.destroy()
            return

        # 4. Esperar a que el servidor esté listo
        self.wait_for_server(attempts=0, max_attempts=40)

    def wait_for_server(self, attempts=0, max_attempts=40):
        if is_server_online():
            log("Servidor verificado en línea mediante health-check.")
            self.on_server_ready()
            # Abrir navegador automáticamente al arrancar
            self.open_browser()
            # Comenzar monitoreo continuo
            self.root.after(1500, self.monitor_server_status)
        else:
            # Comprobar si el proceso murió prematuramente
            if self.server_process and self.server_process.poll() is not None:
                log(f"El proceso del servidor terminó inesperadamente con código {self.server_process.poll()}.")
                self.status_indicator.config(text="● Error al iniciar el servidor", fg="#dc2626")
                messagebox.showerror(
                    "Error de Ejecución",
                    f"El servidor se cerró de forma prematura.\nRevise los detalles en el archivo de logs:\n{SERVER_LOG}"
                )
                return

            if attempts < max_attempts:
                self.root.after(500, lambda: self.wait_for_server(attempts + 1, max_attempts))
            else:
                log("Tiempo de espera agotado esperando respuesta del servidor.")
                self.status_indicator.config(text="● Tiempo de espera agotado", fg="#dc2626")
                messagebox.showwarning(
                    "Advertencia",
                    "El servidor tardó más de lo esperado en responder.\nPuede consultar el log en logs/servidor.log"
                )

    def on_server_ready(self):
        self.status_indicator.config(
            text="● Servidor Activo (HTTPS En Línea)",
            fg="#16a34a"
        )
        self.btn_open_browser.config(state=tk.NORMAL)

    def monitor_server_status(self):
        """Monitorea periódicamente si el servidor sigue activo o fue detenido externamente (ej: desde la web)."""
        if self.server_process:
            poll_res = self.server_process.poll()
            if poll_res is not None:
                log(f"Servidor finalizado externamente (código de salida: {poll_res}).")
                self.status_indicator.config(text="● Servidor detenido desde perfil administrador", fg="#64748b")
                self.btn_stop.config(state=tk.DISABLED)
                self.btn_open_browser.config(state=tk.DISABLED)
                self.root.after(1500, self.cleanup_and_exit)
                return

        self.root.after(1500, self.monitor_server_status)

    def on_request_close(self):
        """Maneja la solicitud de apagado del servidor con confirmación."""
        confirm = messagebox.askyesno(
            "Detener Servidor",
            "¿Está seguro de que desea detener la ejecución del servidor Asistencia-NURR?\n\n"
            "Todos los registros se guardarán en la carpeta 'logs' y el servicio dejará de estar disponible.",
            icon="warning"
        )
        if confirm:
            self.stop_server()

    def stop_server(self):
        log("Detención solicitada por el usuario en la interfaz del Administrador.")
        self.status_indicator.config(text="● Deteniendo servidor...", fg="#d97706")
        self.root.update()

        if self.server_process and self.server_process.poll() is None:
            pid = self.server_process.pid
            log(f"Terminando proceso del servidor PID {pid}...")
            try:
                if os.name == "nt":
                    # Usar taskkill en árbol (/T) para cerrar uvicorn y sus subprocesos de manera forzada y limpia
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        creationflags=0x08000000,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                else:
                    self.server_process.terminate()
                    self.server_process.wait(timeout=3)
            except Exception as e:
                log(f"Error al terminar proceso: {e}")
                try:
                    self.server_process.kill()
                except Exception:
                    pass

        log("Servidor detenido completamente.")
        self.cleanup_and_exit()

    def cleanup_and_exit(self):
        if self.server_log_handle and not self.server_log_handle.closed:
            try:
                self.server_log_handle.flush()
                self.server_log_handle.close()
            except Exception:
                pass
        self.root.destroy()


def main():
    log("==================================================")
    log("Iniciando Lanzador Asistencia-NURR (Modo Administrador)")
    log(f"Directorio de trabajo: {BASE_DIR}")
    log(f"Directorio de logs: {LOGS_DIR}")
    log("==================================================")

    root = tk.Tk()
    app = ServerManagerGUI(root)
    root.mainloop()
    log("Lanzador finalizado.")


if __name__ == "__main__":
    main()
