import json
import os
from datetime import datetime, timezone

def read_config(executable_dir):
    try:
        config_file = os.path.join(executable_dir, os.getenv("CONFIG_FILE"))
        print(config_file)
        with open(config_file, "r") as f:
            config = json.load(f)
            return config
    except Exception as e:
        print("Error: ", e)
        return None
