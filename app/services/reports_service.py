import io
import os
import csv
from datetime import datetime, date, time
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, KeepTogether, Image

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
    depto_nombre: Optional[str] = None,
    usuario_nombre: Optional[str] = None,
    titulo_reporte: Optional[str] = None
) -> bytes:
    """Genera un documento PDF institucional con membrete ULA-NURR, logo oficial,
    título de identificación, métricas de asistencia, desglose y línea de firma."""
    buffer = io.BytesIO()

    # Identificación y numeración de control oficial del reporte
    timestamp_actual = datetime.now()
    codigo_control = f"ASIS-NURR-{timestamp_actual.strftime('%Y%m%d-%H%M%S')}"

    if not titulo_reporte:
        if usuario_nombre:
            titulo_reporte = f"REPORTE INDIVIDUAL DE ASISTENCIA - {usuario_nombre.upper()}"
        elif depto_nombre:
            titulo_reporte = f"REPORTE DEPARTAMENTAL DE ASISTENCIA - {depto_nombre.upper()}"
        else:
            titulo_reporte = "REPORTE CONSOLIDADO DE ASISTENCIA"

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=28,
        bottomMargin=36,
        title=f"{titulo_reporte} ({codigo_control})",
        author="Universidad de Los Andes - NURR (Unidad de Soporte Técnico)",
        subject="Reporte Oficial de Asistencia y Auditoría",
        creator="Sistema Integrado de Control de Asistencia NURR"
    )

    styles = getSampleStyleSheet()

    inst_title_style = ParagraphStyle(
        "InstTitleStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#0056B3"),
        alignment=1
    )
    inst_sub_style = ParagraphStyle(
        "InstSubStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10.5,
        textColor=colors.HexColor("#1A237E"),
        alignment=1
    )
    inst_unit_style = ParagraphStyle(
        "InstUnitStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#555555"),
        alignment=1
    )
    doc_title_style = ParagraphStyle(
        "DocTitleStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=12.5,
        textColor=colors.HexColor("#0D47A1"),
        alignment=1
    )

    badge_label_style = ParagraphStyle(
        "BadgeLabelStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=6.5,
        leading=8,
        textColor=colors.HexColor("#555555"),
        alignment=1
    )
    badge_val_style = ParagraphStyle(
        "BadgeValStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0056B3"),
        alignment=1
    )
    badge_date_style = ParagraphStyle(
        "BadgeDateStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=8,
        textColor=colors.HexColor("#333333"),
        alignment=1
    )

    meta_style = ParagraphStyle(
        "MetaStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#222222")
    )
    cell_style = ParagraphStyle(
        "CellStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10
    )

    story = []

    # 1. Encabezado con Identidad Visual (Logo ULA-NURR + Membrete + Badge de Control)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.normpath(os.path.join(base_dir, "..", "..", "prototipo", "img", "logo-ula-nurr-azul.png"))

    if os.path.exists(logo_path):
        logo_element = Image(logo_path, width=1.75 * inch, height=0.62 * inch)
        logo_element.hAlign = 'LEFT'
    else:
        # Fallback de texto si la imagen no se encontrara
        logo_element = Paragraph("<b>ULA - NURR</b><br/><font size=7>Identidad Institucional</font>", inst_title_style)

    center_content = [
        Paragraph("UNIVERSIDAD DE LOS ANDES", inst_title_style),
        Paragraph("NÚCLEO UNIVERSITARIO RAFAEL RANGEL", inst_sub_style),
        Paragraph("UNIDAD DE SOPORTE TÉCNICO | SISTEMA DE CONTROL DE ASISTENCIA", inst_unit_style),
        Spacer(1, 4),
        Paragraph(titulo_reporte, doc_title_style)
    ]

    badge_content = [
        Paragraph("CÓDIGO DE CONTROL", badge_label_style),
        Paragraph(codigo_control, badge_val_style),
        Spacer(1, 2),
        Paragraph(f"Emisión: {timestamp_actual.strftime('%d/%m/%Y %I:%M %p')}", badge_date_style),
        Paragraph("REPORTE OFICIAL AUDITABLE", badge_label_style)
    ]

    badge_table = Table([[badge_content]], colWidths=[146])
    badge_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0F4F8")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#0056B3")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    header_table = Table([
        [logo_element, center_content, badge_table]
    ], colWidths=[138, 432, 150])

    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 5))

    # Barra decorativa institucional azul ULA
    divider = Table([[""]], colWidths=[720], rowHeights=[2.5])
    divider.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#0056B3")),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(divider)
    story.append(Spacer(1, 7))

    # 2. Metadatos del Informe estructurados
    periodo_str = f"{fecha_desde.strftime('%d/%m/%Y') if fecha_desde else 'Inicio'} al {fecha_hasta.strftime('%d/%m/%Y') if fecha_hasta else 'Actual'}"
    depto_str = depto_nombre if depto_nombre else "Todas las dependencias"
    funcionario_str = usuario_nombre if usuario_nombre else "Todos los funcionarios"

    meta_table = Table([
        [
            Paragraph(f"<b>Período:</b> {periodo_str}", meta_style),
            Paragraph(f"<b>Dependencia:</b> {depto_str}", meta_style),
            Paragraph(f"<b>Personal:</b> {funcionario_str}", meta_style),
            Paragraph(f"<b>Registros:</b> {len(asistencias)}", meta_style),
        ]
    ], colWidths=[180, 200, 220, 120])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#D0DCE5")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

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
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0056B3")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#F5F5F5")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))

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
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 24))

    # 5. Sección de Validación y Firma de Coordinación
    firma_data = [
        ["", ""],
        ["_____________________________________________", "_____________________________________________"],
        ["Prof. Coordinador(a) de Soporte Técnico", "Sello Institucional Unidad de Soporte"],
        ["Universidad de Los Andes - NURR", "Constancia Académica y Administrativa"]
    ]
    firma_table = Table(firma_data, colWidths=[360, 360])
    firma_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#424242")),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(KeepTogether([firma_table]))

    def _draw_page_decorations(canvas, d):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#0056B3"))
        canvas.setLineWidth(0.8)
        canvas.line(36, 26, 792 - 36, 26)

        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawString(
            36,
            15,
            f"Universidad de Los Andes - NURR | {codigo_control} | Sistema Integrado de Control de Asistencia"
        )
        canvas.drawRightString(792 - 36, 15, f"Página {d.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_draw_page_decorations, onLaterPages=_draw_page_decorations)
    buffer.seek(0)
    return buffer.getvalue()
