# Requerimientos del Sistema

## Requerimientos Funcionales
Describen las acciones específicas, servicios o funciones que el software debe ejecutar cuando el usuario interactúa con él. Son las características con las que el usuario interactúa directamente.

### 1. Módulo de Configuración Global 
- **Gestión de estructura organizacional:** Permitir al administrador la gestión (crear, leer, actualizar, eliminar) de unidades organizacionales (dirección, coordinación, sección o área, unidad u oficina) dentro de la institución.
- **Gestión Flexible de Horarios y Turnos:** Permitir la creación de plantillas de horarios de trabajo, definiendo hora de entrada, hora de salida, días laborales y minutos de tolerancia por retraso.
- **Parametrización de Direcciones IP:** Permitir al administrador gestionar un listado de direcciones IP o rangos de red autorizados, que el software utilizará para validar la marcación de asistencia.

### 2. Módulo de Gestión de Usuarios
- **Gestión de usuarios:** Permitir la gestión (crear, leer, actualizar, eliminar) de usuarios registrar sus datos personales, documento de identificación, rol en el sistema y su respectiva asociación a un departamento y horario.
- **Validación de No Duplicidad:** Impedir el registro de usuarios duplicados, validando de forma obligatoria que el número de documento de identificación sea único en la base de datos.
- **Registro Biométrico Facial:** Permitir, a través de una cámara web, la captura de información biométrica de reconocimiento facial del usuario, para procesar y almacenar de forma única esta información en la base de datos.
- **Asignación de Código QR Único:** Generar un código QR único de identificación para cada usuario al momento de su registro, sirviendo como credencial alternativa de identificación.

### 3. Módulo de Autenticación y Registro de Asistencia
- **Validación del Entorno de Red:** Comprobar de forma automática que la dirección IP del cliente coincida con las IPs autorizadas antes de procesar cualquier marcación de asistencia.
- **Marcación Híbrida - Registro de asistencia:** Permitir al usuario marcar su asistencia a través de un sistema híbrido, primero ingresando su número de documento de identificación, para luego hacer una validación de información biométrica o de código QR.
- **Marcación Híbrida - Reconocimiento Facial:** Validar la identidad del usuario en tiempo real mediante la cámara, comparando sus rasgos con los vectores biométricos almacenados para registrar su asistencia.
- **Marcación Híbrida - Código QR:** Permitir al usuario escanear su código QR único en el lector asignado como método de autenticación para registrar su asistencia.
- **Cálculo Automático de Cumplimiento:** Comparar la fecha y hora exacta de la petición de marcación de asistencia con el horario asignado al usuario, para registrar el estado de la asistencia (salida/llegada, retraso/puntual/anticipada).

### 4. Módulo de Reportes e Historial
- **Consulta de Registro Histórico Centralizado:** Almacenar de forma persistente todos los eventos de asistencia y permitir la consulta del historial mediante filtros dinámicos (rango de fechas, departamento, usuario específico, estado de cumplimiento).
- **Generación y Exportación de Reportes:** El sistema debe generar reportes estadísticos y consolidados de asistencia, permitiendo su descarga en formatos estándar e independientes de la plataforma (PDF y CSV/Excel).

---

## Requerimientos No Funcionales (RNF)
No describen una característica que el usuario "usa" directamente, sino las propiedades, cualidades, restricciones o estándares de calidad que el software debe cumplir (rendimiento, seguridad, escalabilidad, usabilidad). En pocas palabras: Son los que determinan la experiencia de uso, la robustez y la calidad técnica del sistema.

### 1. Arquitectura y Escalabilidad
- **Despliegue Local:** El sistema debe estar diseñado bajo una arquitectura cliente-servidor, de API centralizada, capaz de ser desplegada en un entorno de red local (LAN).
- **Independencia de código:** El código fuente de la aplicación no debe contener valores fijos (*hardcoded*). Toda la lógica operativa debe depender exclusivamente de las variables de configuración de la base de datos.

### 2. Seguridad, Confidencialidad e Integridad
- **Inmutabilidad del Historial:** El sistema debe garantizar la integridad de los datos históricos de asistencia, impidiendo su modificación manual directa mediante controles de acceso estrictos a nivel de base de datos.

### 3. Rendimiento y Usabilidad
- **Tiempo de Respuesta en Red Local:** El tiempo total de procesamiento para una marcación de asistencia debe ser rápido, aprovechando la latencia de la red local.

- **Interfaz de Usuario Adaptable:** La interfaz gráfica debe ser intuitiva y fácil de usar, permitiendo mostrar de manera clara mensajes de éxito o alertas/errores ante cualquier fallo de validación (red o biométrico).
