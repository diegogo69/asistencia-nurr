# **Definición de las Interfaces de Usuario por Caso de Uso**

### **Caso de Uso 1: Gestionar Unidades Organizacionales**

* **Módulo de Presentación:** Interfaz de Gestionar Unidades Organizacionales  
* **Definición de Componentes y Flujo Funcional:**  
  * **Barra de Herramientas Superior:**  
    * **Botón** Agregar Unidad**:** Despliega una ventana emergente (*Modal*) para la creación de una unidad.  
    * **Campo/Filtro** Filtrar**:** Entrada de texto y selectores para la búsqueda dinámica en tiempo real por nombre o tipo de unidad (*Dirección*, *Coordinación*, *Sección*, *Oficina*).  
  * **Tabla de Visualización de Registros:**  
    * Muestra las columnas correspondientes a la estructura organizativa (Nombre, Tipo de Unidad).  
    * **Columna** Acciones**:** Cada fila incluye los botones interactivos:  
      * **Botón** Editar**:** Abre el modal de edición cargando los datos de la unidad seleccionada.  
      * **Botón** Eliminar**:** Solicita confirmación y ejecuta el borrado lógico o físico (si no posee dependencias o usuarios vinculados).  
  * **Barra de Navegación / Paginador:**  
    * Contiene los controles Primero, Anterior, Siguiente y Último para el desplazamiento paginado de la tabla (deshabilitados si no hay registros o si existen menos de 10 elementos).  
  * **Ventana Emergente (Modal)** Formulario de Unidad Organizacional**:**  
    * **Campos de Entrada:** Campo de texto libre para Nombre y menú desplegable para Tipo de Unidad.  
    * **Controles de Acción:**  
      * **Botón** Guardar**:** Invoca el servicio de validación de no duplicidad y almacena en la base de datos.  
      * **Botón** Cerrar**:** Oculta la pantalla emergente descartando cambios no guardados.

### 

### **Caso de Uso 2: Gestionar Horarios**

* **Módulo de Presentación:** Interfaz de Gestionar Horarios  
* **Definición de Componentes y Flujo Funcional:**  
  * **Barra de Herramientas Superior:**  
    * **Botón** Agregar Plantilla**:** Despliega el formulario emergente para definir un nuevo esquema de horario.  
    * **Campo/Filtro** Filtrar**:** Permite realizar búsquedas por el nombre de la plantilla o el tipo (*Fijo* o *Flexible*).  
  * **Tabla de Visualización de Registros:**  
    * Muestra las columnas descriptivas (Nombre de Plantilla, Tipo, Horas Requeridas Semanales).  
    * **Columna** Acciones**:**  
      * **Botón** Editar**:** Despliega la interfaz de edición con los bloques u horas semanales cargados.  
      * **Botón** Eliminar**:** Dispara el proceso de verificación de asignación a usuarios antes de confirmar la eliminación.  
  * **Barra de Navegación / Paginador:**  
    * Incluye los botones de paginación Primero, Anterior, Siguiente y Último.  
  * **Ventana Emergente (Modal)** Formulario de Plantilla de Horarios**:**  
    * **Campos Principales:** Campo de texto para Nombre de Plantilla, selector para Tipo (*Fijo* / *Flexible*) y campo numérico para Horas Requeridas Semanales (activado para horarios flexibles de pasantes).  
    * **Módulo Dinámico de Bloques Horarios (Solo para Tipo Fijo):**  
      * Matriz de asignación por día de la semana (Lunes a Domingo) con selectores de Hora de Entrada y Hora de Salida por cada día.  
    * **Controles de Acción:**  
      * **Botón** Guardar**:** Dispara las validaciones de rango (hora entrada \< hora salida) y duplicidad de nombre.  
      * **Botón** Cerrar**:** Cancela la operación y cierra el modal.

### 

### **Caso de Uso 3: Gestionar y Validar Rangos de Red Autorizados**

