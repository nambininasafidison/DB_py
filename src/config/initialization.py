import os
import base64
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.text import tokenizer_from_json
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
from cryptography.fernet import InvalidToken
import config.config as conf

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
                encrypted = f.read()
            data_dir = decrypt_data(encrypted, master_key)
            if not data_dir:
                raise InvalidToken()
            return data_dir
        except InvalidToken:
            print_error("Clé maître invalide pour déchiffrer le répertoire de données.")
            return None
        except Exception as e:
            print_error(f"Erreur lors de la lecture du répertoire de données: {str(e)}")
            return None
    else:
        data_dir = "._" + generate_obfuscated_name()
        os.makedirs(data_dir, exist_ok=True)
        try:
            encrypted = encrypt_data(data_dir, master_key)
            with open(MASTER_CONFIG_FILE, "wb") as f:
                f.write(encrypted)
            return data_dir
        except Exception as e:
            print_error(f"Erreur lors de la création du répertoire de données: {str(e)}")
            return None

def initialize_system():
    master_key = get_master_key()
    if not master_key:
        print_error("Erreur : Clé maître non disponible.")
        return None

    data_dir = get_data_dir(master_key)
    if not data_dir:
        print_error("Erreur : Répertoire de données non disponible.")
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
        # Initialiser les composants principaux
        cache = RedisCache("localhost", 6379)
        replicator = Replicator([], conf.SSL_CERT, conf.SSL_KEY)
        user_manager = UserManager(user_key)
        db_system = DatabaseSystem(key, metadata_key, replicator, cache, user_manager, language=conf.global_language)
        return db_system
    except Exception as e:
        print_error(f"Erreur lors de l'initialisation du système: {str(e)}")
        return None