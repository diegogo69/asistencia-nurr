"""Servicio de envío y gestión de correos electrónicos para Asistencia-NURR."""

import sys
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
import logging

from app.core.config import settings

logger = logging.getLogger("asistencia_nurr.email")

# Almacén en memoria de correos salientes (útil para pruebas unitarias y modo de desarrollo)
sent_emails: List[Dict[str, Any]] = []


def is_test_environment() -> bool:
    """Verifica si la ejecución actual corresponde a una prueba automatizada."""
    return "pytest" in sys.modules or os.getenv("PYTEST_CURRENT_TEST") is not None


def mask_email(email: str) -> str:
    """Enmascara un correo electrónico para proteger la privacidad del usuario en respuestas públicas."""
    if not email or "@" not in email:
        return email or ""
    parts = email.split("@", 1)
    user_part = parts[0]
    domain_part = parts[1]
    
    if len(user_part) <= 2:
        masked_user = user_part[0] + "***"
    elif len(user_part) <= 4:
        masked_user = user_part[:2] + "***"
    else:
        masked_user = user_part[:3] + "***" + user_part[-1]
    
    return f"{masked_user}@{domain_part}"


def get_sent_emails() -> List[Dict[str, Any]]:
    """Retorna la lista de correos enviados en memoria."""
    return sent_emails


def clear_sent_emails() -> None:
    """Limpia el almacén en memoria de correos enviados."""
    sent_emails.clear()


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    reset_token: Optional[str] = None
) -> bool:
    """Envía un correo electrónico mediante SMTP o registra la simulación según la configuración."""
    if not settings.EMAILS_ENABLED:
        logger.info(f"[EMAIL DESACTIVADO] Envío omitido para: {to_email}")
        return False

    # Guardar siempre en memoria para trazabilidad y pruebas automatizadas
    email_record = {
        "to": to_email,
        "subject": subject,
        "html": html_content,
        "text": text_content or html_content,
        "reset_token": reset_token
    }
    sent_emails.append(email_record)

    # 1. En pruebas automatizadas (pytest), simular despacho exitoso sin conectar a SMTP
    if is_test_environment():
        return True

    # 2. Modo desarrollo explícito (SMTP_DEV_MODE=True en .env)
    if settings.SMTP_DEV_MODE:
        print(f"\n==================== [SIMULACIÓN CORREO MODO DESARROLLO] ====================")
        print(f" Para:          {to_email}")
        print(f" Asunto:        {subject}")
        print(f" Remitente:     {settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or 'soporte@ula.ve'}>")
        if reset_token:
            print(f" CÓDIGO TOKEN:  {reset_token}")
        print("-----------------------------------------------------------------------------")
        print(text_content or html_content)
        print(f"=============================================================================\n")
        return True

    # 3. Validación de configuración de servidor SMTP real
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(
            f"[EMAIL NO ENVIADO] Servidor SMTP no configurado en .env (SMTP_HOST, SMTP_USER, SMTP_PASSWORD). "
            f"El correo para {to_email} no pudo ser despachado."
        )
        print(f"\n==================== [ADVERTENCIA SERVIDOR SMTP] ====================")
        print(f" No se pudo enviar el correo real a: {to_email}")
        print(f" Motivo: No se han configurado SMTP_HOST, SMTP_USER y SMTP_PASSWORD en el archivo .env")
        if reset_token:
            print(f" Código de recuperación generado: {reset_token}")
            print(f" (Para pruebas sin SMTP configure SMTP_DEV_MODE=true en .env)")
        print(f"======================================================================\n")
        return False

    # 4. Envío real mediante SMTP
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        from_name = settings.SMTP_FROM_NAME or "Sistema de Asistencia ULA-NURR"
        from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        if html_content:
            msg.attach(MIMEText(html_content, "html", "utf-8"))

        if settings.SMTP_SSL or settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12)
            if settings.SMTP_TLS or settings.SMTP_PORT == 587:
                server.ehlo()
                server.starttls()
                server.ehlo()

        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()
        logger.info(f"[EMAIL ENVIADO] Mensaje enviado exitosamente a {to_email}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL ERROR] Error enviando correo a {to_email}: {e}")
        return False


