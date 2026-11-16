# Asistencia-NURR

Aplicación web para el control y gestión de asistencia automatizada de la Unidad de Soporte Técnico de la Universidad de los Andes (ULA-NURR). 

Registro de asistencia, autenticación digitalizada, gestión de horarios y generación de reportes.

---

## 🚀 Ejecución en Windows 10 (Modo Escritorio)

La aplicación incluye un ejecutable independiente de escritorio para Windows 10 (`AsistenciaNURR.exe`) con las siguientes características:
- **Sin consola de comandos**: La consola negra de terminal permanece completamente oculta (`--noconsole`).
- **Interfaz gráfica de control minimalista**: Despliega un panel visual intuitivo y moderno para controlar el ciclo de vida de la aplicación.
- **Arranque automático y apertura en navegador**: Al abrir el ejecutable, inicia el servidor en segundo plano e inmediatamente abre la aplicación en la pestaña de su navegador web predeterminado (`https://localhost:8000`).
- **Registro persistente de logs**: Mantiene un registro rotativo y unificado de todos los eventos del servidor y la interfaz en el directorio dedicado [`logs/asistencia.log`](file:///C:/Users/LENOVO/.gemini/antigravity/worktrees/asistencia-nurr/desktop_launcher_gui_windows/logs/asistencia.log).

### 🖥️ Cómo usar el Ejecutable
1. Haga doble clic sobre **`AsistenciaNURR.exe`** en la raíz del repositorio.
2. Se iniciará el panel de control gráfico y se abrirá automáticamente la aplicación en su navegador.
3. Desde la ventana de control puede:
   - **Iniciar / Detener Servidor**: Controlar la ejecución del servicio web en cualquier momento.
   - **Abrir en Navegador**: Reabrir la pestaña web si la cerró accidentalmente.
   - **Reiniciar**: Reiniciar los servicios de red con un solo clic.
   - **Ver Carpeta de Logs**: Abrir el explorador de Windows directamente en la carpeta `logs/`.
   - **Visor en tiempo real**: Monitorear peticiones HTTP y eventos de la aplicación en vivo.

### 🛠️ Recompilación del Ejecutable
Si realiza cambios en el código fuente y desea generar una nueva versión del binario:
- Ejecute el script `build_exe.bat` o ejecute en PowerShell / CMD:
  ```powershell
  python build_exe.py
  ```
