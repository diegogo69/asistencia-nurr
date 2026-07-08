# Modelo de Negocio: Sistema de Control de Asistencia Unidad de Soporte Técnico ULA-NURR

Este documento contiene la especificación formal del Modelo de Negocio actual (As-Is) para el proceso de control de asistencia de la Unidad de Soporte Técnico de la Universidad de los Andes (ULA-NURR).

## Actores del Negocio

Son las personas, roles o entidades que participan directamente en el día a día de la unidad o interactúan con sus procesos:

**Coordinador de la Unidad**: Encargado de supervisar los asuntos internos, planificar los horarios, custodiar los registros y validar la asistencia del personal y pasantes.

**Técnicos Contratados**: Personal de planta de la institución encargado de realizar labores de mantenimiento preventivo y correctivo de hardware y asistencia directa a usuarios.

**Programadores Contratados**: Personal de planta de la institución encargado del soporte lógico, desarrollo interno y mantenimiento de sistemas de la unidad.

**Pasantes Técnicos**: Estudiantes universitarios en periodo de práctica profesional que apoyan en las labores de soporte técnico de hardware.

**Pasantes Programadores**: Estudiantes universitarios en periodo de práctica profesional que apoyan en las áreas de desarrollo de software lógico.

**Usuarios Universitarios** (Externos): Personal administrativo, docente u obrero de las distintas áreas de la ULA-NURR que solicita los servicios de soporte técnico a la unidad.

## Objetos del Negocio

Son las entidades de información, insumos o herramientas, físicas o digitales, que los actores manipulan, producen o utilizan en el flujo de trabajo:

**Hoja de Asistencia Diaria**: Formato físico en papel generado cada mañana donde se registra manualmente la fecha, los nombres de los integrantes, sus cédulas de identidad, firmas y las horas exactas de entrada y salida.

**Informe de Control de Visitas**: Documento administrativo-académico que los pasantes (técnicos y programadores) llenan con sus actividades diarias para certificar y validar sus horas acumuladas en el desarrollo de sus pasantías.

## Procesos del Negocio

El proceso es el flujo general para lograr un objetivo. Representan los flujos macro de trabajo lógicamente ordenados para cumplir los objetivos de control interno de la unidad:

1. **Control Diario de Asistencia**: Abarca las tareas consecutivas orientadas al registro del ingreso y egreso diario de todo el personal de la unidad técnico-operativa.

2. **Auditoría y Validación de Horas**: Abarca el flujo de revisión, fiscalización y contraste manual de los registros históricos frente a solicitudes, reportes de incidencias o informes de pasantías.

## Actividades del Negocio

Detalle secuencial y paso a paso de las acciones que ejecutan los actores sobre los objetos en cada proceso:

### Actividades del Proceso 1 (Control Diario de Asistencia)

- **Apertura**: Al iniciar la jornada, el Coordinador genera manualmente la Hoja de Asistencia Diaria, escribiendo a mano los encabezados de las columnas (Nombre, Apellido, Cédula, Firma, Hora de llegada, Hora de salida).

- **Registro de Entrada**: Cada integrante (Técnico, Programador o Pasante) acude al área común al llegar a la unidad, escribe sus datos de identidad, anota la hora actual de entrada y estampa su firma.

- **Registro de Salida**: Al finalizar su jornada diaria, el integrante se dirige nuevamente a la hoja física y asienta manualmente su hora de salida.

Cierre y Archivo: Al culminar el turno operativo, el Coordinador retira la hoja del área común y la archiva físicamente en una carpeta cronológica de control.

### Actividades del Proceso 2 (Auditoría y Validación de Horas)

- **Revisión por Incidencias**: Ante la detección de ausentismo o impuntualidad recurrente, el Coordinador busca manualmente en la carpeta de archivo las hojas físicas de las fechas requeridas para verificar las firmas.

- **Cotejo de Informes de Pasantías**: Al recibir el Informe de Control de Visitas por parte de un pasante, el Coordinador realiza una validación visual manual cruzando las horas declaradas por el estudiante con los registros de la carpeta física, firmando el informe únicamente si los datos concuerdan.

## Reglas del Negocio

Políticas, restricciones y normativas operacionales o institucionales que rigen el comportamiento del negocio:

1. **Horario Fijo Institucional**: El Coordinador y el personal contratado (técnicos y programadores de planta) rigen su jornada bajo un bloque obligatorio fijo de lunes a miércoles, desde las 8:00 AM hasta la 1:00 PM.

2. **Horario Flexible para Pasantes**: Los pasantes de soporte técnico y programación no poseen un bloque de horario único institucional; sus jornadas se definen mediante bloques asignados en acuerdo previo con el Coordinador (ej. bloques de 8:00 AM a 12:00 PM o de 9:00 AM a 11:00 AM), debiendo registrarse y validarse individualmente según la planificación establecida.

3. **Margen Operacional Académico**: Todos los pasantes deben acumular de forma obligatoria entre 2 y 4 horas semanales de labor en la unidad a lo largo de un ciclo de 34 semanas para cumplir con los lineamientos del proceso de pasantías.

4. **Excepción por Omisión de Registro**: Ante un registro incompleto (olvido de la firma/marcado de la hora de salida), el caso queda fuera del flujo estándar y pasa directamente a una resolución manual bajo el criterio exclusivo del Coordinador.
