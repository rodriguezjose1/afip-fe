# Datos de autenticación
import os

from dotenv import load_dotenv
import zeep
from auth import validate_token_and_update
from constants import cuit

from zeep.wsse.username import UsernameToken

env_path = ".env_" + os.getenv("ENV")

load_dotenv(dotenv_path=env_path)


def get_tipos_comp():
    # Configura el cliente de SOAP con la URL del WSDL
    wsdl = os.getenv("WSDL")  # URL de homologación
    token, sign = validate_token_and_update()

    client = zeep.Client(wsdl=wsdl)

    auth = {
        "Token": token,
        "Sign": sign,
        "Cuit": cuit,
    }

    # Realiza la consulta
    try:
        response = client.service.FEParamGetTiposCbte(Auth=auth)

        print(response)
        # Imprimir los resultados
        for tipo in response.ResultGet.CbteTipo:
            print(f"Tipo de Comprobante: {tipo.Id}, Descripción: {tipo.Desc}")

    except zeep.exceptions.Error as e:
        print(f"Error al consultar el estado de la factura: {e}")


get_tipos_comp()
