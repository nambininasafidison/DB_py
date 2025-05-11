import os
import hashlib
import uuid
from cryptography.fernet import Fernet, InvalidToken
from config.config import MASTER_KEY_FILE
import config.config as conf
from utils.logger_utils import print_error

def generate_key():
    return Fernet.generate_key()

def get_master_key():
    if os.path.exists(MASTER_KEY_FILE):
        try:
            with open(MASTER_KEY_FILE, "rb") as f:
                return f.read()
        except Exception as e:
            print_error(f"Erreur de lecture de la clé maître. {str(e)}")
            return None
    else:
        mk = generate_key()
        try:
            with open(MASTER_KEY_FILE, "wb") as f:
                f.write(mk)
            with open(MASTER_KEY_FILE + ".backup", "wb") as f:
                f.write(mk)
            return mk
        except Exception as e:
            print_error(f"Erreur lors de la génération de la clé maître. {str(e)}")
            return None

def encrypt_data(data, key):
    fernet = Fernet(key)
    if isinstance(data, str):
        data = data.encode()
    return fernet.encrypt(data)

def decrypt_data(data, key):
    fernet = Fernet(key)
    try:
        decrypted_data = fernet.decrypt(data)
        try:
            return decrypted_data.decode()
        except UnicodeDecodeError:
            return decrypted_data
    except InvalidToken:
        print_error("Le jeton de décryptage est invalide.")
        return None
    except Exception as e:
        print_error(f"Erreur de décryptage: {str(e)}")
        return None

def generate_obfuscated_name():
    return hashlib.sha256(uuid.uuid4().bytes).hexdigest()

def load_key(filename):
    if not os.path.exists(filename):
        print_error(f"Key file {filename} not found.")
        return None
    try:
        with open(filename, "rb") as f:
            return f.read()
    except Exception as e:
        print_error(f"Error reading key file {filename}: {str(e)}")
        return None