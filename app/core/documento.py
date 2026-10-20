"""Módulo de utilidades y validación para documentos de identidad venezolanos (Cédula de Identidad).

Formatos permitidos de entrada:
- Solo numérico: 00000000, 12345678
- Prefijo sin separador: v00000000, V12345678, e12345678
- Prefijo con guion: v-00000000, V-12345678, e-12345678
- Decimal con puntos: 00.000.000, 12.345.678
- Prefijo con decimal con puntos: v00.000.000, V12.345.678
- Prefijo con guion y decimal con puntos: v-00.000.000, V-12.345.678

Formato canónico en base de datos:
- v-00000000 / e-00000000 (prefijo en minúsculas + '-' + número sin puntos)

Rango válido para usuarios:
- 1.000.000 al 99.999.999 (más 00000000 reservado para administración raíz)
"""

import re
from typing import Tuple

DOCUMENTO_REGEX = re.compile(
    r"^(?P<prefix>[vVeE])?\s*[-]?\s*(?P<number>[0-9\.]+)$"
)

def parse_documento_identidad(val: str, default_prefix: str = "v") -> Tuple[str, str]:
    """Parsea un documento de identidad venezolano en (prefijo, numero_sin_puntos)."""
    if not val or not isinstance(val, str):
        raise ValueError("El documento de identidad es requerido y debe ser una cadena de texto.")
    
    val_clean = val.strip()
    match = DOCUMENTO_REGEX.match(val_clean)
    if not match:
        raise ValueError(
            "Formato de documento de identidad no reconocido. "
            "Debe ser numérico o tener prefijo V o E (ej: 12345678, V-12345678, 12.345.678)."
        )
    
    prefix = (match.group("prefix") or default_prefix).lower()
    raw_number = match.group("number").replace(".", "")
    
    if not raw_number.isdigit():
        raise ValueError("El documento de identidad debe contener únicamente caracteres numéricos.")
    
    return prefix, raw_number


def format_documento_identidad(val: str, default_prefix: str = "v") -> str:
    """Valida y normaliza un documento de identidad al formato canónico de base de datos (ej: 'v-12345678').
    
    Valida que el número esté dentro del rango 1000000 al 99999999,
    o sea el identificador '00000000' reservado para el administrador institucional.
    """
    prefix, raw_number = parse_documento_identidad(val, default_prefix=default_prefix)
    
    num_val = int(raw_number)
    
    if num_val == 0:
        # Documento institucional de administración raíz
        formatted_num = "00000000"
    elif 1000000 <= num_val <= 99999999:
        formatted_num = str(num_val)
    else:
        raise ValueError(
            f"El número de documento de identidad ({num_val}) se encuentra fuera del rango permitido "
            f"(1000000 a 99999999)."
        )
    
    return f"{prefix}-{formatted_num}"


def is_valid_documento_identidad(val: str) -> bool:
    """Verifica si un documento tiene formato y rango válidos."""
    try:
        format_documento_identidad(val)
        return True
    except (ValueError, TypeError):
        return False
