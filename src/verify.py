import zeep
import sys
import os

from auth import validate_token_and_update
from constants import getConfig

config = {}

def verificar_cae(cuit, pto_vta, cbte_tipo, cbte_nro):
    # Configura el cliente de SOAP con la URL del WSDL
    wsdl = config.get("wsdl")
    client = zeep.Client(wsdl=wsdl)

    token, sign = validate_token_and_update()

    # Define los parámetros de autenticación
    auth = {
        "Token": token,
        "Sign": sign,
        "Cuit": cuit,
    }

    # Realiza la consulta
    try:
        response = client.service.FECompConsultar(
            Auth=auth,
            FeCompConsReq={
                "PtoVta": pto_vta,
                "CbteTipo": cbte_tipo,
                "CbteNro": cbte_nro,
            },
        )

        print(response)
        # Maneja la respuesta
        if response.ResultGet.Resultado == "A":
            coda = response.ResultGet.CodAutorizacion
            cae_fch_vto = response.ResultGet.FchVto
            print(f"Factura autorizada con Codigo de Autorización: {coda}, Fecha de vencimiento: {cae_fch_vto}")
        else:
            print(f"Factura no autorizada. Motivo: {response.Errors.Err[0].Msg}")

    except zeep.exceptions.Error as e:
        print(f"Error al consultar el estado de la factura: {e}")


def verify():
    if len(sys.argv) < 5:
        print("Requerido: CUIT, Punto de Venta, Cbte. Tipo, Cbte. Nro.")
        return

    config.update(getConfig())

    if config is None:
        print("Error: No se pudo leer el archivo de configuración.")
        return

    cuit = config["cuit"]

    ptoVta = sys.argv[2]
    cbteTipo = sys.argv[3]
    cbteNro = sys.argv[4]

    verificar_cae(cuit, ptoVta, cbteTipo, cbteNro)
