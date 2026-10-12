import ipaddress
from typing import Optional
from sqlalchemy.orm import Session
from app.models.red import RedAutorizada

def validate_ip_or_cidr(value: str) -> bool:
    """Valida si una cadena es una dirección IP válida (IPv4/IPv6) o un bloque CIDR válido."""
    try:
        ipaddress.ip_network(value.strip(), strict=False)
        return True
    except ValueError:
        return False

def is_ip_authorized(client_ip: str, db: Session) -> bool:
    """Comprueba si la IP cliente coincide con alguna de las reglas activas en la lista blanca de redes_autorizadas."""
    if not client_ip:
        return False

    try:
        client_addr = ipaddress.ip_address(client_ip.strip())
    except ValueError:
        return False

    reglas_activas = db.query(RedAutorizada).filter(RedAutorizada.activo == True).all()

    for regla in reglas_activas:
        try:
            network = ipaddress.ip_network(regla.direccion_ip.strip(), strict=False)
            if client_addr in network:
                return True
        except ValueError:
            continue

    return False
