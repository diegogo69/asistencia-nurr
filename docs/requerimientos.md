# Requerimientos Funcionales (RF)

Describen los servicios específicos que el sistema debe proveer para cumplir con los objetivos del negocio.

## Módulo 1: Configuración Global y Reglas de Negocio

- **RF-1.1 Gestión Organizacional:** El sistema debe permitir al administrador gestionar (crear, leer, actualizar, eliminar) las unidades organizacionales institucionales (dirección, coordinación, sección, oficina).
- **RF-1.2 Gestión de Horarios:** El sistema debe permitir la creación de plantillas de horarios, soportando tanto el bloque obligatorio fijo de la institución (ej. lunes a miércoles de 8:00 AM a 1:00 PM) para el personal contratado, como los bloques de horarios flexibles asignados a los pasantes.
- **RF-1.3 Parametrización de Redes Autorizadas:** El sistema debe permitir al administrador configurar y gestionar un listado de direcciones IP o rangos de red que estarán habilitados para procesar marcaciones de asistencia.
- **RF-1.4 Autenticación de Gestión:** El sistema debe proveer una interfaz de inicio de sesión segura (usuario y contraseña) dedicada a los roles de administrador y de coordinador.

## Módulo 2: Gestión de Usuarios (Actores)

- **RF-2.1 Gestión de Usuarios:** El sistema debe permitir registrar los datos personales de los usuarios y asociarlos a su rol específico (Coordinador, Técnico Contratado, Programador Contratado, Pasante Técnico, Pasante Programador), asignándoles un departamento y horario.
- **RF-2.2 Validación de registro único:** El sistema debe impedir obligatoriamente la duplicidad de usuarios, verificando que el documento de identificación sea único en la base de datos.
- **RF-2.3 Registro Biométrico Facial:** El sistema debe permitir la captura, procesamiento y almacenamiento único de los vectores biométricos faciales del usuario mediante una cámara web.
- **RF-2.4 Generación de Código QR:** El sistema debe generar automáticamente un código QR de identificación único para cada usuario al momento de registrarse, el cual funcionará como credencial alternativa.

## Módulo 3: Autenticación y Registro de Asistencia

- **RF-3.1 Validación de IP:** El sistema debe comprobar automáticamente que la dirección IP del dispositivo cliente coincida con el rango de red autorizado antes de permitir el registro de asistencia.
- **RF-3.2 Autenticación de Asistencia:** El sistema debe requerir que el usuario ingrese su documento de identificación y, posteriormente, valide su identidad en tiempo real mediante reconocimiento facial o escaneo de su código QR único.
- **RF-3.3 Cálculo de Asistencia:** El sistema debe contrastar la hora exacta del registro con el horario asignado al usuario para determinar automáticamente el estado (entrada/salida, puntualidad, retraso o llegada anticipada).
- **RF-3.4 Gestión de Asistencia Incompleta:** El sistema debe gestionar los registros incompletos (sin salida) de asistencia, notificar la anomalía al usuario y al coordinador encargado, para su respectiva revisión.
- **RF-3.5 Panel de Asistencias Incompletas:** El sistema debe proveer al rol "Coordinador" una interfaz dedicada a los registros de asistencia en estado pendiente de revisión, para evaluar y aplicar una resolución definitiva.

## Módulo 4: Auditoría y Reportes

- **RF-4.1 Historial Centralizado:** El sistema debe almacenar de forma persistente todos los eventos y permitir consultas históricas dinámicas utilizando filtros por rango de fechas, usuario, departamento y estado de cumplimiento.
- **RF-4.2 Generación de Reportes:** El sistema debe generar reportes consolidados y estadísticos, permitiendo su exportación en formatos independientes (PDF y CSV/Excel) para facilitar tareas como el cotejo de los Informes de Control de Visitas de los pasantes.

# 2. Requerimientos No Funcionales (RNF)

Definen los atributos de calidad, restricciones tecnológicas y estándares de arquitectura que determinarán la robustez de la plataforma.

## Arquitectura y Entorno

- **RNF-1.1 Despliegue en Red Local (LAN):** El software debe operar bajo una arquitectura cliente-servidor con una API centralizada, desplegada en el entorno de red local de la unidad, con un servidor central de base de datos y puntos de interconexión inalámbrica.
- **RNF-1.2 Independencia Lógica:** El código fuente no debe contener parámetros fijos; toda la lógica de negocio debe depender exclusivamente de las variables almacenadas en la base de datos, evitando el hardcoding.

## Seguridad e Integridad

- **RNF-2.1 Inmutabilidad de Datos:** El sistema debe aplicar controles de acceso estrictos a nivel de base de datos para impedir la alteración o modificación manual directa de los registros históricos consolidados.

## Usabilidad y Rendimiento

- **RNF-3.1 Diseño Responsive:** La interfaz de usuario debe estar diseñada para adaptarse correctamente tanto a entornos web de escritorio como a dispositivos móviles.
- **RNF-3.2 Interfaz Intuitiva y Retroalimentación:** La interfaz gráfica debe ser fácil de usar y comunicar de forma clara mensajes de éxito, o bien, emitir alertas explícitas ante fallos de red o errores biométricos.
- **RNF-3.3 Rendimiento en Red Local:** El sistema debe procesar las marcaciones de asistencia de forma rápida, aprovechando la baja latencia de la red local (LAN).
- **RNF-3.4 Manejo de Fallos de Hardware:** Ante la indisponibilidad del reconocimiento facial, el sistema debe permitir registrar la asistencia utilizando únicamente el documento de identificación y el Código QR como mecanismo de contingencia para garantizar la operatividad de la unidad.

## Escalabilidad y Adaptabilidad

- **RNF-4.1 Diseño Paramétrico:** La arquitectura del sistema debe ser lo suficientemente flexible y modular para permitir que las dependencias, roles y flujos de trabajo de cualquier otra área de la institución (ULA-NURR) se configuren dinámicamente desde la base de datos, evitando dependencias específicas de la unidad de soporte técnico.
- **RNF-4.2 Portabilidad:** El software debe ser diseñado de manera genérica para facilitar su despliegue y funcionamiento en otras instituciones externas.
