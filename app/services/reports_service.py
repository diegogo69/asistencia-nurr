import io
import csv
from datetime import datetime, date, time
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, KeepTogether

from app.models.asistencia import Asistencia, EstadoCumplimiento
from app.models.usuario import Usuario
from app.models.departamento import Departamento
from app.models.rol import Rol
from app.schemas.reportes import UsuarioReporteMetricas, ReporteResumenResponse

def calculate_hours_worked(entrada: time, salida: Optional[time]) -> float:
    """Calcula las horas efectivas trabajadas con dos decimales."""
    if not salida or not entrada:
        return 0.0
    min_entrada = entrada.hour * 60 + entrada.minute + entrada.second / 60.0
    min_salida = salida.hour * 60 + salida.minute + salida.second / 60.0
    diff_min = max(0.0, min_salida - min_entrada)
    return round(diff_min / 60.0, 2)

def build_attendance_query(
    db: Session,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    usuario_id: Optional[int] = None,
    departamento_id: Optional[int] = None,
    estado: Optional[EstadoCumplimiento] = None
):
    query = db.query(Asistencia).join(Usuario, Asistencia.usuario_id == Usuario.id)
    if fecha_desde:
        query = query.filter(Asistencia.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Asistencia.fecha <= fecha_hasta)
    if usuario_id:
        query = query.filter(Asistencia.usuario_id == usuario_id)
    if departamento_id:
        query = query.filter(Usuario.departamento_id == departamento_id)
    if estado:
        query = query.filter(Asistencia.estado_cumplimiento == estado)

    return query

def compute_report_metrics(asistencias: List[Asistencia]) -> ReporteResumenResponse:
    """Calcula las métricas analíticas consolidadas y el acumulado por usuario."""
    total_marcaciones = len(asistencias)
    total_horas = 0.0
    puntuales = 0
    retrasos = 0
    anticipadas = 0
    incompletos = 0

    user_map: Dict[int, Dict[str, Any]] = {}

    for a in asistencias:
        h = calculate_hours_worked(a.hora_entrada, a.hora_salida)
        total_horas += h

        if a.estado_cumplimiento == EstadoCumplimiento.PUNTUAL:
            puntuales += 1
        elif a.estado_cumplimiento == EstadoCumplimiento.RETRASO:
            retrasos += 1
        elif a.estado_cumplimiento == EstadoCumplimiento.ANTICIPADA:
            anticipadas += 1
        elif a.estado_cumplimiento == EstadoCumplimiento.INCOMPLETO:
            incompletos += 1

        uid = a.usuario_id
        if uid not in user_map:
            user_map[uid] = {
                "usuario_id": uid,
                "documento_identidad": a.usuario.documento_identidad,
                "nombre_completo": a.usuario.nombre_completo,
                "rol": a.usuario.rol.nombre if a.usuario.rol else "Personal",
                "departamento": a.usuario.departamento.nombre if a.usuario.departamento else "Soporte Técnico",
                "total_dias_asistidos": 0,
                "horas_totales_acumuladas": 0.0,
                "puntuales": 0,
                "retrasos": 0,
                "anticipadas": 0,
                "incompletos": 0,
            }

        user_map[uid]["total_dias_asistidos"] += 1
        user_map[uid]["horas_totales_acumuladas"] += h
        if a.estado_cumplimiento == EstadoCumplimiento.PUNTUAL:
            user_map[uid]["puntuales"] += 1
        elif a.estado_cumplimiento == EstadoCumplimiento.RETRASO:
            user_map[uid]["retrasos"] += 1
        elif a.estado_cumplimiento == EstadoCumplimiento.ANTICIPADA:
            user_map[uid]["anticipadas"] += 1
        elif a.estado_cumplimiento == EstadoCumplimiento.INCOMPLETO:
            user_map[uid]["incompletos"] += 1

    user_metrics = [
        UsuarioReporteMetricas(
            usuario_id=m["usuario_id"],
            documento_identidad=m["documento_identidad"],
            nombre_completo=m["nombre_completo"],
            rol=m["rol"],
            departamento=m["departamento"],
            total_dias_asistidos=m["total_dias_asistidos"],
            horas_totales_acumuladas=round(m["horas_totales_acumuladas"], 2),
            puntuales=m["puntuales"],
            retrasos=m["retrasos"],
            anticipadas=m["anticipadas"],
            incompletos=m["incompletos"]
        )
        for m in sorted(user_map.values(), key=lambda x: x["nombre_completo"])
    ]

    return ReporteResumenResponse(
        total_marcaciones=total_marcaciones,
        total_horas_acumuladas=round(total_horas, 2),
        total_puntuales=puntuales,
        total_retrasos=retrasos,
        total_anticipadas=anticipadas,
        total_incompletos=incompletos,
        usuarios=user_metrics
    )

