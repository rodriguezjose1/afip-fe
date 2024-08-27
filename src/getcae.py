from datetime import datetime
import sys
from zeep import Client
from zeep.transports import Transport
from requests import Session

from auth import validate_token_and_update

from constants import getConfig

config = {}

def get_client(wsdl):
    session = Session()
    session.verify = False  # Deshabilita la verificación SSL (solo para pruebas)
    transport = Transport(session=session)
    return Client(wsdl=wsdl, transport=transport)


def get_last_proof(client, auth, ptoVta, cbteTipo):
    ultimo_comprobante = client.service.FECompUltimoAutorizado(
        Auth=auth,
        PtoVta=int(ptoVta),
        CbteTipo=int(cbteTipo),
    )
    return ultimo_comprobante.CbteNro


def write_result(status_code, message, err=""):
    # Escribe el estado y el mensaje en output.txt
    with open(config.get("output_file"), "w") as f:
        f.write(f"{status_code},")
        f.write(f"{message},")
        f.write(f"{err}")


def get_date_format_AAAAMMDD():
    return datetime.now().strftime("%Y%m%d")


def calcular_imp_iva(tipo_comprobante, importe_total, tasa_iva=0.21):
    # Inicializar los valores
    imp_neto = 0.00
    imp_iva = 0.00
    iva_detalle = []

    # Calcula el importe neto y el IVA en función de si el IVA está incluido o no
    if tipo_comprobante in ["1", "2", "3", "6", "7", "8"]:
        imp_neto = float(importe_total) / (1 + tasa_iva)
        imp_iva = float(importe_total) - imp_neto
        iva_detalle = {
            "AlicIva": [
                {
                    "Id": 5,  # Identificador del IVA general (ID según AFIP)
                    "BaseImp": round(imp_neto, 2),
                    "Importe": round(imp_iva, 2),
                }
            ]
        }
    else:
        return None

    return {
        "ImpNeto": round(imp_neto, 2),
        "ImpIVA": round(imp_iva, 2),
        "Iva": iva_detalle,
    }


def call_get_cae(factura, cuit, ptoVta, cbteTipo, impTotal, asocPtoVta, asocCbteTipo, asocCbteNro, asocCbteFch):
    try:
        token, sign = validate_token_and_update()
        client = get_client(config.get("wsdl"))

        auth = {"Token": token, "Sign": sign, "Cuit": cuit}

        ultimo_numero = get_last_proof(client, auth, ptoVta, cbteTipo)

        nuevo_numero = int(ultimo_numero) + 1

        factura["FeCabReq"]["PtoVta"] = ptoVta
        factura["FeCabReq"]["CbteTipo"] = cbteTipo

        factura["FeDetReq"]["FECAEDetRequest"][0]["CbteDesde"] = nuevo_numero
        factura["FeDetReq"]["FECAEDetRequest"][0]["CbteHasta"] = nuevo_numero
        factura["FeDetReq"]["FECAEDetRequest"][0]["CbteFch"] = get_date_format_AAAAMMDD()

        factura["FeDetReq"]["FECAEDetRequest"][0]["ImpTotal"] = float(impTotal)

        iva_data = calcular_imp_iva(cbteTipo, impTotal)

        if iva_data is not None:
            factura["FeDetReq"]["FECAEDetRequest"][0].update(iva_data)

        if cbteTipo in ["2", "3", "7", "8"]:
            # ver observaciones RI factura A
            factura["FeDetReq"]["FECAEDetRequest"][0]["CbtesAsoc"] = [
                {
                    "CbteAsoc": {
                        "PtoVta": asocPtoVta,
                        "CbteFch": asocCbteFch,
                        "Nro": asocCbteNro,
                        "Tipo": asocCbteTipo,
                    },
                }
            ]

        print(factura)

        result = client.service.FECAESolicitar(Auth={"Token": token, "Sign": sign, "Cuit": cuit}, FeCAEReq=factura)

        print(result)
        # Procesar la respuesta
        if result.FeCabResp.Resultado == "A":
            print(f"Factura autorizada. CAE: {result.FeDetResp.FECAEDetResponse[0].CAE}")

            write_result(1, result.FeDetResp.FECAEDetResponse[0].CAE, result.FeDetResp.FECAEDetResponse[0].CAEFchVto)
        else:
            for obs in result.FeDetResp.FECAEDetResponse[0].Observaciones.Obs:
                print(f"Error: {obs.Msg}")
                write_result(0, "Factura no autorizada", obs.Msg)

    except Exception as error:
        # Captura cualquier otro tipo de excepción
        print(type(error))
        write_result(0, "ERROR", str(error))
        print(f"An unexpected error occurred: {str(error)}")


def get_cae(factura):
    # if len(sys.argv) < 5:
    #     print("Requerido: CUIT, Punto de Venta, Cbte. Tipo, Cbte. Nro.")
    #     return

    config.update(getConfig())

    if config is None:
        print("Error: No se pudo leer el archivo de configuración.")
        return

    cuit = config["cuit"]
    # cuit = sys.argv[2]
    ptoVta = sys.argv[2]
    cbteTipo = sys.argv[3]
    impTotal = sys.argv[4]

    asocPtoVta = None
    asocCbteTipo = None
    asocCbteNro = None
    asocCbteFch = None

    if len(sys.argv) > 6:
        asocPtoVta = sys.argv[5]
        asocCbteTipo = sys.argv[6]
        asocCbteNro = sys.argv[7]
        asocCbteFch = sys.argv[8]

    call_get_cae(factura, cuit, ptoVta, cbteTipo, impTotal, asocPtoVta, asocCbteTipo, asocCbteNro, asocCbteFch)
