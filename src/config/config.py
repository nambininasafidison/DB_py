import os
from config.language import LANGUAGES  # Ajout de l'import LANGUAGES

MASTER_CONFIG_FILE = "data_dir.cfg"
MASTER_KEY_FILE = "master.key"
CONFIG = {}
global_language = "en"
SSL_CERT = os.path.join(os.path.dirname(__file__), "server.pem")
SSL_KEY = os.path.join(os.path.dirname(__file__), "server.key")