* **Módulo de Presentación:** Interfaz de Gestionar Rangos de Red  
* **Definición de Componentes y Flujo Funcional:**  
  * **Barra de Herramientas Superior:**  
    * **Botón** Agregar Red**:** Despliega el modal de configuración de la dirección IP/CIDR.  
    * **Campo/Filtro** Filtrar**:** Entrada de texto para buscar por dirección IP, descripción o estado de la regla.  
  * **Tabla de Visualización de Registros:**  
    * Presenta la lista blanca de conexión (Dirección IP/CIDR, Descripción, Estado).  
    * **Columna** Acciones**:**  
      * **Botón** Editar**:** Permite corregir el rango IP o la descripción.  
      * **Botón/Switch** Activar/Desactivar**:** Cambia el estado de la regla de red en tiempo real.  
      * **Botón** Eliminar**:** Elimina la regla de la lista blanca.  
  * **Barra de Navegación / Paginador:**  
    * Controles Primero, Anterior, Siguiente y Último.  
  * **Ventana Emergente (Modal)** Formulario de Regla de Red**:**  
    * **Campos de Entrada:** Campo para Dirección IP/CIDR (con máscara de formato IPv4/IPv6) y área de texto para Descripción.  
    * **Controles de Acción:**  
      * **Botón** Guardar**:** Valida el formato IP, comprueba duplicidad e inserta la regla activa.  
      * **Botón** Cerrar**:** Oculta el formulario sin guardar.  
  * **Interfaz / Componente Servidor (Proceso Automático):**  
    * Componente no visual que intercepta las peticiones de marcación y retorna alertas de bloqueo ("*Dispositivo fuera del rango de red autorizado*") en la pantalla de marcación del cliente si la IP no pertenece a las reglas activas.

### 

### **Caso de Uso 4: Gestionar Usuarios**

* **Módulo de Presentación:** Interfaz de Gestionar Usuarios  
* **Definición de Componentes y Flujo Funcional:**  
  * **Barra de Herramientas Superior:**  
    * **Botón** Agregar Usuario**:** Abre la planilla de registro de nuevo usuario.  
    * **Campo/Filtro** Filtrar**:** Filtra en tiempo real por documento de identidad, nombre, apellido, rol o departamento.  
  * **Tabla de Visualización de Registros:**  
    * Despliega la información general (Documento, Nombres y Apellidos, Rol, Departamento, Estado).  
    * **Columna** Acciones**:**  
      * **Botón** Editar**:** Permite modificar los datos del usuario, su rol o su horario.  
      * **Botón** Desactivar/Borrar**:** Ejecuta un borrado lógico (activo \= false) si posee histórico de asistencias o borrado físico si no tiene registros.  
  * **Barra de Navegación / Paginador:**  
    * Controles de paginación Primero, Anterior, Siguiente y Último.  
  * **Ventana Emergente (Modal)** Formulario de Gestión de Usuarios**:**  
    * **Campos de Entrada:** Documento de Identidad, Nombres, Apellidos, selector de Rol, selector de Departamento y selector de Plantilla de Horario.  
    * **Campo Condicional:** Campo Contraseña (se habilita automáticamente si el rol seleccionado requiere acceso administrativo: requiere\_password \= true).  
    * **Controles de Acción:**  
      * **Botón** Guardar**:** Dispara el servicio de validación de unicidad de identidad y almacena el registro.  
      * **Botón** Cerrar**:** Cancela y cierra el modal.

### 

### **Caso de Uso 5: Validar Registro Único (Impedir Duplicidad)**

* **Módulo de Presentación:** Servicio de Validación de Interfaz (Integrado en Formulario de Usuarios)  
* **Definición de Componentes y Flujo Funcional:**  
  * **Evento al Perder el Foco (*OnBlur*) / Evento al Guardar:**  
    * Componente de escucha en el campo Documento de Identidad dentro del formulario de usuarios.  
  * **Mecanismo de Respuesta Visual en la Interfaz:**  
    * **Indicador de Error:** Resaltado de borde en color rojo alrededor del campo Documento de Identidad.  
    * **Mensaje de Alerta Integrado:** Despliegue de un texto o banner informativo de error ("*El documento de identidad ingresado ya se encuentra registrado en la plataforma*").  
  * **Control de Estado de la Interfaz:**  
    * Inhabilitación o bloqueo dinámico del botón Guardar mientras persista la condición de duplicidad o un formato alfanumérico no válido.

### 

### **Caso de Uso 6: Registrar Biometría Facial**

