from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.network import is_ip_authorized
from app.models.usuario import Usuario
from app.models.asistencia import Asistencia
from app.schemas.marcacion import (
    MarcacionRequest, MarcacionResponse, VerificarUsuarioMarcacionResponse
)
from app.services.attendance_engine import (
    verify_user_identity,
    process_attendance_clocking
)

router = APIRouter(prefix="/marcacion", tags=["Punto de Marcación"])

def get_client_ip(request: Request) -> str:
    """Extrae la dirección IP cliente de la solicitud."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    host = request.client.host if request.client else "127.0.0.1"
    if host == "testclient":
        return "127.0.0.1"
    return host

def check_authorized_network(request: Request, db: Session = Depends(get_db)):
    """Dependencia perimetral: valida que la petición provenga de una IP autorizada."""
    client_ip = get_client_ip(request)
    if not is_ip_authorized(client_ip, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Dispositivo fuera del rango de red autorizado (IP cliente: {client_ip})."
        )
    return client_ip

@router.post("/verificar-usuario", response_model=VerificarUsuarioMarcacionResponse, summary="Verificar usuario en el punto de marcación")
def verificar_usuario(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    client_ip: str = Depends(check_authorized_network)
):
    """Verifica si el usuario existe y si cuenta con biometría registrada para orientar la interfaz del kiosco."""
    documento = payload.get("documento_identidad", "").strip().upper()
    if not documento:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debe ingresar el documento de identidad.")

    usuario = db.query(Usuario).filter(func.upper(Usuario.documento_identidad) == documento).first()
    if not usuario:
        return VerificarUsuarioMarcacionResponse(
            registrado=False,
            activo=False,
            documento_identidad=documento,
            mensaje="Usuario no registrado en la institución."
        )

    if not usuario.activo:
        return VerificarUsuarioMarcacionResponse(
            registrado=True,
            activo=False,
            documento_identidad=usuario.documento_identidad,
            usuario_id=usuario.id,
            nombre_completo=usuario.nombre_completo,
            departamento=usuario.departamento.nombre if usuario.departamento else "",
            mensaje="La cuenta del usuario se encuentra inhabilitada."
        )

    tiene_bio = bool(usuario.vector_biometrico)

    # Determinar si la acción esperada es ENTRADA o SALIDA
    hoy = date.today()
    asistencia_abierta = db.query(Asistencia).filter(
        Asistencia.usuario_id == usuario.id,
        Asistencia.fecha == hoy,
        Asistencia.hora_salida.is_(None)
    ).first()
    accion = "SALIDA" if asistencia_abierta else "ENTRADA"

    return VerificarUsuarioMarcacionResponse(
        registrado=True,
        activo=True,
        documento_identidad=usuario.documento_identidad,
        usuario_id=usuario.id,
        nombre_completo=usuario.nombre_completo,
        departamento=usuario.departamento.nombre if usuario.departamento else "Soporte Técnico",
        tiene_biometria=tiene_bio,
        horario=usuario.horario.nombre if usuario.horario else "Sin horario asignado",
        accion_esperada=accion,
        mensaje="Usuario validado. Proceda con la autenticación facial o código QR."
    )

@router.post("/registrar", response_model=MarcacionResponse, summary="Registrar marcación de asistencia")
def registrar_marcacion(
    data: MarcacionRequest,
    request: Request,
    db: Session = Depends(get_db),
    client_ip: str = Depends(check_authorized_network)
):
    """Procesa y valida la marcación de asistencia con biometría facial o código QR de contingencia."""
    doc_clean = data.documento_identidad.strip().upper()
    usuario = db.query(Usuario).filter(func.upper(Usuario.documento_identidad) == doc_clean).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no registrado en el sistema."
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Su cuenta se encuentra inhabilitada. Contacte al coordinador."
        )

    # 1. Verificar identidad (Facial o QR)
    es_valido, motivo = verify_user_identity(
        usuario=usuario,
        metodo=data.metodo,
        vector_facial=data.vector_facial,
        codigo_qr=data.codigo_qr
    )

    if not es_valido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=motivo
        )

    # 2. Procesar marcación (determinar entrada/salida y estado)
    now_dt = datetime.now()
    asistencia, tipo_evento, mensaje = process_attendance_clocking(
        db=db,
        usuario=usuario,
        metodo=data.metodo,
        client_ip=client_ip,
        now_dt=now_dt
    )

    hora_display = (asistencia.hora_salida if tipo_evento == "SALIDA" else asistencia.hora_entrada).strftime("%I:%M %p")

    return MarcacionResponse(
        asistencia_id=asistencia.id,
        usuario_id=usuario.id,
        documento_identidad=usuario.documento_identidad,
        nombre_completo=usuario.nombre_completo,
        departamento=usuario.departamento.nombre if usuario.departamento else "Soporte Técnico",
        tipo_evento=tipo_evento,
        fecha=asistencia.fecha.strftime("%d/%m/%Y"),
        hora=hora_display,
        estado_cumplimiento=asistencia.estado_cumplimiento.value,
        metodo_validacion=asistencia.metodo_validacion.value,
        mensaje=mensaje
    )
