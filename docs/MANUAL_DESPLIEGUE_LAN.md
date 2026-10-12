# Manual de Despliegue en Red Local (LAN) y Operación
## Sistema de Asistencia Automatizada y Auditoría ULA-NURR

Este manual describe los pasos necesarios para desplegar, ejecutar y operar el sistema en un entorno de red local sobre **Windows 10 o Windows 11**, garantizando acceso seguro HTTPS para cámaras web y ejecución interactiva mediante consola tradicional.

---

## 1. Requisitos Previos en el Servidor (Windows 10 / 11)

1. **Python 3.11, 3.12 o 3.13** instalado y agregado al `PATH`.
2. **Entorno Virtual** configurado en la carpeta raíz del proyecto (`venv/`).
3. **Dependencias instaladas:**
   ```powershell
   .\venv\Scripts\pip install -r requirements.txt
   ```
4. **Base de Datos:**
   - **Desarrollo / Pruebas:** SQLite (`asistencia_nurr.db`) configurada por defecto.
   - **Producción LAN:** MySQL Server 8.0 (opcional, configurable en `.env`).

---

## 2. Configuración de IP Fija y Firewall de Windows

Para que los equipos clientes (laptops, PCs de laboratorios, tablets) puedan conectarse de manera permanente al servidor, se recomienda fijar la dirección IP local del equipo servidor:

### 2.1. Asignar IP Fija en Windows
1. Abrir **Configuración** $\rightarrow$ **Red e Internet** $\rightarrow$ **Ethernet** o **Wi-Fi**.
2. En la configuración de IP, seleccionar **Editar**.
3. Cambiar de *Automático (DHCP)* a *Manual (IPv4)*.
4. Introducir los valores asignados por la red institucional (Ejemplo típico):
   - **Dirección IP:** `192.168.0.50` (o la IP asignada en su subred)
   - **Máscara de subred:** `255.255.255.0`
   - **Puerta de enlace predeterminada:** `192.168.0.1`
   - **DNS preferido:** `8.8.8.8`

### 2.2. Abrir Puerto 8000 en el Firewall de Windows
Para permitir que otros computadores de la red local accedan al servidor:

Ejecutar PowerShell como **Administrador** y correr el siguiente comando:
```powershell
New-NetFirewallRule -DisplayName "Asistencia NURR HTTPS" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```
*(También puede crearse manualmente desde el "Firewall de Windows Defender con Seguridad Avanzada" $\rightarrow$ Reglas de entrada $\rightarrow$ Nueva regla $\rightarrow$ Puerto $\rightarrow$ TCP 8000 $\rightarrow$ Permitir la conexión).*

---

## 3. Generación de Certificados SSL (HTTPS Local con SAN)

Los navegadores modernos (*Chrome, Edge, Firefox*) **bloquean el acceso a la cámara web (`getUserMedia`)** si la página no se sirve bajo **HTTPS**, incluso en redes locales.

El proyecto incluye el generador automático [`generate_certs.py`](file:///C:/Users/LENOVO/.gemini/antigravity/worktrees/asistencia-nurr/create_development_plan/generate_certs.py). Para regenerar los certificados si cambia la IP del servidor:

```powershell
.\venv\Scripts\python.exe generate_certs.py
```
Este script genera `certs/cert.pem` y `certs/key.pem` con extensiones *Subject Alternative Name (SAN)* para:
- `localhost`
- `127.0.0.1`
- `192.168.0.0/16` y la IP local actual de su máquina.

---

## 4. Confianza del Certificado en Clientes LAN (Acceso sin Advertencias)

Al acceder por primera vez desde otro computador de la red local a `https://192.168.0.50:8000`:
1. El navegador mostrará una advertencia de seguridad inicial (*"La conexión no es privada"* o *"Certificado autofirmado"*).
2. Hacer clic en **Configuración Avanzada** $\rightarrow$ **Continuar a 192.168.0.50 (no seguro)**.
3. El navegador guardará la excepción y habilitará inmediatamente el acceso a la **Cámara Web** y a todas las funciones del Kiosco.
4. Para eliminar la advertencia de forma permanente en los equipos del laboratorio:
   - Copiar el archivo `certs/cert.pem` a la máquina cliente.
   - Cambiar la extensión a `cert.crt` y hacer doble clic $\rightarrow$ **Instalar Certificado** $\rightarrow$ **Equipo local** $\rightarrow$ Colocar en **"Entidades de certificación raíz de confianza"**.

---

## 5. Puesta en Marcha Tradicional (Script Batch)

Para iniciar el servidor con un solo clic y ver los logs en vivo:
1. Hacer doble clic sobre [`start_server.bat`](file:///C:/Users/LENOVO/.gemini/antigravity/worktrees/asistencia-nurr/create_development_plan/start_server.bat).
2. Se abrirá una ventana de consola interactiva con el servidor Uvicorn corriendo bajo HTTPS:
   ```text
   INFO:     Started server process
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   INFO:     Uvicorn running on https://0.0.0.0:8000 (Press CTRL+C to quit)
   ```
3. Puede crear un acceso directo a `start_server.bat` y colocarlo directamente en el **Escritorio** de Windows.

---

## 6. URLs de Acceso al Sistema

Una vez iniciado el servidor:

| Propósito | URL Local en Servidor | URL desde Clientes LAN |
| :--- | :--- | :--- |
| **Panel Administrativo** | `https://localhost:8000/` | `https://[IP_SERVIDOR]:8000/` |
| **Inicio de Sesión** | `https://localhost:8000/static/login.html` | `https://[IP_SERVIDOR]:8000/static/login.html` |
| **Punto de Marcación (Kiosco)** | `https://localhost:8000/static/marcacion.html` | `https://[IP_SERVIDOR]:8000/static/marcacion.html` |
| **Documentación Swagger API** | `https://localhost:8000/docs` | `https://[IP_SERVIDOR]:8000/docs` |
| **Verificación de Salud** | `https://localhost:8000/api/health` | `https://[IP_SERVIDOR]:8000/api/health` |

---

## 7. Credenciales Iniciales de Administrador

- **Documento de Identidad:** `V-00000000`
- **Contraseña:** `admin1234`
- **Rol:** Administrador del Sistema

*(Se recomienda actualizar la contraseña o crear los usuarios institucionales definitivos una vez iniciada la sesión).*

---

## 8. Mantenimiento y Respaldos

### Respaldo de Base de Datos SQLite (Predeterminada)
Copiar el archivo `asistencia_nurr.db` a una unidad de almacenamiento seguro o disco externo periódicamente:
```powershell
Copy-Item asistencia_nurr.db "D:\Respaldos\asistencia_backup_$(Get-Date -Format 'yyyyMMdd').db"
```

### Respaldo si utiliza MySQL
```powershell
mysqldump -u root -p asistencia_nurr > "D:\Respaldos\asistencia_nurr_$(Get-Date -Format 'yyyyMMdd').sql"
```

### Reinicializar Datos de Prueba / Semilla
Si se desea restablecer los datos iniciales y usuarios de prueba:
```powershell
.\venv\Scripts\python.exe seed.py
```
