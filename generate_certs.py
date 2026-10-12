"""Script para generar certificados SSL/TLS autofirmados locales válidos para
desarrollo y red local (LAN) en Windows, permitiendo acceso seguro por HTTPS y
habilitando el uso de la cámara web (getUserMedia) sin bloqueos del navegador.
"""

import os
import socket
import ipaddress
from datetime import datetime, timedelta, timezone

def get_local_ips():
    ips = {"127.0.0.1"}
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            ips.add(ip)
    except Exception:
        pass
    return list(ips)

def generate_self_signed_cert(cert_dir="certs", cert_file="cert.pem", key_file="key.pem"):
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        print("[!] La librería 'cryptography' no está instalada. Ejecute 'pip install cryptography'.")
        return False

    os.makedirs(cert_dir, exist_ok=True)
    cert_path = os.path.join(cert_dir, cert_file)
    key_path = os.path.join(cert_dir, key_file)

    if os.path.exists(cert_path) and os.path.exists(key_path):
        print(f"[i] Los certificados ya existen en: {cert_dir}/")
        return True

    print("[*] Generando clave privada RSA de 2048 bits...")
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "VE"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Trujillo"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Trujillo"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Universidad de los Andes - NURR"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Soporte Tecnico"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Asistencia-NURR Local LAN"),
    ])

    alt_names = [
        x509.DNSName("localhost"),
        x509.DNSName(socket.gethostname()),
    ]

    for ip_str in get_local_ips():
        try:
            alt_names.append(x509.IPAddress(ipaddress.ip_address(ip_str)))
        except ValueError:
            pass

    print(f"[*] Asignando nombres alternativos (SAN): {[str(n.value) for n in alt_names]}")

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365 * 3))
        .add_extension(
            x509.SubjectAlternativeName(alt_names),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )

    with open(key_path, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"[+] Certificados generados exitosamente:")
    print(f"    - Clave privada: {key_path}")
    print(f"    - Certificado:   {cert_path}")
    return True

if __name__ == "__main__":
    generate_self_signed_cert()
