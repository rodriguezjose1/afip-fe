factura = {
    "FeCabReq": {
        "CantReg": 1,
        # "PtoVta": 1,
        # "CbteTipo": 6,
    },
    "FeDetReq": {
        "FECAEDetRequest": [
            {
                "Concepto": 1,  # Productos
                "DocTipo": 99,  # CUIT
                "DocNro": "0",  # CUIT del cliente
                "ImpTotConc": 0,
                "ImpOpEx": 0,
                "ImpTrib": 0,
                "MonId": "PES",  # Pesos argentinos
                "MonCotiz": 1,
            }
        ]
    },
}

config = {}

def setConfig(update):
    config.update(update)

def getConfig():
    return config
