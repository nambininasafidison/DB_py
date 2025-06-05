import os
import logging
from multiprocessing import Pool, cpu_count

import config.config as conf
from config.language import LANGUAGES
from core.bplus_tree import BPlusTree
from managers.backup_manager import BackupManager
from utils.file_utils import get_obfuscated_name, read_msgpack, write_msgpack
from utils.filter_utils import filter_rows
from utils.logger_utils import print_error, print_response, print_success, print_warning
from utils.utils import encrypt_data, generate_obfuscated_name
from datetime import datetime
import re
import msgpack
import json
from src.core.procedures import ProcedureManager

class DatabaseSystem:
    def __init__(self, key, metadata_key, replicator, cache, user_manager, language=None):
        if language is None:
            language = conf.global_language
        self.key = key
        self.metadata_key = metadata_key
        self.replicator = replicator
        self.cache = cache
        self.user_manager = user_manager
        self.indexes = {}
        self.current_database = None
        self.language = language
        self.logger = self._setup_logger()
        self.backup_manager = BackupManager(self)
        self.procedure_manager = ProcedureManager(os.path.join(conf.CONFIG["DATA_DIR"], "procedures"))

    def _setup_logger(self):
        logger = logging.getLogger("audit")
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(conf.CONFIG["AUDIT_LOG"])
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def set_language(self, new_lang):
        if new_lang in LANGUAGES:
            conf.global_language = new_lang
            self.language = new_lang
            print_success(LANGUAGES[self.language]["language_changed"].format(language=new_lang))
        else:
            print_error(LANGUAGES[self.language]["language_not_supported"])

    def use_database(self, database_name):
        obfuscated_name = get_obfuscated_name(database_name, self.key)
        db_path = os.path.join(conf.CONFIG["DATA_DIR"], obfuscated_name)
        if obfuscated_name and os.path.exists(db_path):
            self.current_database = database_name
            print_success(LANGUAGES[self.language]["db_selected"].format(db=database_name))
            return True
        else:
            print_error(LANGUAGES[self.language]["db_not_found"])
            return False

    def write_msgpack_atomic(self, file_path, content, key):
        temp_path = file_path + ".tmp"
        packed_data = msgpack.packb(content)
        encrypted_data = encrypt_data(packed_data, key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(temp_path, "wb") as f:
            f.write(encrypted_data)
        os.replace(temp_path, file_path)

    def create_database(self, name, user):
        try:
            if user["role"] != "admin":
                print_error(LANGUAGES[self.language]["permission_denied"])
                return
            mapping = read_msgpack(conf.CONFIG["MAPPING_FILE"], self.key) or {}
            if name in mapping:
                print_error(LANGUAGES[self.language]["db_exists"])
                return
            obfuscated_name = generate_obfuscated_name()
            db_path = os.path.join(conf.CONFIG["DATA_DIR"], obfuscated_name)
            os.makedirs(db_path, exist_ok=True)
            mapping[name] = obfuscated_name
            write_msgpack(conf.CONFIG["MAPPING_FILE"], mapping, self.key)
            metadata_path = os.path.join(db_path, ".metadata.msgpack")
            self.write_msgpack_atomic(metadata_path, {"tables": {}, "indexes": {}}, self.metadata_key)
            self.logger.info(f"User: {user['username']} - Created database: {name}")
            print_success(LANGUAGES[self.language]["db_created"].format(db=name))
        except Exception as e:
            print_error(LANGUAGES[self.language]["db_creation_failed"].format(error=str(e)))

    def create_table(self, table_name, columns, constraints, user):
        if not self.current_database or (
            user["role"] != "admin" and 
            "create" not in user.get("permissions", {}).get(self.current_database, {}).get(table_name, {})
        ):
            print_error(LANGUAGES[self.language]["permission_denied"])
            return

        db_obfuscated = get_obfuscated_name(self.current_database, self.key)
        if not db_obfuscated:
            print_error(LANGUAGES[self.language]["db_not_found"])
            return

        db_path = os.path.join(conf.CONFIG["DATA_DIR"], db_obfuscated)
        metadata_path = os.path.join(db_path, ".metadata.msgpack")
        metadata = read_msgpack(metadata_path, self.metadata_key)

        if table_name in metadata.get("tables", {}):
            print_error(LANGUAGES[self.language]["table_exists"])
            return

        table_obfuscated = generate_obfuscated_name()
        table_path = os.path.join(db_path, table_obfuscated + ".msgpack")
        table_data = {
            "columns": columns,
            "constraints": constraints,
            "rows": [],
            "defaults": constraints.get("defaults", {}),
            "nullable": {col: col not in constraints.get("not_null", []) for col in columns},
            "primary_keys": constraints.get("primary_keys", []),
            "unique_keys": constraints.get("unique_keys", [])
        }

        write_msgpack(table_path, table_data, self.metadata_key)
        metadata.setdefault("tables", {})[table_name] = table_obfuscated
        write_msgpack(metadata_path, metadata, self.metadata_key)

        for col in constraints.get("unique_keys", []):
            self.indexes[f"{self.current_database}.{table_name}.{col}"] = BPlusTree()

        self.replicator.replicate({"operation": "create_table", "table": table_name, "columns": columns})
        self.logger.info(f"User: {user['username']} - Created table: {table_name}")
        print_success(LANGUAGES[self.language]["table_created"].format(table=table_name))

    def insert_record(self, table_name, record, user):
        try:
            if not self.current_database:
                print_error(LANGUAGES[self.language]["no_db_selected"])
                return
            if user["role"] != "admin" and "insert" not in user.get("permissions", {}).get(self.current_database, {}).get(table_name, {}):
                print_error(LANGUAGES[self.language]["permission_denied"])
                return
            table_path = self._get_table_path(table_name)
            if not table_path:
                print_error(LANGUAGES[self.language]["table_not_found"])
                return
            table_data = read_msgpack(table_path, self.metadata_key)
            constraints = table_data.get("constraints", {})
            # NOT NULL
            for col in constraints.get("not_null", []):
                if col not in record or record[col] is None:
                    print_error(LANGUAGES[self.language]["not_null_violation"].format(col=col))
                    return
            # UNIQUE
            for col in constraints.get("unique_keys", []):
                for row in table_data["rows"]:
                    if row.get(col) == record.get(col):
                        print_error(LANGUAGES[self.language]["unique_violation"].format(val=record.get(col), col=col))
                        return
            # PRIMARY KEY
            for col in constraints.get("primary_keys", []):
                for row in table_data["rows"]:
                    if row.get(col) == record.get(col):
                        print_error(LANGUAGES[self.language]["primary_key_duplicate"].format(col=col, val=record.get(col)))
                        return
            # FOREIGN KEY
            for fk in constraints.get("foreign_keys", {}).values():
                ref_table = fk["ref_table"]
                ref_cols = fk["ref_columns"]
                fk_cols = fk["columns"]
                ref_path = self._get_table_path(ref_table)
                if not ref_path:
                    print_error(LANGUAGES[self.language]["table_not_found"])
                    return
                ref_data = read_msgpack(ref_path, self.metadata_key)
                found = False
                for ref_row in ref_data["rows"]:
                    if all(record.get(fk_col) == ref_row.get(ref_col) for fk_col, ref_col in zip(fk_cols, ref_cols)):
                        found = True
                        break
                if not found:
                    print_error(LANGUAGES[self.language]["foreign_key_violation"].format(col=','.join(fk_cols), val=','.join(str(record.get(fk_col)) for fk_col in fk_cols), ref_table=ref_table, ref_col=','.join(ref_cols)))
                    return
            # CHECK
            for check in constraints.get("checks", []):
                check_name, check_condition = check
                try:
                    if not eval(check_condition, {}, record):
                        print_error(LANGUAGES[self.language]["check_violation"].format(col=check_name, condition=check_condition))
                        return
                except Exception as e:
                    print_error(f"Erreur d'évaluation CHECK: {str(e)}")
                    return
            table_data["rows"].append(record)
            write_msgpack(table_path, table_data, self.metadata_key)
            self.logger.info(f"User: {user['username']} - Inserted record into {table_name}: {record}")
            print_success(LANGUAGES[self.language]["record_inserted"])
        except Exception as e:
            print_error(LANGUAGES[self.language]["insert_failed"].format(error=str(e)))

    def update_record(self, table_name, set_clause, conditions, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return
        if user["role"] != "admin" and "update" not in user.get("permissions", {}).get(self.current_database, {}).get(table_name, {}):
            print_error(LANGUAGES[self.language]["permission_denied"])
            return
        table_path = self._get_table_path(table_name)
        if not table_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return
        set_col = set_clause.split('=')[0].strip()
        set_val = set_clause.split('=')[1].strip().strip("'")
        table_data = read_msgpack(table_path, self.metadata_key)
        if set_col not in table_data["columns"]:
            print_error(LANGUAGES[self.language]["column_invalid"])
            return
        constraints = table_data.get("constraints", {})
        updated = False
        for row in table_data["rows"]:
            if all(row.get(k) == v for k, v in conditions.items()):
                # NOT NULL
                if set_val is None and set_col in constraints.get("not_null", []):
                    print_error(LANGUAGES[self.language]["not_null_violation"].format(col=set_col))
                    return
                # UNIQUE
                if set_col in constraints.get("unique_keys", []):
                    for other in table_data["rows"]:
                        if other is not row and other.get(set_col) == set_val:
                            print_error(LANGUAGES[self.language]["unique_violation"].format(val=set_val, col=set_col))
                            return
                # PRIMARY KEY
                if set_col in constraints.get("primary_keys", []):
                    for other in table_data["rows"]:
                        if other is not row and other.get(set_col) == set_val:
                            print_error(LANGUAGES[self.language]["primary_key_duplicate"].format(col=set_col, val=set_val))
                            return
                # FOREIGN KEY
                for fk in constraints.get("foreign_keys", {}).values():
                    if set_col in fk["columns"]:
                        ref_table = fk["ref_table"]
                        ref_cols = fk["ref_columns"]
                        fk_cols = fk["columns"]
                        ref_path = self._get_table_path(ref_table)
                        if not ref_path:
                            print_error(LANGUAGES[self.language]["table_not_found"])
                            return
                        ref_data = read_msgpack(ref_path, self.metadata_key)
                        found = False
                        for ref_row in ref_data["rows"]:
                            if all((set_val if fk_col == set_col else row.get(fk_col)) == ref_row.get(ref_col) for fk_col, ref_col in zip(fk_cols, ref_cols)):
                                found = True
                                break
                        if not found:
                            print_error(LANGUAGES[self.language]["foreign_key_violation"].format(col=set_col, val=set_val, ref_table=ref_table, ref_col=','.join(ref_cols)))
                            return
                # CHECK
                for check in constraints.get("checks", []):
                    check_name, check_condition = check
                    temp_row = row.copy()
                    temp_row[set_col] = set_val
                    try:
                        if not eval(check_condition, {}, temp_row):
                            print_error(LANGUAGES[self.language]["check_violation"].format(col=check_name, condition=check_condition))
                            return
                    except Exception as e:
                        print_error(f"Erreur d'évaluation CHECK: {str(e)}")
                        return
                row[set_col] = set_val
                updated = True
        if updated:
            write_msgpack(table_path, table_data, self.metadata_key)
            self.replicator.replicate({"operation": "update", "table": table_name, "set": set_clause, "conditions": conditions})
            self.cache.set(f"{self.current_database}:{table_name}", table_data["rows"])
            self.logger.info(f"User: {user['username']} - Updated {table_name}: SET {set_clause} WHERE {conditions}")
            print_success(LANGUAGES[self.language]["data_updated"])
        else:
            print_warning(LANGUAGES[self.language]["no_row_updated"])

    def alter_table(self, table_name, action, column_name, column_type=None, default_value=None, user=None):
        if not self.current_database or (user["role"] != "admin" and "alter" not in user.get("permissions", {}).get(self.current_database, {}).get(table_name, {})):
            print_error(LANGUAGES[self.language]["permission_denied"])
            return
        table_path = self._get_table_path(table_name)
        if not table_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return
        table_data = read_msgpack(table_path, self.metadata_key)
        if action.upper() == "ADD":
            if column_name in table_data["columns"]:
                print_error(LANGUAGES[self.language]["column_already_exists"])
                return
            table_data["columns"][column_name] = column_type
            for row in table_data["rows"]:
                row[column_name] = default_value if default_value is not None else None
        elif action.upper() == "DROP":
            if column_name not in table_data["columns"]:
                print_error(LANGUAGES[self.language]["column_not_exists"])
                return
            del table_data["columns"][column_name]
            for row in table_data["rows"]:
                row.pop(column_name, None)
        write_msgpack(table_path, table_data, self.metadata_key)
        self.logger.info(f"User: {user['username']} - Altered table {table_name}: {action} {column_name}")
        print_success(f"Table {table_name} modifiée")

    def drop_table(self, table_name, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return
        if user["role"] != "admin" and "drop" not in user.get("permissions", {}).get(self.current_database, {}).get(table_name, {}):
            print_error(LANGUAGES[self.language]["permission_denied"])
            return
        table_path = self._get_table_path(table_name)
        if not table_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return
        db_obfuscated = get_obfuscated_name(self.current_database, self.key)
        db_path = os.path.join(conf.CONFIG["DATA_DIR"], db_obfuscated)
        metadata_path = os.path.join(db_path, ".metadata.msgpack")
        metadata = read_msgpack(metadata_path, self.metadata_key)
        table_obfuscated = metadata["tables"].pop(table_name, None)
        if table_obfuscated:
            os.remove(os.path.join(db_path, table_obfuscated + ".msgpack"))
            write_msgpack(metadata_path, metadata, self.metadata_key)
            self.logger.info(f"User: {user['username']} - Dropped table: {table_name}")
            print_success(LANGUAGES[self.language]["table_dropped"].format(table=table_name))
        else:
            print_error(LANGUAGES[self.language]["table_not_found"])

    def drop_database(self, database_name, user):
        try:
            if user["role"] != "admin":
                print_error(LANGUAGES[self.language]["permission_denied"])
                return
            obfuscated_name = get_obfuscated_name(database_name, self.key)
            db_path = os.path.join(conf.CONFIG["DATA_DIR"], obfuscated_name)
            if not os.path.exists(db_path):
                print_error(LANGUAGES[self.language]["db_not_found"])
                return
            for root, dirs, files in os.walk(db_path, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
            os.rmdir(db_path)
            mapping = read_msgpack(conf.CONFIG["MAPPING_FILE"], self.key)
            mapping.pop(database_name, None)
            write_msgpack(conf.CONFIG["MAPPING_FILE"], mapping, self.key)
            self.logger.info(f"User: {user['username']} - Dropped database: {database_name}")
            print_success(LANGUAGES[self.language]["db_dropped"].format(db=database_name))
        except Exception as e:
            print_error(LANGUAGES[self.language]["db_deletion_failed"].format(error=str(e)))

    def join_tables(self, table1, table2, col1, col2, user):
        if not self.current_database or (user["role"] != "admin" and "select" not in user.get("permissions", {}).get(self.current_database, {}).get(table1, {})) or \
        (user["role"] != "admin" and "select" not in user.get("permissions", {}).get(self.current_database, {}).get(table2, {})):
            print_error(LANGUAGES[self.language]["permission_denied"])
            return []
        
        table1_path = self._get_table_path(table1)
        table2_path = self._get_table_path(table2)
        if not table1_path or not table2_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return []
        
        table1_data = read_msgpack(table1_path, self.metadata_key)["rows"]
        table2_data = read_msgpack(table2_path, self.metadata_key)["rows"]
        
        return [{**row1, **row2} for row1 in table1_data for row2 in table2_data if row1[col1] == row2[col2]]

    def create_index(self, table_name, column_name, user, index_type="bplus"):
        if not self.current_database or (user["role"] != "admin" and "create" not in user.get("permissions", {}).get(self.current_database, {}).get(table_name, {})):
            print_error(LANGUAGES[self.language]["permission_denied"])
            return
        table_path = self._get_table_path(table_name)
        if not table_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return
        table_data = read_msgpack(table_path, self.metadata_key)
        if column_name not in table_data["columns"]:
            print_error(LANGUAGES[self.language]["column_not_exists"])
            return
        index_key = f"{self.current_database}.{table_name}.{column_name}"
        if index_key not in self.indexes:
            if index_type == "bplus":
                self.indexes[index_key] = BPlusTree()
            elif index_type == "hash":
                self.indexes[index_key] = {}
            for row in table_data["rows"]:
                if index_type == "bplus":
                    self.indexes[index_key].insert(row[column_name], row)
                elif index_type == "hash":
                    self.indexes[index_key][row[column_name]] = row
        self.logger.info(f"User: {user['username']} - Created {index_type} index on {table_name}.{column_name}")
        print_success(LANGUAGES[self.language]["index_created"].format(table=table_name, column=column_name))

    def shard_table(self, table_name, shard_column, num_shards, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return
        table_path = self._get_table_path(table_name)
        if not table_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return
        table_data = read_msgpack(table_path, self.metadata_key)
        if shard_column not in table_data["columns"]:
            print_error(LANGUAGES[self.language]["column_invalid"])
            return
        shards = [{} for _ in range(num_shards)]
        for row in table_data["rows"]:
            shard_index = hash(row[shard_column]) % num_shards
            shards[shard_index].setdefault("rows", []).append(row)
        for i, shard in enumerate(shards):
            shard_path = f"{table_path}_shard_{i}"
            write_msgpack(shard_path, shard, self.metadata_key)
        print_success(LANGUAGES[self.language]["table_sharded"].format(table=table_name, num_shards=num_shards, shard_column=shard_column))

    def _get_table_path(self, table_name):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return None
        db_obfuscated = get_obfuscated_name(self.current_database, self.key)
        if not db_obfuscated:
            return None
        db_path = os.path.join(conf.CONFIG["DATA_DIR"], db_obfuscated)
        metadata_path = os.path.join(db_path, ".metadata.msgpack")
        metadata = read_msgpack(metadata_path, self.metadata_key)
        table_obfuscated = metadata["tables"].get(table_name)
        if not table_obfuscated:
            return None
        return os.path.join(db_path, table_obfuscated + ".msgpack")

    def show_databases(self):
        mapping = read_msgpack(conf.CONFIG["MAPPING_FILE"], self.key)
        db_list = "\n".join(mapping.keys())
        print_success(LANGUAGES[self.language]["list_databases"].format(list=db_list))

    def show_tables(self):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return
        db_obfuscated = get_obfuscated_name(self.current_database, self.key)
        if not db_obfuscated:
            print_error(LANGUAGES[self.language]["db_not_found"])
            return
        db_path = os.path.join(conf.CONFIG["DATA_DIR"], db_obfuscated)
        metadata_path = os.path.join(db_path, ".metadata.msgpack")
        metadata = read_msgpack(metadata_path, self.metadata_key)
        tables = list(metadata.get("tables", {}).keys())
        table_list = "\n".join(tables)
        print_success(LANGUAGES[self.language]["list_tables"].format(list=table_list))

    def create_materialized_view(self, view_name, query, user):
        if not self.current_database or (user["role"] != "admin" and "create" not in user.get("permissions", {}).get(self.current_database, {}).get(view_name, {})):
            print_error(LANGUAGES[self.language]["permission_denied"])
            return
        view_path = os.path.join(conf.CONFIG["DATA_DIR"], f"{view_name}.view")
        result = self.query_raw(query, user)
        write_msgpack(view_path, result, self.metadata_key)
        print_success(f"Materialized view {view_name} created.")

    def refresh_materialized_view(self, view_name, query, user):
        if not self.current_database or (user["role"] != "admin" and "update" not in user.get("permissions", {}).get(self.current_database, {}).get(view_name, {})):
            print_error(LANGUAGES[self.language]["permission_denied"])
            return
        view_path = os.path.join(conf.CONFIG["DATA_DIR"], f"{view_name}.view")
        result = self.query_raw(query, user)
        write_msgpack(view_path, result, self.metadata_key)
        print_success(f"Materialized view {view_name} refreshed.")

    def create_cte(self, cte_name, query, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return
        cte_path = os.path.join(conf.CONFIG["DATA_DIR"], f"{cte_name}.cte")
        result = self.query_raw(query, user)
        write_msgpack(cte_path, result, self.metadata_key)
        print_success(f"CTE {cte_name} created.")

    def grant_all_privileges(self, username, user):
        if user["role"] != "admin":
            print_error(LANGUAGES[self.language]["permission_denied"])
            return
        if not self.user_manager.user_exists(username):
            print_error(LANGUAGES[self.language]["user_not_found"])
            return
        self.user_manager.grant(username, "*", "*", ["ALL PRIVILEGES"], user["role"])
        print_success(f"All privileges granted to {username}.")

    def revoke_all_privileges(self, username, user):
        if user["role"] != "admin":
            print_error(LANGUAGES[self.language]["permission_denied"])
            return
        if not self.user_manager.user_exists(username):
            print_error(LANGUAGES[self.language]["user_not_found"])
            return
        self.user_manager.revoke(username, "*", "*", ["ALL PRIVILEGES"], user["role"])
        print_success(f"All privileges revoked from {username}.")

    def merge_records(self, target_table, source_table, on_condition, when_matched, when_not_matched, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return
        target_path = self._get_table_path(target_table)
        source_path = self._get_table_path(source_table)
        if not target_path or not source_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return
        
        target_data = read_msgpack(target_path, self.metadata_key)
        source_data = read_msgpack(source_path, self.metadata_key)
        
        for source_row in source_data["rows"]:
            matched = False
            for target_row in target_data["rows"]:
                if eval(on_condition, {"target": target_row, "source": source_row}):
                    matched = True
                    if when_matched:
                        exec(when_matched, {"target": target_row, "source": source_row})
            if not matched and when_not_matched:
                new_row = {}
                exec(when_not_matched, {"new_row": new_row, "source": source_row})
                target_data["rows"].append(new_row)
        
        write_msgpack(target_path, target_data, self.metadata_key)
        print_success(f"MERGE operation completed on {target_table}.")

    def query_with_window_function(self, table_name, select_columns, partition_by_clause, order_by_clause, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return []
        table_path = self._get_table_path(table_name)
        if not table_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return []
        
        table_data = read_msgpack(table_path, self.metadata_key)
        rows = table_data["rows"]
        
        if partition_by_clause:
            partition_column = partition_by_clause.split()[2]
            partitions = {}
            for row in rows:
                key = row[partition_column]
                partitions.setdefault(key, []).append(row)
        else:
            partitions = {"all": rows}
        
        result = []
        for partition_key, partition_rows in partitions.items():
            if order_by_clause:
                order_column = order_by_clause.split()[2]
                partition_rows.sort(key=lambda x: x[order_column])
            for i, row in enumerate(partition_rows):
                row["row_number"] = i + 1
                result.append(row)
        
        return result

    def query_json(self, table_name, json_column, json_path, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return []
        table_path = self._get_table_path(table_name)
        if not table_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return []
        table_data = read_msgpack(table_path, self.metadata_key)
        rows = table_data["rows"]
        result = []
        for row in rows:
            if json_column in row:
                try:
                    json_data = json.loads(row[json_column])
                    value = eval(f"json_data{json_path}")
                    result.append({json_column: value})
                except Exception as e:
                    print_error(f"JSON extraction error: {str(e)}")
        return result

    def query_array(self, table_name, array_column, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return []
        table_path = self._get_table_path(table_name)
        if not table_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return []
        table_data = read_msgpack(table_path, self.metadata_key)
        rows = table_data["rows"]
        result = []
        for row in rows:
            if array_column in row:
                result.append(row[array_column])
        return {"array_agg": result}

    def full_outer_join(self, table1, table2, condition, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return []
        table1_path = self._get_table_path(table1)
        table2_path = self._get_table_path(table2)
        if not table1_path or not table2_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return []
        table1_data = read_msgpack(table1_path, self.metadata_key)["rows"]
        table2_data = read_msgpack(table2_path, self.metadata_key)["rows"]
        result = []
        matched_rows = set()
        for row1 in table1_data:
            match_found = False
            for row2 in table2_data:
                if eval(condition, {"row1": row1, "row2": row2}):
                    result.append({**row1, **row2})
                    match_found = True
                    matched_rows.add(id(row2))
            if not match_found:
                result.append({**row1, **{col: None for col in table2_data[0].keys()}})
        for row2 in table2_data:
            if id(row2) not in matched_rows:
                result.append({**{col: None for col in table1_data[0].keys()}, **row2})
        return result

    def division_operation(self, table1, table2, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return []
        table1_path = self._get_table_path(table1)
        table2_path = self._get_table_path(table2)
        if not table1_path or not table2_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return []
        table1_data = read_msgpack(table1_path, self.metadata_key)["rows"]
        table2_data = read_msgpack(table2_path, self.metadata_key)["rows"]
        result = [row1 for row1 in table1_data if all(any(row1[col] == row2[col] for row2 in table2_data) for col in table2_data[0])]
        return result

    def json_table(self, table_name, json_column, path, columns, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return []
        table_path = self._get_table_path(table_name)
        if not table_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return []
        table_data = read_msgpack(table_path, self.metadata_key)
        rows = table_data["rows"]
        result = []
        for row in rows:
            if json_column in row:
                try:
                    json_data = json.loads(row[json_column])
                    extracted_data = eval(f"json_data{path}")
                    for item in extracted_data:
                        result.append({col: item.get(col) for col in columns})
                except Exception as e:
                    print_error(f"JSON_TABLE extraction error: {str(e)}")
        return result

    def add_generated_column(self, table_name, column_name, expression, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return
        table_path = self._get_table_path(table_name)
        if not table_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return
        table_data = read_msgpack(table_path, self.metadata_key)
        if column_name in table_data["columns"]:
            print_error(LANGUAGES[self.language]["column_already_exists"])
            return
        table_data["columns"][column_name] = f"GENERATED AS ({expression})"
        for row in table_data["rows"]:
            row[column_name] = eval(expression, {"row": row})
        write_msgpack(table_path, table_data, self.metadata_key)
        print_success(f"Generated column {column_name} added to {table_name}.")

    def recursive_cte(self, cte_name, anchor_query, recursive_query, main_query, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return []
        cte_result = self.query_raw(anchor_query, user)
        while True:
            new_rows = self.query_raw(recursive_query, user)
            if not new_rows:
                break
            cte_result.extend(new_rows)
        final_result = self.query_raw(main_query, user)
        return final_result

    def create_sequence(self, sequence_name, start_value, increment_by, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return
        db_path = os.path.join(conf.CONFIG["DATA_DIR"], get_obfuscated_name(self.current_database, self.key))
        sequence_path = os.path.join(db_path, f"{sequence_name}.seq")
        if os.path.exists(sequence_path):
            print_error(LANGUAGES[self.language]["sequence_exists"].format(sequence=sequence_name))
            return
        sequence_data = {
            "current_value": int(start_value),
            "increment_by": int(increment_by)
        }
        write_msgpack(sequence_path, sequence_data, self.metadata_key)
        print_success(LANGUAGES[self.language]["sequence_created"].format(sequence=sequence_name))

    def create_enum(self, enum_name, values, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return
        db_path = os.path.join(conf.CONFIG["DATA_DIR"], get_obfuscated_name(self.current_database, self.key))
        enum_path = os.path.join(db_path, f"{enum_name}.enum")
        if os.path.exists(enum_path):
            print_error(LANGUAGES[self.language]["enum_exists"].format(enum=enum_name))
            return
        enum_data = {"values": values.split(",")}
        write_msgpack(enum_path, enum_data, self.metadata_key)
        print_success(LANGUAGES[self.language]["enum_created"].format(enum=enum_name))

    def create_foreign_data_wrapper(self, fdw_name, handler, validator, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return
        db_path = os.path.join(conf.CONFIG["DATA_DIR"], get_obfuscated_name(self.current_database, self.key))
        fdw_path = os.path.join(db_path, f"{fdw_name}.fdw")
        if os.path.exists(fdw_path):
            print_error(LANGUAGES[self.language]["fdw_exists"].format(fdw=fdw_name))
            return
        fdw_data = {"handler": handler, "validator": validator}
        write_msgpack(fdw_path, fdw_data, self.metadata_key)
        print_success(LANGUAGES[self.language]["fdw_created"].format(fdw=fdw_name))

    def create_tablespace(self, tablespace_name, location, user):
        if not os.path.exists(location):
            print_error(LANGUAGES[self.language]["location_not_found"].format(location=location))
            return
        tablespace_path = os.path.join(conf.CONFIG["DATA_DIR"], f"{tablespace_name}.tablespace")
        if os.path.exists(tablespace_path):
            print_error(LANGUAGES[self.language]["tablespace_exists"].format(tablespace=tablespace_name))
            return
        tablespace_data = {"location": location}
        write_msgpack(tablespace_path, tablespace_data, self.metadata_key)
        print_success(LANGUAGES[self.language]["tablespace_created"].format(tablespace=tablespace_name))

    def time_travel_query(self, table_name, timestamp, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return []
        table_path = self._get_table_path(table_name)
        if not table_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return []
        history_path = table_path + ".history"
        if not os.path.exists(history_path):
            print_error(LANGUAGES[self.language]["no_history_found"])
            return []
        history_data = read_msgpack(history_path, self.metadata_key)
        result = [row for row in history_data if row["_timestamp"] <= timestamp]
        return result

    def add_data_masking(self, table_name, column_name, mask_function, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return
        table_path = self._get_table_path(table_name)
        if not table_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return
        table_data = read_msgpack(table_path, self.metadata_key)
        if column_name not in table_data["columns"]:
            print_error(LANGUAGES[self.language]["column_not_exists"])
            return
        table_data["columns"][column_name] = f"MASKED USING {mask_function}"
        write_msgpack(table_path, table_data, self.metadata_key)
        print_success(f"Data masking added to column {column_name} in table {table_name}.")

    def enable_row_level_security(self, table_name, user):
        if not self.current_database:
            print_error(LANGUAGES[self.language]["no_db_selected"])
            return
        table_path = self._get_table_path(table_name)
        if not table_path:
            print_error(LANGUAGES[self.language]["table_not_found"])
            return
        table_data = read_msgpack(table_path, self.metadata_key)
        table_data["row_level_security"] = True
        write_msgpack(table_path, table_data, self.metadata_key)
        print_success(f"Row-level security enabled for table {table_name}.")

    def execute_with_hints(self, query, hints, user):
        # Example: Apply hints like "USE INDEX", "PARALLEL", etc.
        if "USE INDEX" in hints:
            print_warning("Hint: Using index for query optimization.")
        if "PARALLEL" in hints:
            print_warning("Hint: Executing query in parallel mode.")
        # Execute the query normally
        return self.query_raw(query, user)

    def query(self, table_name, conditions=None, user=None):
        """
        Query a table with optional conditions.
        """
        try:
            if not self.current_database:
                print_error(LANGUAGES[self.language]["no_db_selected"])
                return []
            if user and user["role"] != "admin" and "select" not in user.get("permissions", {}).get(self.current_database, {}).get(table_name, {}):
                print_error(LANGUAGES[self.language]["permission_denied"])
                return []
            table_path = self._get_table_path(table_name)
            if not table_path:
                print_error(LANGUAGES[self.language]["table_not_found"])
                return []
            table_data = read_msgpack(table_path, self.metadata_key)
            rows = table_data["rows"]
            if conditions:
                filtered_rows = [row for row in rows if all(row.get(k) == v for k, v in conditions.items())]
                return filtered_rows
            return rows
        except Exception as e:
            print_error(f"Erreur : La requête a échoué. {str(e)}")
            return []

    def create_procedure(self, name, code, user, is_function=False):
        if user["role"] != "admin":
            print_error(LANGUAGES[self.language]["permission_denied"])
            return
        self.procedure_manager.save_procedure(name, code, is_function)
        print_success(f"Procédure {'fonction' if is_function else 'procédure'} {name} enregistrée.")

    def execute_procedure(self, name, context, user):
        if user["role"] != "admin":
            print_error(LANGUAGES[self.language]["permission_denied"])
            return
        try:
            result = self.procedure_manager.execute_procedure(name, context)
            print_success(f"Procédure {name} exécutée. Résultat: {result}")
            return result
        except Exception as e:
            print_error(f"Erreur d'exécution de la procédure {name}: {e}")

    def list_procedures(self):
        return self.procedure_manager.list_procedures()