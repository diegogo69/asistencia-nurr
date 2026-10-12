from datetime import datetime, date, time, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.asistencia import Asistencia, EstadoCumplimiento
from app.models.asistencia_pendiente import AsistenciaPendiente

def detect_and_mark_incomplete_attendances(db: Session, reference_date: Optional[date] = None) -> int:
    """Busca asistencias con hora_salida nula de jornadas previas a la fecha de referencia

    y actualiza su estado automáticamente a 'incompleto'.
    """
    if reference_date is None:
        reference_date = datetime.now().date()

    incompletas = db.query(Asistencia).filter(
        Asistencia.hora_salida.is_(None),
        Asistencia.fecha < reference_date,
        Asistencia.estado_cumplimiento != EstadoCumplimiento.INCOMPLETO
    ).all()

    count = len(incompletas)
    for a in incompletas:
        a.estado_cumplimiento = EstadoCumplimiento.INCOMPLETO

    if count > 0:
        db.commit()

    return count

def resolve_incident(
    db: Session,
    coordinador_id: int,
    asistencia_id: int,
    hora_salida: time,
    nuevo_estado: EstadoCumplimiento,
    observacion: str
) -> Tuple[Asistencia, AsistenciaPendiente]:
    """Ejecuta una transacción atómica para resolver una asistencia irregular e

    insertar el registro inmutable en asistencias_pendientes.
    """
    asistencia = db.query(Asistencia).filter(Asistencia.id == asistencia_id).first()
    if not asistencia:
        raise ValueError("El registro de asistencia especificado no existe.")

    # Validar que la hora de salida sea mayor que la de entrada
    if asistencia.hora_entrada >= hora_salida:
        raise ValueError(
            f"La hora de salida ({hora_salida.strftime('%H:%M')}) debe ser posterior a la hora de entrada ({asistencia.hora_entrada.strftime('%H:%M')})."
        )

    estado_anterior = asistencia.estado_cumplimiento.value

    # 1. Crear registro inmutable de auditoría
    resolucion = AsistenciaPendiente(
        asistencia_id=asistencia.id,
        coordinador_id=coordinador_id,
        observacion=observacion.strip(),
        fecha_resolucion=datetime.now(timezone.utc),
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado.value
    )
    db.add(resolucion)

    # 2. Actualizar registro en asistencias
    asistencia.hora_salida = hora_salida
    asistencia.estado_cumplimiento = nuevo_estado

    db.commit()
    db.refresh(asistencia)
    db.refresh(resolucion)

    return asistencia, resolucion
