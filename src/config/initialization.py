import os
import json
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.text import tokenizer_from_json

import config.config as conf
from config.config import MASTER_CONFIG_FILE
from core.cache import RedisCache
from core.database_system import DatabaseSystem
from core.replication import Replicator
from managers.user_manager import UserManager
from utils.logger_utils import print_error, print_response
from utils.utils import decrypt_data, encrypt_data, generate_obfuscated_name, get_master_key
from query.nlp_model import nlp_model
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64
from cryptography.fernet import InvalidToken

DATA_KEY_SALT = "data_key_salt"
METADATA_KEY_SALT = "metadata_key_salt"
USER_KEY_SALT = "user_key_salt"

def derive_key(master_key, salt, key_name):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt.encode(),
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(master_key))
    return key

def get_data_dir(master_key):
    if os.path.exists(MASTER_CONFIG_FILE):
        try:
            with open(MASTER_CONFIG_FILE, "rb") as f:
                encrypted_data = f.read()
            data_dir = decrypt_data(encrypted_data, master_key)
            if data_dir is None:
                print_error("Échec du déchiffrement de MASTER_CONFIG_FILE.")
                return None
            os.makedirs(data_dir, exist_ok=True)
            return data_dir
        except InvalidToken:
            print_error("Le jeton de décryptage est invalide.")
            return None
        except Exception as e:
            print_error(f"Erreur lors du déchiffrement de MASTER_CONFIG_FILE. {str(e)}")
            return None
    else:
        data_dir = "._" + generate_obfuscated_name()
        os.makedirs(data_dir, exist_ok=True)
        try:
            with open(MASTER_CONFIG_FILE, "wb") as f:
                f.write(encrypt_data(data_dir, master_key))
            return data_dir
        except Exception as e:
            print_error(f"Erreur lors de la création de MASTER_CONFIG_FILE. {str(e)}")
            return None

def initialize_system():
    master_key = get_master_key()
    if not master_key:
        print("Erreur : Clé maître non disponible.")
        return None

    data_dir = get_data_dir(master_key)
    if not data_dir:
        print("Erreur : Répertoire de données non disponible.")
        return None

    conf.CONFIG.update({
        "BACKUP_DIR": os.path.join(data_dir, ".backups"),
        "AUDIT_LOG": os.path.join(data_dir, "audit.log"),
        "USER_FILE": os.path.join(data_dir, "users.msgpack"),
        "USER_KEY_FILE": os.path.join(data_dir, "user_key"),
        "MAPPING_FILE": os.path.join(data_dir, "cfg.dat"),
        "HISTORY_FILE": os.path.join(data_dir, "history"),
        "TOKENIZER": os.path.join(data_dir, "tokenizer.json"),
        "SQL_MAPPING": os.path.join(data_dir, "sql_mapping.json"),
        "DATA_DIR": data_dir
    })

    try:
        # Dériver les clés à partir de la clé maître
        key = derive_key(master_key, DATA_KEY_SALT, "data_key")
        metadata_key = derive_key(master_key, METADATA_KEY_SALT, "metadata_key")
        user_key = derive_key(master_key, USER_KEY_SALT, "user_key")

        try:
            replicator = Replicator(
                nodes=[("localhost", 5000), ("localhost", 5001)],
                ssl_cert=conf.SSL_CERT,
                ssl_key=conf.SSL_KEY
            )
        except Exception as e:
            print_error(f"Failed to initialize replicator: {str(e)}")
            replicator = None

        try:
            cache = RedisCache("localhost", 6379)
        except Exception as e:
            print_error(f"Failed to initialize Redis cache: {str(e)}")
            cache = None

        user_manager = UserManager(user_key)
        db_system = DatabaseSystem(key, metadata_key, replicator, cache, user_manager)
        db_system.backup_manager.schedule_backups(interval_hours=24)

        print_response("Système initialisé avec prise en charge SSL.", "info")

        model_path = os.path.join(conf.CONFIG["DATA_DIR"], "model.h5")
        if os.path.exists(model_path):
            nlp_model.model = load_model(model_path)
            with open(conf.CONFIG["TOKENIZER"], "r") as f:
                tokenizer_json = f.read()
                nlp_model.tokenizer = tokenizer_from_json(tokenizer_json)
            with open(conf.CONFIG["SQL_MAPPING"], "r") as f:
                nlp_model.sql_to_index = json.load(f)

        return db_system
    except Exception as e:
        print_error(f"Erreur : L'initialisation du système a échoué. {str(e)}")
        return None