* **Módulo de Presentación:** Interfaz de Enrolamiento Biométrico Facial  
* **Definición de Componentes y Flujo Funcional:**  
  * **Panel de Captura de Vídeo:**  
    * **Componente de Vista Previa (*Webcam View*):** Recuadro que proyecta la señal en vivo de la cámara web.  
    * **Guía Visual de Encuadre:** Recuadro u óvalo sobrepuesto en la vista previa para guiar la postura del usuario.  
  * **Controles y Botones:**  
    * **Botón** Iniciar Captura / Activar Cámara**:** Solicita los permisos del navegador e inicia la transmisión de vídeo.  
    * **Botón** Capturar y Validar Rostro**:** Congela la imagen actual para que el algoritmo verifique condiciones de iluminación, enfoque y presencia del rostro.  
    * **Botón** Reintentar**:** Descarta la captura fotográfica previa, limpia los mensajes de error y reinicia el flujo en vivo de la cámara.  
  * **Retroalimentación del Sistema:**  
    * Mensajes de estado en tiempo real ("*Cámara no detectada*", "*Rostro no detectado correctamente*", "*Patrón biométrico facial registrado correctamente*").

### 

### **Caso de Uso 7: Generar Código QR de Identificación**

* **Módulo de Presentación:** Interfaz de Credencial y Registro QR  
* **Definición de Componentes y Flujo Funcional:**  
  * **Área de Renderizado del Código QR:**  
    * **Componente Visor de QR:** Espacio donde el sistema dibuja la matriz bidimensional del código QR generado dinámicamente a partir del hash único.  
  * **Panel de Información del Usuario (Vista de Credencial):**  
    * Muestra resumida del Nombre, Apellido, Documento de Identidad, Departamento y Rol.  
  * **Controles de Acción:**  
    * **Botón** Descargar Credencial QR**:** Genera y descarga el archivo gráfico en formato PDF o imagen.  
    * **Botón** Imprimir Carnet**:** Abre el diálogo de impresión directamente desde el navegador.  
    * **Botón** Regenerar Código QR**:** Dispara la invalidación del hash antiguo y la creación inmediata de una nueva credencial (útil ante extravíos).

### 

### **Caso de Uso 8: Autenticar Usuarios Administrativos**

* **Módulo de Presentación:** Interfaz de Inicio de Sesión (Login Administrative)  
* **Definición de Componentes y Flujo Funcional:**  
  * **Formulario de Credenciales:**  
    * **Campo** Documento / Usuario**:** Entrada de texto para el número de identificación.  
    * **Campo** Contraseña**:** Entrada de texto con enmascaramiento de caracteres.  
  * **Controles de Acción:**  
    * **Botón** Iniciar Sesión**:** Envía la solicitud para validar las credenciales, verificar la clave encriptada y comprobar que el rol tenga privilegios administrativos (requiere\_password \= true).  
  * **Manejo de Respuestas / Mensajes de Error:**  
    * Área para notificaciones que muestra alertas en caso de credenciales inválidas, usuario inhabilitado o falta de permisos administrativos.  
  * **Módulo del Menú Principal (Post-Autenticación):**  
    * Incluye el botón/opción Cerrar Sesión visible en la barra superior para destruir el token de sesión activo y retornar al login.

### 

### **Caso de Uso 9: Registrar y Validar Asistencias**

* **Módulo de Presentación:** Interfaz del Punto de Marcación (Kiosco / Pantalla de Marcaje)  
* **Definición de Componentes y Flujo Funcional:**  
  * **Pantalla de Entrada de Datos:**  
    * **Campo** Documento de Identidad**:** Entrada de texto para iniciar el proceso de marcación.  
  * **Módulo de Autenticación Integrado:**  
    * **Visor de Cámara Facial:** Componente de escaneo biométrico automático al ingresar la cédula.  
    * **Lector / Escáner QR de Contingencia:** Componente alternativo activado automáticamente en caso de fallo o indetección facial para escanear la credencial física/digital.  
  * **Módulo de Confirmación y Retroalimentación:**  
    * **Panel de Resultado de Marcación:** Al terminar el proceso, despliega en pantalla la información formateada:  
      * Datos del usuario (Nombre, Apellido, Departamento).  
      * Tipo de Marcación calculada automáticamente (ENTRADA o SALIDA).  
      * Hora exacta de registro y el Estado de Cumplimiento determinado (*Puntual*, *Retraso*, *Anticipada*).  
      * Método utilizado (*Facial* o *QR*).  
  * **Manejo de Mensajes de Error:**  
    * Notificaciones en pantalla ante errores de red no autorizada, usuario inexistente/inactivo o fallo de autenticación de identidad.