def generate_csv_report(asistencias: List[Asistencia]) -> bytes:
    """Genera un archivo CSV codificado con UTF-8 BOM para compatibilidad directa con Excel."""
    output = io.StringIO()
    # Escribir UTF-8 BOM para evitar problemas de tildes en Excel
    output.write("\ufeff")

    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Fecha", "Documento", "Nombre Completo", "Rol", "Departamento",
        "Hora Entrada", "Hora Salida", "Horas Laboradas", "Estado Cumplimiento",
        "Método Validación"
    ])

    for a in asistencias:
        h = calculate_hours_worked(a.hora_entrada, a.hora_salida)
        writer.writerow([
            a.fecha.strftime("%d/%m/%Y"),
            a.usuario.documento_identidad,
            a.usuario.nombre_completo,
            a.usuario.rol.nombre if a.usuario.rol else "",
            a.usuario.departamento.nombre if a.usuario.departamento else "",
            a.hora_entrada.strftime("%H:%M:%S"),
            a.hora_salida.strftime("%H:%M:%S") if a.hora_salida else "SIN SALIDA",
            f"{h:.2f}",
            a.estado_cumplimiento.value.capitalize(),
            a.metodo_validacion.value.upper()
        ])

    return output.getvalue().encode("utf-8")

def generate_pdf_report(
    asistencias: List[Asistencia],
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    depto_nombre: Optional[str] = None
) -> bytes:
    """Genera un documento PDF institucional con membrete ULA-NURR, desglose y línea de firma."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        "HeaderStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        textColor=colors.HexColor("#0D47A1"),
        alignment=1
    )
    subheader_style = ParagraphStyle(
        "SubHeaderStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#333333"),
        alignment=1
    )
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1A237E"),
        alignment=1
    )
    cell_style = ParagraphStyle(
        "CellStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10
    )

    story = []

    # 1. Membrete Institucional
    story.append(Paragraph("UNIVERSIDAD DE LOS ANDES - NÚCLEO UNIVERSITARIO RAFAEL RANGEL", header_style))
    story.append(Paragraph("UNIDAD DE SOPORTE TÉCNICO | SISTEMA DE CONTROL DE ASISTENCIA", subheader_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("INFORME OFICIAL CONSOLIDADO DE ASISTENCIA Y AUDITORÍA", title_style))
    story.append(Spacer(1, 8))

    # 2. Metadatos del Informe
    periodo_str = f"Período: {fecha_desde.strftime('%d/%m/%Y') if fecha_desde else 'Inicio'} al {fecha_hasta.strftime('%d/%m/%Y') if fecha_hasta else 'Actual'}"
    emision_str = f"Emitido el: {datetime.now().strftime('%d/%m/%Y %I:%M %p')}"
    depto_str = f"Unidad: {depto_nombre if depto_nombre else 'General (Todas las dependencias)'}"
    
    meta_table = Table([
        [Paragraph(f"<b>{periodo_str}</b>", cell_style), Paragraph(f"<b>{depto_str}</b>", cell_style), Paragraph(f"<b>{emision_str}</b>", cell_style)]
    ], colWidths=[240, 260, 220])
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # 3. Resumen Cuantitativo
    metrics = compute_report_metrics(asistencias)
    summary_data = [
        ["Total Marcaciones", "Horas Acumuladas", "Puntuales", "Retrasos", "Anticipadas", "Incompletas"],
        [
            str(metrics.total_marcaciones),
            f"{metrics.total_horas_acumuladas:.2f} hrs",
            str(metrics.total_puntuales),
            str(metrics.total_retrasos),
            str(metrics.total_anticipadas),
            str(metrics.total_incompletos)
        ]
    ]
    summary_table = Table(summary_data, colWidths=[120, 120, 120, 120, 120, 120])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0D47A1")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#F5F5F5")),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 14))

    # 4. Tabla Detallada de Marcaciones
    table_headers = ["Fecha", "Cédula", "Nombre y Apellido", "Rol", "Entrada", "Salida", "Horas", "Estado"]
    table_rows = [table_headers]

    for a in asistencias:
        h = calculate_hours_worked(a.hora_entrada, a.hora_salida)
        salida_str = a.hora_salida.strftime("%I:%M %p") if a.hora_salida else "SIN SALIDA"
        table_rows.append([
            a.fecha.strftime("%d/%m/%Y"),
            a.usuario.documento_identidad,
            a.usuario.nombre_completo,
            a.usuario.rol.nombre if a.usuario.rol else "",
            a.hora_entrada.strftime("%I:%M %p"),
            salida_str,
            f"{h:.2f}",
            a.estado_cumplimiento.value.capitalize()
        ])

    detail_table = Table(table_rows, colWidths=[65, 75, 175, 125, 70, 75, 55, 80])
    detail_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A237E")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),
        ('ALIGN', (3, 1), (3, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 30))

    # 5. Sección de Validación y Firma de Coordinación
    firma_data = [
        ["", ""],
        ["_____________________________________________", "_____________________________________________"],
        ["Prof. Coordinador(a) de Soporte Técnico", "Sello Institucional Unidad de Soporte"],
        ["Universidad de los Andes - NURR", "Constancia Académica y Administrativa"]
    ]
    firma_table = Table(firma_data, colWidths=[360, 360])
    firma_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#424242")),
    ]))
    story.append(KeepTogether([firma_table]))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
