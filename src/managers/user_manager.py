import os
import hashlib
import msgpack
import numpy as np
from cryptography.fernet import Fernet, InvalidToken

import config.config as conf
from config.language import LANGUAGES
from utils.logger_utils import print_error, print_response, print_success

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
                encrypted_data = f.read()
            decrypted_data = Fernet(self.key).decrypt(encrypted_data)
            return msgpack.unpackb(decrypted_data, raw=False)
        except InvalidToken:
            print_error("Le jeton de décryptage est invalide.")
        except Exception as e:
            print_error(f"Impossible de charger les utilisateurs. {str(e)}")
        return {}

    def _save_users(self):
        user_file = conf.CONFIG["USER_FILE"]
        try:
            packed_data = msgpack.packb(self.users)
            encrypted_data = Fernet(self.key).encrypt(packed_data)
            with open(user_file, "wb") as f:
                f.write(encrypted_data)
        except Exception as e:
            print_error(f"La sauvegarde des utilisateurs a échoué. {str(e)}")

    def user_exists(self, username):
        return username in self.users

    def create_user(self, username, password, role="user", caller_role="user"):
        if caller_role != "admin":
            print_error(LANGUAGES[conf.global_language]["permission_denied"])
            return
        if username in self.users:
            print_error(LANGUAGES[conf.global_language]["user_exists"])
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
            print_error(LANGUAGES[conf.global_language]["permission_denied"])
            return
        if username not in self.users:
            print_error(LANGUAGES[conf.global_language]["user_not_found"])
            return
        if new_password:
            self.users[username]["password"] = hashlib.sha256(new_password.encode()).hexdigest()
        if new_role:
            self.users[username]["role"] = new_role
        self._save_users()
        print_success(LANGUAGES[conf.global_language]["user_altered"].format(username=username))

    def drop_user(self, username, caller_role="user"):
        if caller_role != "admin":
            print_error(LANGUAGES[conf.global_language]["permission_denied"])
            return
        if username not in self.users:
            print_error(LANGUAGES[conf.global_language]["user_not_found"])
            return
        del self.users[username]
        self._save_users()
        print_success(LANGUAGES[conf.global_language]["user_dropped"].format(username=username))

    def grant(self, username, db, table, permissions, caller_role="user"):
        if caller_role != "admin":
            print_error(LANGUAGES[conf.global_language]["permission_denied"])
            return
        if username not in self.users:
            print_error(LANGUAGES[conf.global_language]["user_not_found"])
            return
        if db not in self.users[username]["permissions"]:
            self.users[username]["permissions"][db] = {}
        if table not in self.users[username]["permissions"][db]:
            self.users[username]["permissions"][db][table] = {}
        for perm in permissions:
            self.users[username]["permissions"][db][table][perm.strip()] = True
        self._save_users()
        print_success(f"Permissions {permissions} accordées à {username} pour {db}.{table}")

    def revoke(self, username, db, table, permissions, caller_role="user"):
        if caller_role != "admin":
            print_error(LANGUAGES[conf.global_language]["permission_denied"])
            return
        if username not in self.users:
            print_error(LANGUAGES[conf.global_language]["user_not_found"])
            return
        if db in self.users[username]["permissions"] and table in self.users[username]["permissions"][db]:
            for perm in permissions:
                self.users[username]["permissions"][db][table].pop(perm.strip(), None)
        self._save_users()
        print_success(f"Permissions {permissions} révoquées pour {username} sur {db}.{table}")

    def grant_all_privileges(self, username, caller_role="user"):
        if caller_role != "admin":
            print_error(LANGUAGES[conf.global_language]["permission_denied"])
            return
        if username not in self.users:
            print_error(LANGUAGES[conf.global_language]["user_not_found"])
            return
        self.users[username]["permissions"]["*"] = {"*": {"ALL PRIVILEGES": True}}
        self._save_users()
        print_success(f"All privileges granted to {username}.")

    def revoke_all_privileges(self, username, caller_role="user"):
        if caller_role != "admin":
            print_error(LANGUAGES[conf.global_language]["permission_denied"])
            return
        if username not in self.users:
            print_error(LANGUAGES[conf.global_language]["user_not_found"])
            return
        if "*" in self.users[username]["permissions"]:
            del self.users[username]["permissions"]["*"]
        self._save_users()
        print_success(f"All privileges revoked from {username}.")

    def authenticate(self, username, password):
        if username not in self.users:
            return None
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        if self.users[username]["password"] != hashed_password:
            return None
        otp = str(np.random.randint(100000, 999999))
        print_response(LANGUAGES[conf.global_language]["otp_sent"] + otp, "info")
        entered_otp = input("Code OTP: ").strip()
        if entered_otp != otp:
            print_error(LANGUAGES[conf.global_language]["otp_invalid"])
            return None
        print_success(f"User '{username}' authenticated successfully.")
        return self.users[username]