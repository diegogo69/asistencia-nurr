import json
import math
from datetime import datetime, date, time
from typing import Optional, List, Tuple
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.usuario import Usuario
from app.models.horario import HorarioPlantilla, HorarioDetalle, TipoHorario
from app.models.asistencia import Asistencia, EstadoCumplimiento, MetodoValidacion

UMBRAL_DISTANCIA_FACIAL = 0.55  # Umbral estándar para descriptores 128D de face-api.js

def calculate_euclidean_distance(v1: List[float], v2: List[float]) -> float:
    """Calcula la distancia euclidiana entre dos vectores numéricos."""
    arr1 = np.array(v1, dtype=np.float32)
    arr2 = np.array(v2, dtype=np.float32)
    return float(np.linalg.norm(arr1 - arr2))

def verify_user_identity(
    usuario: Usuario,
    metodo: MetodoValidacion,
    vector_facial: Optional[List[float]],
    codigo_qr: Optional[str]
) -> Tuple[bool, str]:
    """Verifica la identidad del usuario mediante reconocimiento facial o código QR."""
    if metodo == MetodoValidacion.FACIAL:
        if not vector_facial or len(vector_facial) != 128:
            return False, "Vector facial inválido o no suministrado por la cámara."

        if not usuario.vector_biometrico:
            return False, "El usuario no tiene enrolado su vector biométrico facial. Utilice el código QR de contingencia."

        try:
            stored_vector = json.loads(usuario.vector_biometrico)
        except Exception:
            return False, "Error al decodificar el vector biométrico almacenado."

        distancia = calculate_euclidean_distance(vector_facial, stored_vector)
        if distancia <= UMBRAL_DISTANCIA_FACIAL:
            return True, f"Identidad verificada exitosamente por reconocimiento facial (Distancia: {distancia:.2f})."
        else:
            return False, f"Autenticación biométrica fallida: el rostro no coincide (Distancia: {distancia:.2f} > {UMBRAL_DISTANCIA_FACIAL})."

    elif metodo == MetodoValidacion.QR:
        if not codigo_qr:
            return False, "Código QR de credencial no suministrado."

        if not usuario.codigo_qr:
            return False, "El usuario no tiene una credencial QR asignada."

        if usuario.codigo_qr.strip() == codigo_qr.strip():
            return True, "Identidad verificada exitosamente mediante credencial QR."
        else:
            return False, "Código QR de credencial inválido o no reconocido."

    return False, "Método de autenticación no admitido."

def calculate_attendance_status(usuario: Usuario, current_dt: datetime) -> EstadoCumplimiento:
    """Calcula el estado de cumplimiento (puntual, retraso, anticipada) contrastando contra el horario."""
    if not usuario.horario:
        return EstadoCumplimiento.PUNTUAL

    horario = usuario.horario

    # Horario flexible (Pasantes)
    if horario.tipo == TipoHorario.FLEXIBLE:
        return EstadoCumplimiento.PUNTUAL

    # Horario fijo (Personal Contratado)
    if horario.tipo == TipoHorario.FIJO:
        dia_semana_actual = current_dt.isoweekday()  # 1 = Lunes ... 7 = Domingo
        detalle = None
        for d in horario.detalles:
            if d.dia_semana == dia_semana_actual:
                detalle = d
                break

        if not detalle:
            # Marcación fuera de los días regulares planificados
            return EstadoCumplimiento.PUNTUAL

        # Comparar hora actual con hora_entrada en minutos
        hora_actual = current_dt.time()
        curr_mins = hora_actual.hour * 60 + hora_actual.minute
        req_mins = detalle.hora_entrada.hour * 60 + detalle.hora_entrada.minute
        diff = curr_mins - req_mins

        tolerancia = settings.TOLERANCIA_MINUTOS_ENTRADA  # 15 minutos

        if diff < -tolerancia:
            return EstadoCumplimiento.ANTICIPADA
        elif diff <= tolerancia:
            return EstadoCumplimiento.PUNTUAL
        else:
            return EstadoCumplimiento.RETRASO

    return EstadoCumplimiento.PENDIENTE

def process_attendance_clocking(
    db: Session,
    usuario: Usuario,
    metodo: MetodoValidacion,
    client_ip: str,
    now_dt: Optional[datetime] = None
) -> Tuple[Asistencia, str, str]:
    """Procesa la transacción de marcación en base de datos: determina si es ENTRADA o SALIDA y calcula estado."""
    if now_dt is None:
        now_dt = datetime.now()

    hoy = now_dt.date()
    hora_actual = now_dt.time()

    # Buscar si ya existe marcación el día de hoy
    asistencia_hoy = db.query(Asistencia).filter(
        Asistencia.usuario_id == usuario.id,
        Asistencia.fecha == hoy
    ).first()

    if not asistencia_hoy:
        # Caso 1: Registrar ENTRADA
        estado = calculate_attendance_status(usuario, now_dt)
        nueva_asistencia = Asistencia(
            usuario_id=usuario.id,
            fecha=hoy,
            hora_entrada=hora_actual,
            hora_salida=None,
            estado_cumplimiento=estado,
            ip_registro_entrada=client_ip,
            ip_registro_salida=None,
            metodo_validacion=metodo
        )
        db.add(nueva_asistencia)
        db.commit()
        db.refresh(nueva_asistencia)
        return nueva_asistencia, "ENTRADA", f"Entrada registrada exitosamente a las {hora_actual.strftime('%I:%M %p')}. Estado: {estado.value.capitalize()}."

    elif asistencia_hoy.hora_salida is None:
        # Caso 2: Registrar SALIDA
        asistencia_hoy.hora_salida = hora_actual
        asistencia_hoy.ip_registro_salida = client_ip
        db.commit()
        db.refresh(asistencia_hoy)
        return asistencia_hoy, "SALIDA", f"Salida registrada exitosamente a las {hora_actual.strftime('%I:%M %p')}."

    else:
        # Caso 3: Ya completó tanto entrada como salida hoy
        return asistencia_hoy, "COMPLETADO", f"El usuario ya completó su jornada diaria hoy (Entrada: {asistencia_hoy.hora_entrada.strftime('%I:%M %p')}, Salida: {asistencia_hoy.hora_salida.strftime('%I:%M %p')})."
