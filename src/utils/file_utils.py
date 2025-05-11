import os
import platform
import subprocess
import msgpack
from functools import lru_cache

from config.language import LANGUAGES
from utils.logger_utils import print_error
from utils.utils import decrypt_data, encrypt_data
import config.config as conf


def get_obfuscated_name(name, key):
    return read_msgpack(conf.CONFIG["MAPPING_FILE"], key)[name]

def set_immutable(file_path):
    if platform.system() == "Linux":
        try:
            subprocess.run(["chattr", "+i", file_path], check=True)
        except subprocess.CalledProcessError:
            pass

def read_msgpack(file_path, key):
    try:
        if not os.path.exists(file_path):
            return {}
        with open(file_path, "rb") as f:
            encrypted_data = f.read()
        decrypted_data = decrypt_data(encrypted_data, key)
        if decrypted_data is None:
            print_error("Impossible de décrypter les données.")
            return None
        return msgpack.unpackb(decrypted_data, raw=False)
    except Exception as e:
        print_error(LANGUAGES[conf.global_language].get("decryption_failed", "Decryption failed: {error}").format(error=str(e)))
        return None

def write_msgpack(file_path, content, key):
    packed_data = msgpack.packb(content)
    encrypted_data = encrypt_data(packed_data, key)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(encrypted_data)

@lru_cache(maxsize=1000)
def cached_read(file_path, key):
    return read_msgpack(file_path, key)