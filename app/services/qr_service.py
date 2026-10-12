import io
import uuid
from typing import Tuple
import qrcode
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

from app.models.usuario import Usuario

def generate_unique_qr_code(db: Session, prefix: str = "ULA") -> str:
    """Genera un hash/código de credencial QR 100% único sin colisiones en la tabla usuarios."""
    while True:
        token = f"{prefix}-{uuid.uuid4().hex[:12].upper()}"
        exists = db.query(Usuario).filter(Usuario.codigo_qr == token).first()
        if not exists:
            return token

def generate_qr_image_bytes(qr_data: str) -> bytes:
    """Genera los bytes en formato PNG de la matriz bidimensional del código QR."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def generate_credencial_pdf(usuario: Usuario) -> bytes:
    """Genera un carnet / credencial institucional imprimible en PDF con membrete oficial y código QR."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Dimensiones del carnet institucional (3.5 x 2.25 pulgadas, centrado)
    card_width = 3.6 * inch
    card_height = 5.2 * inch
    page_w, page_h = letter
    x = (page_w - card_width) / 2
    y = (page_h - card_height) / 2

    # Fondo y borde del carnet
    c.setStrokeColor(colors.HexColor("#0D47A1"))  # Azul institucional ULA
    c.setLineWidth(2)
    c.roundRect(x, y, card_width, card_height, 10, stroke=1, fill=0)

    # Franja superior (Header)
    header_height = 0.9 * inch
    c.setFillColor(colors.HexColor("#0D47A1"))
    c.roundRect(x, y + card_height - header_height, card_width, header_height, 8, stroke=0, fill=1)

    # Texto encabezado
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(x + card_width / 2, y + card_height - 0.3 * inch, "UNIVERSIDAD DE LOS ANDES")
    c.setFont("Helvetica", 8)
    c.drawCentredString(x + card_width / 2, y + card_height - 0.5 * inch, "NÚCLEO UNIVERSITARIO RAFAEL RANGEL")
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(x + card_width / 2, y + card_height - 0.75 * inch, "UNIDAD DE SOPORTE TÉCNICO")

    # Título de Credencial
    c.setFillColor(colors.HexColor("#1A237E"))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(x + card_width / 2, y + card_height - 1.2 * inch, "CREDENCIAL DE ASISTENCIA")

    # Renderizar Código QR en el centro
    if usuario.codigo_qr:
        qr_bytes = generate_qr_image_bytes(usuario.codigo_qr)
        qr_image = ImageReader(io.BytesIO(qr_bytes))
        qr_size = 2.0 * inch
        qr_x = x + (card_width - qr_size) / 2
        qr_y = y + card_height - 3.4 * inch
        c.drawImage(qr_image, qr_x, qr_y, width=qr_size, height=qr_size)

    # Datos del Usuario
    c.setFillColor(colors.HexColor("#212121"))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(x + card_width / 2, y + 1.5 * inch, usuario.nombre_completo.upper())

    c.setFont("Helvetica", 9)
    c.drawCentredString(x + card_width / 2, y + 1.25 * inch, f"Cédula: {usuario.documento_identidad}")

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#0D47A1"))
    rol_nombre = usuario.rol.nombre if usuario.rol else "Personal"
    c.drawCentredString(x + card_width / 2, y + 1.0 * inch, rol_nombre.upper())

    depto_nombre = usuario.departamento.nombre if usuario.departamento else "Soporte Técnico"
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#616161"))
    c.drawCentredString(x + card_width / 2, y + 0.75 * inch, depto_nombre)

    # Pie de carnet
    c.setFont("Helvetica-Oblique", 7)
    c.setFillColor(colors.HexColor("#757575"))
    c.drawCentredString(x + card_width / 2, y + 0.3 * inch, "Presente este carnet en el punto de marcación")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
