import json
import sqlparse
from tabulate import tabulate

import config.config as conf
from config.language import LANGUAGES
from query.nlp_model import nlp_model
from utils.file_utils import read_msgpack, write_msgpack
from utils.logger_utils import print_error, print_response, print_success, print_warning
import re

def clean_tokens(query):
    parsed = sqlparse.parse(query)
    if not parsed:
        return []
    return [token for token in parsed[0].tokens if not token.is_whitespace]

def find_token_value(tokens, keyword):
    for i, token in enumerate(tokens):
        if token.value.lower() == keyword.lower():
            if i + 1 < len(tokens):
                return tokens[i + 1].value
    return None

def execute_query(query, db_system, user, depth=0):
    try:
        if depth > 5:
            print_error(LANGUAGES[conf.global_language]["error"].format(error="Recursion limit reached"))
            return
        query_lower = query.lower()
        sql_keywords = [
            "use", "create", "insert", "select", "update", "alter", "drop",
            "truncate", "describe", "show", "grant", "revoke", "create index",
            "backup", "restore", "set", "train", "with", "union", "intersect", "except"
        ]

        if not any(query_lower.startswith(cmd) for cmd in sql_keywords):
            if nlp_model.model:
                sql_query = nlp_model.process(query)
                print_response(LANGUAGES[conf.global_language]["translated_query"].format(sql_query=sql_query), "info")
                execute_query(sql_query, db_system, user, depth + 1)
            else:
                print_error(LANGUAGES[conf.global_language]["nlp_model_not_trained"])
            return
        
        tokens = clean_tokens(query)

        if not tokens:
            print_error(LANGUAGES[conf.global_language]["error"].format(error="Empty query"))
            return
        command = None
        for token in tokens:
            if hasattr(token, 'ttype') and token.ttype is not None and str(token.ttype).startswith('Token.Keyword'):
                command = token.value.lower()
                break
            elif hasattr(token, 'ttype') and token.ttype is not None and str(token.ttype).startswith('Token.DML'):
                command = token.value.lower()
                break
            elif hasattr(token, 'ttype') and token.ttype is not None and str(token.ttype).startswith('Token.DDL'):
                command = token.value.lower()
                break
        if not command:
            for token in tokens:
                if hasattr(token, 'value') and token.value.strip():
                    command = token.value.lower()
                    break
        if not command:
            print_error(LANGUAGES[conf.global_language]["error"].format(error="Invalid query syntax: no command found"))
            return
        if command == "use":
            db_name = tokens[1].value if len(tokens) > 1 else None
            if db_name:
                if db_system.use_database(db_name):
                    print_success(LANGUAGES[conf.global_language]["db_selected"].format(db=db_name))
                else:
                    print_error(LANGUAGES[conf.global_language]["db_not_found"])
            else:
                print_error("Nom de base de données manquant")
        elif command == "create" and "database" in query_lower:
            if len(tokens) != 3:
                print_error("Syntaxe incorrecte pour la création de la base de données")
                return
            db_name = find_token_value(tokens, "database")
            db_system.create_database(db_name, user)
        elif command.lower() == "create" and "table" in query_lower:
            match = re.search(r'create\s+table\s+(\w+)', query, re.IGNORECASE)
            if not match:
                print_error("Syntaxe incorrecte pour la création de la table")
                return
            table_name = match.group(1)

            try:
                columns_str = query[query.index("(")+1:query.rindex(")")]
            except ValueError:
                print_error("Syntaxe incorrecte : parenthèses manquantes")
                return

            definitions = re.split(r',\s*(?![^()]*\))', columns_str)
            columns = {}
            constraints = {"primary_keys": [], "unique_keys": [], "foreign_keys": {}, "checks": [], "defaults": {}, "not_null": []}

            for definition in definitions:
                definition = definition.strip()
                if definition.lower().startswith("constraint"):
                    parts = definition.split()
                    if len(parts) < 3:
                        print_error("Syntaxe incorrecte pour la contrainte")
                        return
                    constraint_name = parts[1]
                    constraint_def = " ".join(parts[2:])
                    if "primary key" in constraint_def.lower():
                        constraints["primary_keys"].append(constraint_name)
                    elif "unique" in constraint_def.lower():
                        constraints["unique_keys"].append(constraint_name)
                    elif "foreign key" in constraint_def.lower():
                        fk_match = re.search(r'foreign key \(([^)]+)\) references (\w+)\(([^)]+)\)', constraint_def, re.IGNORECASE)
                        if fk_match:
                            fk_cols = [c.strip() for c in fk_match.group(1).split(",")]
                            ref_table = fk_match.group(2)
                            ref_cols = [c.strip() for c in fk_match.group(3).split(",")]
                            constraints["foreign_keys"][constraint_name] = {
                                "columns": fk_cols,
                                "ref_table": ref_table,
                                "ref_columns": ref_cols
                            }
                        else:
                            print_error(f"Syntaxe incorrecte pour la contrainte FOREIGN KEY: {constraint_def}")
                    elif "check" in constraint_def.lower():
                        check_match = re.search(r'check \((.+)\)', constraint_def, re.IGNORECASE)
                        if check_match:
                            check_condition = check_match.group(1).strip()
                            constraints["checks"].append((constraint_name, check_condition))
                        else:
                            print_error(f"Syntaxe incorrecte pour la contrainte CHECK: {constraint_def}")
                else:
                    parts = definition.split()
                    if len(parts) < 2:
                        print_error("Syntaxe incorrecte pour la colonne")
                        return
                    col_name = parts[0]
                    col_definition = " ".join(parts[1:])
                    columns[col_name] = col_definition

                    if "primary key" in col_definition.lower():
                        constraints["primary_keys"].append(col_name)
                    if "unique" in col_definition.lower():
                        constraints["unique_keys"].append(col_name)
                    if "not null" in col_definition.lower():
                        constraints["not_null"].append(col_name)
                    if "default" in col_definition.lower():
                        default_value = re.search(r'default\s+(.+)', col_definition, re.IGNORECASE)
                        if default_value:
                            constraints["defaults"][col_name] = default_value.group(1)

            db_system.create_table(table_name, columns, constraints, user)

        elif command == "insert":
            table_name, columns, all_values = None, [], []
            for i, token in enumerate(tokens):
                t = token.value if hasattr(token, "value") else token
                low = t.lower()
                if low == "into" and i + 1 < len(tokens):
                    nxt = tokens[i+1].value if hasattr(tokens[i+1], "value") else tokens[i+1]
                    if "(" in nxt:
                        table_name = nxt.split("(")[0]
                        columns = nxt[nxt.index("(")+1:nxt.index(")")].split(",")
                    else:
                        table_name = nxt
                elif low.startswith("values"):
                    after = t[len("values"):].strip()
                    if not after and i + 1 < len(tokens):
                        after = tokens[i+1].value if hasattr(tokens[i+1], "value") else tokens[i+1]
                    for group in re.findall(r'\((.*?)\)', after):
                        all_values.append([val.strip() for val in group.split(",")])

            if not table_name or not columns or not all_values:
                print_error("Requête INSERT incomplète")
                return

            for values in all_values:
                if len(columns) != len(values):
                    print_error("Le nombre de colonnes et de valeurs ne correspondent pas")
                    continue
                record = {}
                for col, val in zip(columns, values):
                    if val.lower() == "null":
                        record[col] = None
                    elif val.lower() in ("true", "false"):
                        record[col] = val.lower() == "true"
                    elif val.isdigit():
                        record[col] = int(val)
                    else:
                        record[col] = val.strip("'")
                db_system.insert_record(table_name, record, user)

        elif command == "select":
            select_columns = tokens[1].value if len(tokens) > 1 else "*"
            table_name = find_token_value(tokens, "from")
            
            where_clause, group_by_clause, having_clause, order_by_clause, limit_clause = None, None, None, None, None
            for token in tokens:
                if token.value.lower().startswith("where"):
                    where_clause = token.value
                elif token.value.lower().startswith("group by"):
                    group_by_clause = token.value
                elif token.value.lower().startswith("having"):
                    having_clause = token.value
                elif token.value.lower().startswith("order by"):
                    order_by_clause = token.value
                elif token.value.lower().startswith("limit"):
                    limit_clause = token.value
            
            conditions = {}
            if where_clause:
                cond_parts = where_clause.split()[1:]
                for clause in cond_parts:
                    if "=" in clause:
                        k, v = clause.split("=")
                        conditions[k] = v.strip("'")
            
            result = db_system.query(table_name, conditions, user)
            
            if group_by_clause:
                group_columns = group_by_clause.split()[2:]
                grouped_result = {}
                for row in result:
                    key = tuple(row[col] for col in group_columns)
                    grouped_result.setdefault(key, []).append(row)
                result = [{"group": key, "rows": rows} for key, rows in grouped_result.items()]
            
            if having_clause:
                having_condition = having_clause.split(" ", 1)[1]
                result = [group for group in result if eval(having_condition, {"group": group["group"], "rows": group["rows"]})]
            
            if order_by_clause:
                order_columns = order_by_clause.split()[2:]
                reverse = "desc" in order_columns[-1].lower()
                result.sort(key=lambda x: tuple(x[col] for col in order_columns if col.lower() != "desc"), reverse=reverse)
            
            if limit_clause:
                limit = int(limit_clause.split()[1])
                result = result[:limit]
            
            print_response(json.dumps(result, indent=2), "info")
        elif command == "update":
            table_name = tokens[1].value if len(tokens) > 1 else None
            set_clause = find_token_value(tokens, "set")
            where_clause = find_token_value(tokens, "where")
            conditions = {}
            if where_clause:
                for clause in where_clause.split():
                    if "=" in clause:
                        k, v = clause.split("=")
                        conditions[k] = v.strip("'")
            db_system.update_record(table_name, set_clause, conditions, user)
        elif command == "alter" and "table" in query_lower:
            table_name = find_token_value(tokens, "table")
            action = tokens[3].value.upper() if len(tokens) > 3 else None
            column_name = tokens[4].value if len(tokens) > 4 else None
            column_type = tokens[5].value if action and action.lower() == "add" and len(tokens) > 5 else None
            default_value = None
            if action and action.lower() == "add" and "default" in query_lower:
                default_idx = query_lower.index("default") + len("default")
                default_value = query[default_idx:].strip().strip("'")
            db_system.alter_table(table_name, action, column_name, column_type, default_value, user)
        elif command == "drop" and "table" in query_lower:
            table_name = find_token_value(tokens, "table")
            db_system.drop_table(table_name, user)
        elif command == "drop" and "database" in query_lower:
            db_name = find_token_value(tokens, "database")
            db_system.drop_database(db_name, user)
        elif command == "truncate":
            table_name = tokens[1].value if len(tokens) > 1 else None
            table_path = db_system._get_table_path(table_name)
            if table_path:
                table_data = read_msgpack(table_path, db_system.metadata_key)
                table_data["rows"] = []
                write_msgpack(table_path, table_data, db_system.metadata_key)
                print_success(LANGUAGES[db_system.language]["table_truncated"].format(table=table_name))
            else:
                print_error(LANGUAGES[db_system.language]["table_not_found"])
        elif command == "describe":
            table_name = tokens[1].value if len(tokens) > 1 else None
            table_path = db_system._get_table_path(table_name)
            if table_path:
                table_data = read_msgpack(table_path, db_system.metadata_key)
                columns = table_data.get("columns", {})
                constraints = table_data.get("constraints", {})
                defaults = table_data.get("defaults", {})
                nullable = table_data.get("nullable", {})
                primary_keys = table_data.get("primary_keys", [])
                unique_keys = table_data.get("unique_keys", [])

                table_structure = [
                    [
                        col,
                        typ,
                        defaults.get(col, "None"),
                        "YES" if nullable.get(col, False) else "NO",
                        "YES" if col in primary_keys else "NO",
                        "YES" if col in unique_keys else "NO"
                    ]
                    for col, typ in columns.items()
                ]

                constraints_structure = [[name, definition] for name, definition in constraints.items()]

                structure = "Table Structure:\n"
                structure += tabulate(
                    table_structure,
                    headers=["Column", "Type", "Default Value", "Nullable", "Primary Key", "Unique"],
                    tablefmt="grid"
                )

                if constraints:
                    structure += "\n\nConstraints:\n"
                    structure += tabulate(
                        constraints_structure,
                        headers=["Constraint Name", "Definition"],
                        tablefmt="grid"
                    )

                print_response(LANGUAGES[db_system.language]["table_structure"].format(table=table_name, structure=structure), "info")
            else:
                print_error(LANGUAGES[db_system.language]["table_not_found"])
        elif command == "show" and "databases" in query_lower:
            db_system.show_databases()
        elif command == "show" and "tables" in query_lower:
            db_system.show_tables()
        elif command == "create" and "user" in query_lower:
            if user["role"] != "admin":
                print_error(LANGUAGES[db_system.language]["permission_denied"])
                return
            username = tokens[2].value if len(tokens) > 1 else None
            password = tokens[3].value.strip("'") if len(tokens) > 3 else None
            role = tokens[4].value if len(tokens) > 5 else "user"
            db_system.user_manager.create_user(username, password, role, caller_role=user["role"])
        elif command == "alter" and "user" in query_lower:
            if user["role"] != "admin":
                print_error(LANGUAGES[db_system.language]["permission_denied"])
                return
            username = tokens[1].value if len(tokens) > 1 else None
            new_password = next((t.value.split("=")[1].strip("'") for t in tokens if t.value.startswith("password")), None)
            new_role = next((t.value.split("=")[1] for t in tokens if t.value.startswith("role")), None)
            db_system.user_manager.alter_user(username, new_password, new_role, caller_role=user["role"])
        elif command == "drop" and "user" in query_lower:
            if user["role"] != "admin":
                print_error(LANGUAGES[db_system.language]["permission_denied"])
                return
            username = tokens[1].value if len(tokens) > 1 else None
            db_system.user_manager.drop_user(username, caller_role=user["role"])
        elif command == "grant":
            if user["role"] != "admin":
                print_error(LANGUAGES[db_system.language]["permission_denied"])
                return
            username = tokens[1].value if len(tokens) > 1 else None
            permissions = tokens[3].value.split(",") if len(tokens) > 3 else []
            db_table = tokens[5].value.split(".") if len(tokens) > 5 else []
            if len(db_table) < 2:
                print_error("Database and table must be specified")
                return
            db_system.user_manager.grant(username, db_table[0], db_table[1], permissions, caller_role=user["role"])
        elif command == "revoke":
            if user["role"] != "admin":
                print_error(LANGUAGES[db_system.language]["permission_denied"])
                return
            username = tokens[1].value if len(tokens) > 1 else None
            permissions = tokens[3].value.split(",") if len(tokens) > 3 else []
            db_table = tokens[5].value.split(".") if len(tokens) > 5 else []
            if len(db_table) < 2:
                print_error("Database and table must be specified")
                return
            db_system.user_manager.revoke(username, db_table[0], db_table[1], permissions, caller_role=user["role"])
        elif command == "join":
            table1 = tokens[1].value if len(tokens) > 1 else None
            table2 = tokens[3].value if len(tokens) > 3 else None
            condition = find_token_value(tokens, "on")
            result = db_system.join_tables(table1, table2, condition, user)
            print_response(json.dumps(result, indent=2), "info")
        elif command == "create" and "index" in query_lower:
            table_name = tokens[3].value if len(tokens) > 3 else None
            column_name = tokens[5].value if len(tokens) > 5 else None
            db_system.create_index(table_name, column_name, user)
        elif command == "backup":
            db_system.backup_manager.backup()
        elif command == "restore":
            backup_file = tokens[1].value if len(tokens) > 1 else None
            db_system.backup_manager.restore(backup_file)
        elif command == "set" and "language" in query_lower:
            lang = tokens[2].value.lower() if len(tokens) > 2 else None
            db_system.set_language(lang)
        elif command == "train" and "nlp" in query_lower and "model" in query_lower:
            training_data_file = tokens[3].value if len(tokens) > 3 else None
            nlp_model.train(training_data_file)
        elif command == "with":
            cte_definitions = []
            main_query = None
            if "as" in query_lower:
                cte_parts = query_lower.split("as")
                for i in range(0, len(cte_parts) - 1, 2):
                    cte_name = cte_parts[i].strip().split()[-1]
                    cte_query = cte_parts[i + 1].strip().split("select")[0]
                    cte_definitions.append((cte_name, cte_query))
                main_query = "select" + query_lower.split("select")[-1]
            for cte_name, cte_query in cte_definitions:
                db_system.create_cte(cte_name, cte_query, user)
            execute_query(main_query, db_system, user)
        elif command in ["union", "intersect", "except"]:
            queries = query_lower.split(command)
            if len(queries) != 2:
                print_error(f"Syntax error in {command.upper()} query")
                return
            result1 = db_system.query_raw(queries[0].strip(), user)
            result2 = db_system.query_raw(queries[1].strip(), user)
            if command == "union":
                result = result1 + [row for row in result2 if row not in result1]
            elif command == "intersect":
                result = [row for row in result1 if row in result2]
            elif command == "except":
                result = [row for row in result1 if row not in result2]
            print_response(json.dumps(result, indent=2), "info")
        elif command == "grant" and "all privileges" in query_lower:
            username = find_token_value(tokens, "to")
            if not username:
                print_error("Nom d'utilisateur manquant pour GRANT ALL PRIVILEGES.")
                return
            db_system.user_manager.grant_all_privileges(username, user)
        elif command == "revoke" and "all privileges" in query_lower:
            username = find_token_value(tokens, "from")
            if not username:
                print_error("Nom d'utilisateur manquant pour REVOKE ALL PRIVILEGES.")
                return
            db_system.user_manager.revoke_all_privileges(username, user)
        elif command == "savepoint":
            savepoint_name = tokens[1].value if len(tokens) > 1 else None
            if not savepoint_name:
                print_error("Nom de savepoint manquant.")
                return
            db_system.transaction_manager.create_savepoint(savepoint_name, user)
        elif command == "rollback" and "to savepoint" in query_lower:
            savepoint_name = find_token_value(tokens, "savepoint")
            if not savepoint_name:
                print_error("Nom de savepoint manquant pour ROLLBACK TO SAVEPOINT.")
                return
            db_system.transaction_manager.rollback_to_savepoint(savepoint_name, user)
        elif command == "release" and "savepoint" in query_lower:
            savepoint_name = find_token_value(tokens, "savepoint")
            if not savepoint_name:
                print_error("Nom de savepoint manquant pour RELEASE SAVEPOINT.")
                return
            db_system.transaction_manager.release_savepoint(savepoint_name, user)
        elif command == "merge":
            target_table = find_token_value(tokens, "into")
            source_table = find_token_value(tokens, "using")
            on_condition = find_token_value(tokens, "on")
            when_matched = find_token_value(tokens, "when matched then")
            when_not_matched = find_token_value(tokens, "when not matched then")
            if not (target_table and source_table and on_condition):
                print_error("Syntax error in MERGE statement. Usage: MERGE INTO ... USING ... ON ...")
                return
            try:
                db_system.merge_records(target_table, source_table, on_condition, when_matched, when_not_matched, user)
                print_success(LANGUAGES[db_system.language]["merge_completed"].format(table=target_table))
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "select" and "as of" in query_lower:
            table_name = find_token_value(tokens, "from")
            timestamp = find_token_value(tokens, "as of")
            if not (table_name and timestamp):
                print_error("Syntax error: SELECT ... FROM ... AS OF <timestamp>")
                return
            try:
                result = db_system.time_travel_query(table_name, timestamp, user)
                print_response(json.dumps(result, indent=2), "info")
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "alter" and "add data masking" in query_lower:
            table_name = find_token_value(tokens, "table")
            column_name = find_token_value(tokens, "add")
            mask_function = find_token_value(tokens, "using")
            if not (table_name and column_name and mask_function):
                print_error("Syntax error: ALTER TABLE ... ADD DATA MASKING ON ... USING ...")
                return
            try:
                db_system.add_data_masking(table_name, column_name, mask_function, user)
                print_success(LANGUAGES[db_system.language]["data_masking_added"].format(column=column_name, table=table_name))
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "alter" and "enable row level security" in query_lower:
            table_name = find_token_value(tokens, "table")
            if not table_name:
                print_error("Syntax error: ALTER TABLE ... ENABLE ROW LEVEL SECURITY")
                return
            try:
                db_system.enable_row_level_security(table_name, user)
                print_success(LANGUAGES[db_system.language]["row_level_security_enabled"].format(table=table_name))
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "select" and "over" in query_lower:
            select_columns = tokens[1].value if len(tokens) > 1 else "*"
            table_name = find_token_value(tokens, "from")
            partition_by_clause = find_token_value(tokens, "partition by")
            order_by_clause = find_token_value(tokens, "order by")
            if not table_name:
                print_error("Syntax error: SELECT ... FROM ... OVER ...")
                return
            try:
                result = db_system.query_with_window_function(table_name, select_columns, partition_by_clause, order_by_clause, user)
                print_response(json.dumps(result, indent=2), "info")
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "select" and "json_table" in query_lower:
            table_name = find_token_value(tokens, "from")
            json_column = find_token_value(tokens, "json_table")
            path = find_token_value(tokens, "path")
            columns = find_token_value(tokens, "columns")
            if not (table_name and json_column and path and columns):
                print_error("Syntax error: SELECT ... JSON_TABLE(...)")
                return
            try:
                result = db_system.json_table(table_name, json_column, path, columns, user)
                print_response(json.dumps(result, indent=2), "info")
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["json_table_error"].format(error=str(e)))
        elif command == "with" and "recursive" in query_lower:
            cte_name = find_token_value(tokens, "with")
            anchor_query = find_token_value(tokens, "as")
            recursive_query = find_token_value(tokens, "union all")
            main_query = query_lower.split("select")[-1]
            if not (cte_name and anchor_query and recursive_query and main_query):
                print_error("Syntax error: WITH RECURSIVE ...")
                return
            try:
                result = db_system.recursive_cte(cte_name, anchor_query, recursive_query, main_query, user)
                print_response(json.dumps(result, indent=2), "info")
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["recursive_cte_completed"].format(cte_name=cte_name))
        elif command == "savepoint":
            savepoint_name = tokens[1].value if len(tokens) > 1 else None
            if not savepoint_name:
                print_error("Nom de savepoint manquant.")
                return
            try:
                db_system.transaction_manager.create_savepoint(savepoint_name, user)
                print_success(LANGUAGES[db_system.language]["savepoint_created"].format(savepoint_name=savepoint_name))
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "rollback" and "to savepoint" in query_lower:
            savepoint_name = find_token_value(tokens, "savepoint")
            if not savepoint_name:
                print_error("Nom de savepoint manquant pour ROLLBACK TO SAVEPOINT.")
                return
            try:
                db_system.transaction_manager.rollback_to_savepoint(savepoint_name, user)
                print_success(LANGUAGES[db_system.language]["savepoint_rolled_back"].format(savepoint_name=savepoint_name))
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "release" and "savepoint" in query_lower:
            savepoint_name = find_token_value(tokens, "savepoint")
            if not savepoint_name:
                print_error("Nom de savepoint manquant pour RELEASE SAVEPOINT.")
                return
            try:
                db_system.transaction_manager.release_savepoint(savepoint_name, user)
                print_success(LANGUAGES[db_system.language]["savepoint_released"].format(savepoint_name=savepoint_name))
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "join" and "full outer" in query_lower:
            table1 = tokens[1].value if len(tokens) > 1 else None
            table2 = tokens[3].value if len(tokens) > 3 else None
            condition = find_token_value(tokens, "on")
            if not (table1 and table2 and condition):
                print_error("Syntax error: JOIN ... FULL OUTER ... ON ...")
                return
            try:
                result = db_system.full_outer_join(table1, table2, condition, user)
                print_response(json.dumps(result, indent=2), "info")
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "select" and "division" in query_lower:
            table1 = find_token_value(tokens, "from")
            table2 = find_token_value(tokens, "division")
            if not (table1 and table2):
                print_error("Syntax error: SELECT ... FROM ... DIVISION ...")
                return
            try:
                result = db_system.division_operation(table1, table2, user)
                print_response(json.dumps(result, indent=2), "info")
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "select" and "/*+" in query_lower:
            hints = re.findall(r'/\*\+(.+?)\*/', query)
            query_without_hints = re.sub(r'/\*\+.+?\*/', '', query)
            try:
                result = db_system.execute_with_hints(query_without_hints, hints, user)
                print_response(json.dumps(result, indent=2), "info")
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "create" and "enum" in query_lower:
            enum_name = find_token_value(tokens, "enum")
            values = find_token_value(tokens, "values")
            if not (enum_name and values):
                print_error("Syntax error: CREATE ENUM ... VALUES ...")
                return
            try:
                db_system.create_enum(enum_name, values, user)
                print_success(LANGUAGES[db_system.language]["enum_created"].format(enum=enum_name))
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "create" and "sequence" in query_lower:
            sequence_name = find_token_value(tokens, "sequence")
            start_value = find_token_value(tokens, "start with")
            increment_by = find_token_value(tokens, "increment by")
            if not sequence_name:
                print_error("Syntax error: CREATE SEQUENCE ...")
                return
            try:
                db_system.create_sequence(sequence_name, start_value, increment_by, user)
                print_success(LANGUAGES[db_system.language]["sequence_created"].format(sequence=sequence_name))
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "create" and "foreign data wrapper" in query_lower:
            fdw_name = find_token_value(tokens, "foreign data wrapper")
            handler = find_token_value(tokens, "handler")
            validator = find_token_value(tokens, "validator")
            if not (fdw_name and handler and validator):
                print_error("Syntax error: CREATE FOREIGN DATA WRAPPER ... HANDLER ... VALIDATOR ...")
                return
            try:
                db_system.create_foreign_data_wrapper(fdw_name, handler, validator, user)
                print_success(LANGUAGES[db_system.language]["fdw_created"].format(fdw=fdw_name))
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "create" and "tablespace" in query_lower:
            tablespace_name = find_token_value(tokens, "tablespace")
            location = find_token_value(tokens, "location")
            if not (tablespace_name and location):
                print_error("Syntax error: CREATE TABLESPACE ... LOCATION ...")
                return
            try:
                db_system.create_tablespace(tablespace_name, location, user)
                print_success(LANGUAGES[db_system.language]["tablespace_created"].format(tablespace=tablespace_name))
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "begin":
            try:
                db_system.transaction_manager.begin(user)
                print_success(LANGUAGES[db_system.language]["nested_transaction_started"])
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "commit":
            try:
                db_system.transaction_manager.commit(user)
                print_success(LANGUAGES[db_system.language]["nested_transaction_committed"])
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "rollback":
            try:
                db_system.transaction_manager.rollback(user)
                print_success(LANGUAGES[db_system.language]["nested_transaction_rolled_back"])
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "create" and "materialized view" in query_lower:
            view_name = find_token_value(tokens, "view")
            select_query = query[query.lower().index("as")+2:].strip()
            try:
                db_system.create_materialized_view(view_name, select_query, user)
                print_success(LANGUAGES[db_system.language]["materialized_view_created"].format(view_name=view_name))
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "refresh" and "materialized view" in query_lower:
            view_name = find_token_value(tokens, "view")
            try:
                db_system.refresh_materialized_view(view_name, user)
                print_success(LANGUAGES[db_system.language]["materialized_view_refreshed"].format(view_name=view_name))
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "shard" and "table" in query_lower:
            table_name = find_token_value(tokens, "table")
            shard_column = find_token_value(tokens, "by")
            num_shards = int(find_token_value(tokens, "en"))
            try:
                db_system.shard_table(table_name, shard_column, num_shards, user)
                print_success(LANGUAGES[db_system.language]["table_sharded"].format(table=table_name, num_shards=num_shards, shard_column=shard_column))
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        elif command == "create" and "secondary index" in query_lower:
            idx_name = find_token_value(tokens, "index")
            table_name = find_token_value(tokens, "on")
            columns_str = query[query.index("(")+1:query.index(")")]
            columns = [c.strip() for c in columns_str.split(",")]
            try:
                db_system.create_secondary_index(idx_name, table_name, columns, user)
                print_success(LANGUAGES[db_system.language]["index_created"].format(index_type="SECONDARY", table=table_name, column=",".join(columns)))
            except Exception as e:
                print_error(LANGUAGES[db_system.language]["query_failed"].format(error=str(e)))
        else:
            print_error(LANGUAGES[db_system.language]["command_not_supported"])
    except Exception as e:
        db_system.logger.error(f"Erreur lors de l'exécution de la requête '{query}': {str(e)}")
        print_error(LANGUAGES[db_system.language]["error"].format(error=str(e)))