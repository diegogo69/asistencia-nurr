## Tabla departamentos:

Tabla departamentos: En esta tabla irán todos los datos que almacenan la estructura organizativa de la institución.


| Campo | Tipo | Longitud | Requerimiento | Descripción |
| --- | --- | --- | --- | --- |
| id | int | 11 | si | Identificador único del departamento |
| nombre | varchar | 100 | si | Nombre descriptivo del departamento (ej: "Soporte Técnico") |
| tipo | enum |  | si | Clasificación jerárquica del departamento |


## Tabla roles:

Tabla roles: En esta tabla irán todos los datos que definen los roles asignados a los usuarios del sistema y sus privilegios.


| Campo | Tipo | Longitud | Requerimiento | Descripción |
| --- | --- | --- | --- | --- |
| id | int | 11 | si | Identificador único del rol |
| nombre | varchar | 50 | si | Nombre del rol (ej: "Coordinador", "Técnico Contratado", "Pasante Técnico") |
| requiere_password | boolean |  | si | Indica si el rol tiene acceso al módulo de gestión administrativa mediante contraseña |


## Tabla horarios_plantillas:

Tabla horarios_plantillas: En esta tabla irán todos los datos que definen los contenedores lógicos de horarios para clasificar si son fijos o flexibles.


| Campo | Tipo | Longitud | Requerimiento | Descripción |
| --- | --- | --- | --- | --- |
| id | int | 11 | si | Identificador único de la plantilla |
| nombre | varchar | 100 | si | Nombre descriptivo de la plantilla |
| tipo | enum |  | si | Define si el horario se compone de bloques fijos obligatorios o si es flexible |
| horas_requeridas | int | 11 | si | Cantidad mínima de horas a cumplir por semana (usado primordialmente para pasantes) |


## Tabla horarios_detalles:

Tabla horarios_detalles: En esta tabla irán todos los datos que detallan los bloques horarios específicos asignados por cada día de la semana para una plantilla fija.


| Campo | Tipo | Longitud | Requerimiento | Descripción |
| --- | --- | --- | --- | --- |
| id | int | 11 | si | Identificador único del bloque de detalle |
| horario_plantilla_id | int | 11 | si | Referencia a la plantilla de horario padre |
| dia_semana | tinyint | 4 | si | Día de la semana (1 = Lunes, 2 = Martes, ..., 7 = Domingo) |
| hora_entrada | time |  | si | Hora exacta obligatoria para registrar el ingreso |
| hora_salida | time |  | si | Hora exacta obligatoria para registrar la salida |


## Tabla redes_autorizadas:

Tabla redes_autorizadas: En esta tabla irán todos los datos que contienen la lista blanca de direcciones IP o subredes desde las cuales es válido registrar asistencias.


| Campo | Tipo | Longitud | Requerimiento | Descripción |
| --- | --- | --- | --- | --- |
| id | int | 11 | si | Identificador único de la regla de red |
| direccion_ip | varchar | 45 | si | Dirección IP (IPv4/IPv6) o notación CIDR (rango de red) |
| descripcion | varchar | 255 | si | Comentario descriptivo del punto físico de conexión |
| activo | boolean |  | si | Indica si la regla de red está vigente |


## Tabla usuarios:

Tabla usuarios: En esta tabla irán todos los datos de la entidad principal que almacena los datos de los técnicos, programadores, pasantes y coordinadores.


| Campo | Tipo | Longitud | Requerimiento | Descripción |
| --- | --- | --- | --- | --- |
| id | int | 11 | si | Identificador único de usuario |
| horario_id | int | 11 | si | Referencia a la plantilla de horario asignada |
| rol_id | int | 11 | si | Referencia al rol asignado |
| departamento_id | int | 11 | si | Referencia a la unidad organizacional a la que pertenece |
| documento_identidad | varchar | 20 | si | Cédula de identidad o pasaporte del usuario |
| nombre | varchar | 100 | si | Nombres del usuario |
| apellido | varchar | 100 | si | Apellidos del usuario |
| vector_biometrico | text |  | no | Representación matemática serializada de los vectores faciales para el reconocimiento biométrico |
| codigo_qr | varchar | 255 | no | Hash/código único de credencial QR generado para el usuario |
| password_hash | varchar | 255 | no | Contraseña encriptada para el acceso a la web administrativa (solo perfiles autorizados) |
| activo | boolean |  | si | Estado lógico del usuario (Activo/Inactivo) |


## Tabla asistencias:

Tabla asistencias: En esta tabla irán todos los datos de transacciones históricas que guarda las marcaciones diarias de entrada y salida del personal.


| Campo | Tipo | Longitud | Requerimiento | Descripción |
| --- | --- | --- | --- | --- |
| id | int | 11 | si | Identificador del registro |
| usuario_id | int | 11 | si | Referencia al usuario que realiza la marcación |
| fecha | date |  | si | Fecha del registro |
| hora_entrada | time |  | si | Hora de marcación del ingreso |
| hora_salida | time |  | no | Hora de marcación del egreso (puede ser nula temporalmente si no ha salido) |
| estado_cumplimiento | enum |  | si | Categorización automática calculada por el sistema |
| ip_registro_entrada | varchar | 45 | si | IP desde la cual se marcó la entrada |
| ip_registro_salida | varchar | 45 | no | IP desde la cual se marcó la salida |
| metodo_validacion | enum |  | si | Método utilizado para verificar la identidad en el dispositivo de marcación |


## Tabla asistencias_pendientes:

Tabla asistencias_pendientes: En esta tabla irán todos los datos del registro de auditoría de las correcciones hechas manualmente por el coordinador sobre las asistencias inconsistentes o incompletas.


| Campo | Tipo | Longitud | Requerimiento | Descripción |
| --- | --- | --- | --- | --- |
| id | int | 11 | si | Identificador único de la resolución |
| asistencia_id | int | 11 | si | Referencia al registro de asistencia modificado |
| coordinador_id | int | 11 | si | Referencia al usuario (Coordinador) que aprobó la resolución |
| observacion | text |  | si | Justificación del cambio o nota explicativa |
| fecha_resolucion | datetime |  | si | Fecha y hora exactas en que se guardó la modificación |
| estado_anterior | varchar | 20 | si | Estado en el que se encontraba la asistencia antes de la resolución |
| estado_nuevo | varchar | 20 | si | Nuevo estado asignado tras la evaluación |