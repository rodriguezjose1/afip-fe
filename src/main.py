import os
import sys

from getcae import get_cae
from verify import verify
from utils_fn import read_config

from constants import factura, setConfig, getConfig

from dotenv import load_dotenv
import os


def main():
    if getattr(sys, 'frozen', False):
    # Si se está ejecutando como un ejecutable generado por PyInstaller
        internal_executable_dir = sys._MEIPASS
        executable_dir = os.path.dirname(sys.executable)
    else:
        # Si se está ejecutando desde el código fuente
        executable_dir = os.path.dirname(os.path.abspath(__file__))
        internal_executable_dir = executable_dir

    config = read_config(executable_dir)

    if config is None:
        print("Error: No se pudo leer el archivo de configuración.")
        return

    env = config["env"]

    env_path = os.path.join(internal_executable_dir, ".env_" + env)

    load_dotenv(dotenv_path=env_path)

    config["output_file"] = os.path.join(executable_dir, os.getenv("OUTPUT"))
    config["wsdl"] = os.getenv("WSDL")
    config["executable_dir"] = executable_dir
    config["internal_executable_dir"] = internal_executable_dir

    setConfig(config)

    if env is None:
        print("Por favor, especifica el ambiente")
        sys.exit(1)

    # Verifica si se ha proporcionado un argumento
    if len(sys.argv) < 2:
        print("Por favor, especifica el script")
        sys.exit(1)

    # Captura el argumento
    script = sys.argv[1]

    # Ejecuta la función correspondiente
    if script == "getcae":
        get_cae(factura)
    elif script == "verify":
        verify()
    else:
        print(f"'{script}' no es un script válido.")
        sys.exit(1)


if __name__ == "__main__":
    main()
