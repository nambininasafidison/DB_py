import os
import threading
import time

import config.config as conf
from config.language import LANGUAGES
from utils.file_utils import read_msgpack, write_msgpack
from utils.logger_utils import print_error, print_success

class BackupManager:
    def __init__(self, db_system):
        self.backup_dir = conf.CONFIG["BACKUP_DIR"]
        self.db_system = db_system
        os.makedirs(self.backup_dir, exist_ok=True)

    def backup(self):
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}.msgpack")
            data = {
                "mapping": read_msgpack(conf.CONFIG["MAPPING_FILE"], self.db_system.key),
                "users": read_msgpack(conf.CONFIG["USER_FILE"], self.db_system.key),
                "databases": {}
            }
            user_data = read_msgpack(conf.CONFIG["USER_FILE"], self.db_system.key)
            if user_data is None:
                print_error("La sauvegarde des utilisateurs a échoué.")
                return
            mapping = read_msgpack(conf.CONFIG["MAPPING_FILE"], self.db_system.key)
            for db_name, db_obf in mapping.items():
                db_path = os.path.join(conf.CONFIG["DATA_DIR"], db_obf)
                metadata_path = os.path.join(db_path, ".metadata.msgpack")
                metadata = read_msgpack(metadata_path, self.db_system.metadata_key)
                data["databases"][db_name] = {"metadata": metadata}
                for table_name, table_obf in metadata.get("tables", {}).items():
                    table_path = os.path.join(db_path, table_obf + ".msgpack")
                    data["databases"][db_name][table_name] = read_msgpack(table_path, self.db_system.metadata_key)
            write_msgpack(backup_path, data, self.db_system.key)
            print_success(LANGUAGES[conf.global_language]["backup_created"].format(backup_file=backup_path))
        except Exception as e:
            print_error(f"La sauvegarde a échoué. {str(e)}")

    def restore(self, backup_file):
        backup_path = os.path.join(self.backup_dir, backup_file)
        if not os.path.exists(backup_path):
            print_error(LANGUAGES[conf.global_language]["backup_not_found"].format(backup_file=backup_file))
            return
        try:
            data = read_msgpack(backup_path, self.db_system.key)
            write_msgpack(conf.CONFIG["MAPPING_FILE"], data["mapping"], self.db_system.key)
            write_msgpack(conf.CONFIG["USER_FILE"], data["users"], self.db_system.key)
            for db_name, db_data in data["databases"].items():
                db_obf = data["mapping"][db_name]
                db_path = os.path.join(conf.CONFIG["DATA_DIR"], db_obf)
                os.makedirs(db_path, exist_ok=True)
                metadata_path = os.path.join(db_path, ".metadata.msgpack")
                write_msgpack(metadata_path, db_data["metadata"], self.db_system.metadata_key)
                for table_name, table_data in db_data.items():
                    if table_name != "metadata":
                        table_obf = db_data["metadata"]["tables"][table_name]
                        table_path = os.path.join(db_path, table_obf + ".msgpack")
                        write_msgpack(table_path, table_data, self.db_system.metadata_key)
            print_success(LANGUAGES[conf.global_language]["restore_completed"].format(backup_file=backup_path))
        except Exception as e:
            print_error(f"Restore failed: {str(e)}")

    def schedule_backups(self, interval_hours):
        try:
            def backup_task():
                while True:
                    self.backup()
                    time.sleep(interval_hours * 3600)
            threading.Thread(target=backup_task, daemon=True).start()
        except Exception as e:
            print_error(f"Failed to schedule backups: {str(e)}")