### 

### **Caso de Uso 10: Detectar y Resolver Asistencias Incompletas**

* **Módulo de Presentación:** Interfaz del Panel de Asistencias Incompletas  
* **Definición de Componentes y Flujo Funcional:**  
  * **Tabla de Incidencias / Registros Irregulares:**  
    * Presenta la lista de marcaciones que tienen hora de entrada registrada pero hora de salida nula (NULL), con su estado automático actualizado a incompleto.  
    * Columnas: Fecha, Usuario, Departamento, Hora de Entrada, Estado Actual.  
  * **Columna de Acción:**  
    * **Botón** Resolver Incidencia**:** Abre la ventana emergente de resolución manual.  
  * **Ventana Emergente (Modal)** Resolución de Inconsistencia**:**  
    * **Campos de Edición:**  
      * Selector de Hora de Salida (para imputar la hora omitida).  
      * Desplegable de Nuevo Estado de Cumplimiento (*Puntual*, *Retraso*, etc.).  
      * Área de texto obligatoria Observación / Justificación.  
    * **Controles de Acción:**  
      * **Botón** Guardar Resolución**:** Verifica la presencia de la observación justificativa, actualiza la tabla de asistencias e inserta el registro inmutable de auditoría en asistencias\_pendientes.  
      * **Botón** Cancelar**:** Oculta la ventana emergente.

### 

### **Caso de Uso 11: Consultar Historial de Asistencia**

* **Módulo de Presentación:** Interfaz de Consulta de Historial  
* **Definición de Componentes y Flujo Funcional:**  
  * **Panel de Filtros Avanzados (Barra Superior):**  
    * Selector de Rango de Fechas (Fecha Desde / Fecha Hasta).  
    * Selector desplegable de Usuario específico.  
    * Selector desplegable de Departamento.  
    * Selector desplegable de Estado de Cumplimiento (*Puntual*, *Retraso*, *Anticipada*, *Incompleto*).  
    * **Botón** Consultar / Aplicar Filtros**:** Actualiza la consulta en la base de datos con los parámetros seleccionados.  
  * **Tabla de Resultados del Historial:**  
    * Despliega el desglose consolidado de marcaciones: Fecha, Usuario, Departamento, Hora Entrada, Hora Salida, Método (Facial/QR), Estado de Cumplimiento.  
    * Muestra un mensaje informativo en caso de que la búsqueda no arroje coincidencias ("*No se encontraron registros de asistencia para los filtros especificados*").  
  * **Barra de Navegación / Paginador:**  
    * Botones Primero, Anterior, Siguiente y Último para recorrer los registros de manera paginada.

### 

### **Caso de Uso 12: Generar Reportes de Asistencia**

* **Módulo de Presentación:** Interfaz de Generación de Reportes  
* **Definición de Componentes y Flujo Funcional:**  
  * **Formulario de Parametrización del Reporte:**  
    * Selectores de Rango de Fechas (Fecha Desde y Fecha Hasta).  
    * Filtros opcionales de segmentación: Desplegable de Departamento y Desplegable de Usuario.  
    * Selector del Formato de Exportación (Opciones: *PDF* / *CSV-Excel*).  
  * **Controles de Acción:**  
    * **Botón** Procesar y Exportar Reporte**:** Desencadena el cálculo de métricas consolidadas (acumulado de horas trabajadas, total de puntualidades, retrasos e inasistencias).  
  * **Mecanismos de Salida / Visualización:**  
    * **Para Formato PDF:** Abre una vista previa descargable del documento formateado con encabezados institucionales de la ULA-NURR y línea de firma para la coordinación.  
    * **Para Formato CSV / Excel:** Dispara la descarga directa del archivo plano con la matriz de datos procesada.  
  * **Manejo de Excepciones:**  
    * Alerta en pantalla si la consulta no devuelve datos para el período o filtros seleccionados ("*No existen registros disponibles para generar el reporte en el rango especificado*").

