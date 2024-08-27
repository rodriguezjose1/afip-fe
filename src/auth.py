from datetime import datetime, timedelta
import os
from zeep import Client
import json
from dateutil.tz import tzlocal, tzutc
from base64 import b64encode
from dotenv import load_dotenv

from suds.client import Client
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding
from asn1crypto import cms, algos, x509 as asn1_x509

import xml.etree.ElementTree as ET

import sys

if getattr(sys, 'frozen', False):
    # Si se está ejecutando como un ejecutable generado por PyInstaller
    executable_dir = os.path.dirname(sys.executable)
    internal_executable_dir = sys._MEIPASS
else:
    # Si se está ejecutando desde el código fuente
    executable_dir = os.path.dirname(os.path.abspath(__file__))
    internal_executable_dir = executable_dir

env_path = os.path.join(internal_executable_dir, ".env_" + os.getenv("ENV"))

load_dotenv(dotenv_path=env_path)

service_afip = os.getenv("SERVICE")
print("service", service_afip)
cert_file_path = os.getenv("CERT_FILE")
key_file_path = os.getenv("KEY_FILE")
login_url = os.getenv("LOGIN_URL")
archivo_auth_data = os.getenv("AUTH_DATA")

# Tiempo máximo de validez del token en minutos
TIEMPO_MAXIMO = os.getenv("TIEMPO_MAXIMO")


def read_auth_data():
    try:
        with open(os.path.join(executable_dir, archivo_auth_data), "r") as f:
            datos = json.load(f)
            return datos
    except FileNotFoundError:
        print("El archivo 'auth_data.json' no se encontró.")
        return None
    except json.JSONDecodeError:
        print("Error al decodificar el archivo JSON.")
        return None
    except Exception as e:
        print("Error: ", e)
        return None


def validate_token_and_update():
    datos = read_auth_data()

    if datos is None:
        print("No se encontraron datos de autenticación.")
        return get_login_ticket()

    fecha_guardada_str = datos.get("date")
    if fecha_guardada_str is None:
        print("No se encontró la fecha en los datos.")
        return get_login_ticket()

    fecha_guardada = datetime.strptime(fecha_guardada_str, "%Y-%m-%d %H:%M:%S")
    fecha_actual = datetime.now()

    if fecha_actual - fecha_guardada > timedelta(minutes=int(TIEMPO_MAXIMO)):
        print("El token ha expirado. Generando un nuevo token...")
        return get_login_ticket()

    print("Token y sign válidos.")
    return datos.get("token"), datos.get("sign")


def create_tra(service, ttl=300):
    tz = tzutc()
    now = datetime.now(tz).replace(microsecond=0)
    trans_id = str(int(now.timestamp()))
    expiration = now + timedelta(seconds=ttl)

    print("generationTime: ", now.isoformat())
    print("expirationTime: ", expiration.isoformat())

    tra = f"""<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
    <header>
        <uniqueId>{trans_id}</uniqueId>
        <generationTime>{now.isoformat()}</generationTime>
        <expirationTime>{expiration.isoformat()}</expirationTime>
    </header>
    <service>{service}</service>
</loginTicketRequest>"""

    return tra


def sign_tra(tra, cert_file, key_file_path):
    # Leer certificado y clave privada
    with open(os.path.join(executable_dir, cert_file), "rb") as f:
        cert_data = f.read()
        cert = x509.load_pem_x509_certificate(cert_data)

    with open(os.path.join(executable_dir, key_file_path), "rb") as f:
        key_data = f.read()
        private_key = load_pem_private_key(key_data, password=None)

    # Convertir el certificado a DER y luego cargarlo con asn1crypto
    cert_der = cert.public_bytes(Encoding.DER)
    asn1_cert = asn1_x509.Certificate.load(cert_der)

    # Firmar el TRA
    signature = private_key.sign(tra.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())

    # Crear la estructura CMS
    signed_data = cms.SignedData(
        {
            "version": "v1",
            "digest_algorithms": [algos.DigestAlgorithm({"algorithm": "sha256"})],
            "encap_content_info": {"content_type": "data", "content": tra.encode("utf-8")},
            "certificates": [asn1_cert],
            "signer_infos": [
                cms.SignerInfo(
                    {
                        "version": "v1",
                        "sid": cms.SignerIdentifier(
                            {
                                "issuer_and_serial_number": cms.IssuerAndSerialNumber(
                                    {"issuer": asn1_cert.issuer, "serial_number": asn1_cert.serial_number}
                                )
                            }
                        ),
                        "digest_algorithm": algos.DigestAlgorithm({"algorithm": "sha256"}),
                        "signature_algorithm": algos.SignedDigestAlgorithm({"algorithm": "rsassa_pkcs1v15"}),
                        "signature": signature,
                    }
                )
            ],
        }
    )

    # Envolver en ContentInfo
    content_info = cms.ContentInfo({"content_type": "signed_data", "content": signed_data})

    # Codificar en DER y luego en base64
    der_bytes = content_info.dump()
    return b64encode(der_bytes).decode("utf-8")


def call_wsaa(tra, login_url):
    client = Client(login_url)
    return client.service.loginCms(tra)


def handle_error_and_get_ta(e):
    # Verificar si el error es el que indica que ya existe un TA válido
    if "El CEE ya posee un TA valido para el acceso al WSN solicitado" in str(e):
        datos = read_auth_data()
        return datos
    else:
        raise e


def get_login_ticket():
    tra = create_tra(service_afip)
    signed_tra = sign_tra(tra, cert_file_path, key_file_path)

    try:
        response = call_wsaa(signed_tra, login_url)
    except Exception as e:
        print(e)
        datos = handle_error_and_get_ta(e)
        if datos is None:
            return None
        print("Token y sign recuperados de 'auth_data.json'.")
        return datos.get("token"), datos.get("sign")

    # Parsear la respuesta XML
    root = ET.fromstring(response)
    token = root.find(".//token").text
    sign = root.find(".//sign").text

    print(f"Token: {token}")
    print(f"Sign: {sign}")

    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    datos = {"token": token, "sign": sign, "date": fecha_actual}

    # Escribir en el archivo JSON
    with open(os.path.join(executable_dir, archivo_auth_data), "w") as f:
        json.dump(datos, f, indent=4)

    print("Token y sign guardados en 'auth_data.json'.")

    return token, sign
