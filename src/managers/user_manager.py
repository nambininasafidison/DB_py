import os
import hashlib
import config.config as conf
from config.language import LANGUAGES
from cryptography.fernet import Fernet, InvalidToken
from utils.logger_utils import print_error, print_success
import json

class UserManager:
    def __init__(self, key):
        self.key = key
        self.users = self._load_users()

    def _load_users(self):
        user_file = conf.CONFIG["USER_FILE"]
        if not os.path.exists(user_file):
            return {}
        try:
            with open(user_file, "rb") as f:
                encrypted = f.read()
            fernet = Fernet(self.key)
            decrypted = fernet.decrypt(encrypted)
            users = json.loads(decrypted.decode())
            return users
        except InvalidToken:
            print_error("Clé utilisateur invalide.")
            return {}
        except Exception as e:
            print_error(f"Erreur lors du chargement des utilisateurs: {str(e)}")
            return {}

    def _save_users(self):
        user_file = conf.CONFIG["USER_FILE"]
        try:
            fernet = Fernet(self.key)
            data = json.dumps(self.users).encode()
            encrypted = fernet.encrypt(data)
            with open(user_file, "wb") as f:
                f.write(encrypted)
        except Exception as e:
            print_error(f"Erreur lors de la sauvegarde des utilisateurs: {str(e)}")

    def user_exists(self, username):
        return username in self.users

    def create_user(self, username, password, role="user", caller_role="user"):
        if caller_role != "admin" and username != "admin":
            print_error("Seul un administrateur peut créer un utilisateur.")
            return
        if username in self.users:
            print_error("Utilisateur déjà existant.")
            return
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        self.users[username] = {
            "username": username,
            "password": hashed_password,
            "role": role,
            "permissions": {}
        }
        self._save_users()
        print_success(LANGUAGES[conf.global_language]["user_created"].format(username=username))

    def alter_user(self, username, new_password=None, new_role=None, caller_role="user"):
        if caller_role != "admin":
            print_error("Seul un administrateur peut modifier un utilisateur.")
            return
        if username not in self.users:
            print_error("Utilisateur inexistant.")
            return
        if new_password:
            self.users[username]["password"] = hashlib.sha256(new_password.encode()).hexdigest()
        if new_role:
            self.users[username]["role"] = new_role
        self._save_users()
        print_success(LANGUAGES[conf.global_language]["user_altered"].format(username=username))

    def drop_user(self, username, caller_role="user"):
        if caller_role != "admin":
            print_error("Seul un administrateur peut supprimer un utilisateur.")
            return
        if username not in self.users:
            print_error("Utilisateur inexistant.")
            return
        del self.users[username]
        self._save_users()
        print_success(LANGUAGES[conf.global_language]["user_dropped"].format(username=username))

    def grant(self, username, db, table, permissions, caller_role="user"):
        if caller_role != "admin":
            print_error("Seul un administrateur peut accorder des privilèges.")
            return
        if username not in self.users:
            print_error("Utilisateur inexistant.")
            return
        self.users[username]["permissions"][f"{db}.{table}"] = permissions
        self._save_users()

    def revoke(self, username, db, table, permissions, caller_role="user"):
        if caller_role != "admin":
            print_error("Seul un administrateur peut révoquer des privilèges.")
            return
        if username not in self.users:
            print_error("Utilisateur inexistant.")
            return
        if f"{db}.{table}" in self.users[username]["permissions"]:
            del self.users[username]["permissions"][f"{db}.{table}"]
        self._save_users()

    def grant_all_privileges(self, username, caller_role="user"):
        if caller_role != "admin":
            print_error("Seul un administrateur peut accorder tous les privilèges.")
            return
        if username not in self.users:
            print_error("Utilisateur inexistant.")
            return
        self.users[username]["permissions"]["ALL"] = True
        self._save_users()

    def revoke_all_privileges(self, username, caller_role="user"):
        if caller_role != "admin":
            print_error("Seul un administrateur peut révoquer tous les privilèges.")
            return
        if username not in self.users:
            print_error("Utilisateur inexistant.")
            return
        self.users[username]["permissions"] = {}
        self._save_users()

    def authenticate(self, username, password):
        if username not in self.users:
            return None
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        if self.users[username]["password"] == hashed_password:
            return self.users[username]
        return None