def send_password_reset_email(
    to_email: str,
    nombre_usuario: str,
    reset_token: str,
    expires_minutes: int = 30
) -> bool:
    """Genera y despacha el correo institucional de restablecimiento de contraseña."""
    subject = "Recuperación de Contraseña - Asistencia ULA-NURR"
    
    text_content = f"""UNIVERSIDAD DE LOS ANDES - NÚCLEO UNIVERSITARIO RAFAEL RANGEL
UNIDAD DE SOPORTE TÉCNICO - SISTEMA DE ASISTENCIA

Estimado(a) {nombre_usuario},

Hemos recibido una solicitud para recuperar la contraseña de su cuenta administrativa en el Sistema de Control de Asistencia ULA-NURR.

Su token / código de recuperación es:
{reset_token}

Para restablecer su contraseña, ingrese al sistema e introduzca este código o visite:
/static/login.html?token={reset_token}&mode=recovery

Por motivos de seguridad, este token expirará en {expires_minutes} minutos.

Si usted no solicitó este cambio de contraseña, ignore este mensaje. Su cuenta permanecerá segura.

--
Unidad de Soporte Técnico
Universidad de Los Andes (ULA - NURR)
"""

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }}
        .email-container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-top: 5px solid #002855; }}
        .header {{ background-color: #002855; color: #ffffff; padding: 24px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 20px; letter-spacing: 0.5px; }}
        .header p {{ margin: 6px 0 0; font-size: 13px; color: #90caf9; }}
        .body {{ padding: 30px 25px; line-height: 1.6; font-size: 15px; }}
        .code-box {{ background: #eef2f7; border: 2px dashed #002855; border-radius: 6px; padding: 15px; text-align: center; margin: 25px 0; }}
        .code {{ font-size: 20px; font-weight: bold; letter-spacing: 2px; color: #002855; word-break: break-all; }}
        .btn {{ display: inline-block; background-color: #002855; color: #ffffff !important; text-decoration: none; padding: 12px 24px; border-radius: 5px; font-weight: 600; margin-top: 15px; text-align: center; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #eee; }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <h1>Universidad de Los Andes</h1>
            <p>Núcleo Universitario Rafael Rangel • Unidad de Soporte Técnico</p>
        </div>
        <div class="body">
            <h2>Recuperación de Contraseña</h2>
            <p>Estimado(a) <strong>{nombre_usuario}</strong>,</p>
            <p>Se ha recibido una solicitud para restablecer la contraseña de su cuenta administrativa en el <strong>Sistema de Asistencia ULA-NURR</strong>.</p>
            
            <p>Utilice el siguiente código o token de verificación:</p>
            <div class="code-box">
                <div class="code">{reset_token}</div>
            </div>

            <p style="text-align: center;">
                <a href="/static/login.html?token={reset_token}&mode=recovery" class="btn">Restablecer mi Contraseña</a>
            </p>

            <p style="margin-top: 25px; font-size: 13px; color: #666;">
                ⏳ <strong>Tiempo de validez:</strong> Este enlace y código expirarán en <strong>{expires_minutes} minutos</strong>.
            </p>
            <p style="font-size: 13px; color: #666;">
                🔒 Si usted no realizó esta solicitud, puede desestimar este mensaje. Su contraseña actual continuará siendo válida.
            </p>
        </div>
        <div class="footer">
            Sistema Institucional de Asistencia Automatizada • ULA-NURR Trujillo, Venezuela
        </div>
    </div>
</body>
</html>
"""

    return send_email(to_email, subject, html_content, text_content, reset_token=reset_token)
