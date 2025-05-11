import os
from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from config.config import CONFIG
from config.language import LANGUAGES
from query.query_parser import execute_query
from utils.file_utils import get_obfuscated_name, read_msgpack
from utils.logger_utils import print_error

box_style = Style.from_dict({
    "border":          "#777777",
    "title":           "#2d578b bold",
    "version":         "#666666",
    "separator":       "#4a90d9",
    "icon":            "#ffd700 bold",
    "input":           "#e6e6e6",
    "database":        "#98fb98 bold",
    "completion-menu.completion": "bg:#333333 #e6e6e6",
    "completion-menu.completion.current": "bg:#444444 #ffffff",
})

def get_suggestions(db_system):
    suggestions = [
        "USE", "CREATE DATABASE", "CREATE TABLE", "INSERT INTO", "SELECT * FROM",
        "UPDATE", "ALTER TABLE", "DROP TABLE", "DROP DATABASE", "CREATE USER",
        "ALTER USER", "DROP USER", "GRANT", "REVOKE", "JOIN", "CREATE INDEX",
        "BACKUP", "RESTORE", "SET LANGUAGE", "TRUNCATE TABLE", "DESCRIBE",
        "SHOW DATABASES", "SHOW TABLES", "TRAIN NLP MODEL"
    ]
    if db_system.current_database:
        db_obf = get_obfuscated_name(db_system.current_database, db_system.key)
        if db_obf:
            metadata_path = os.path.join(CONFIG["DATA_DIR"], db_obf, ".metadata.msgpack")
            metadata = read_msgpack(metadata_path, db_system.metadata_key)
            if metadata:  # Vérifier si les métadonnées existent
                tables = list(metadata.get("tables", {}).keys())
                suggestions.extend([f"SELECT * FROM {table}" for table in tables])
                suggestions.extend([f"INSERT INTO {table}" for table in tables])
                suggestions.extend([f"UPDATE {table}" for table in tables])
                suggestions.extend([f"ALTER TABLE {table}" for table in tables])
                suggestions.extend([f"DROP TABLE {table}" for table in tables])
                suggestions.extend([f"JOIN {table}" for table in tables])
                suggestions.extend([f"CREATE INDEX ON {table}" for table in tables])
                suggestions.extend([f"GRANT SELECT ON {db_system.current_database}.{table}" for table in tables])
                suggestions.extend([f"REVOKE SELECT ON {db_system.current_database}.{table}" for table in tables])
        suggestions.extend(["TRUNCATE TABLE", "DESCRIBE table_name"])
    return suggestions

def user_prompt(user, db_system):
    history = FileHistory(CONFIG["HISTORY_FILE"])
    session = PromptSession(history=history, style=box_style)

    version = "1.2.1"
    prompt_message = [
        ("class:border", "┏"), 
        ("class:border", "━" * 60), 
        ("class:border", "┓\n"),
        ("class:border", "┃ "),
        ("class:title", "λ Database Pro "),
        ("class:version", f"[Version {version}] (lang='{db_system.language}')"),
        ("class:border"," " * 17),
        ("class:border", "┃\n"),
        ("class:border", "┣"), 
        ("class:separator", "┅" * 60), 
        ("class:border", "┫\n"),
        ("class:border", "┃ "),
        ("class:icon", "➤"),
        ("class:border", " "),
        ("class:input", LANGUAGES[db_system.language]["command_title"]),
        ("class:border"," " * 44),
        ("class:border", "┃\n"),
        ("class:border", "┃ "),
        ("class:icon", "➜"),
        ("class:border", " "),
        ("class:database", user['username']),
        ("class:border", "@"),
        ("class:database", db_system.current_database or LANGUAGES[db_system.language]["none"]),
        ("class:border", " $ "),
    ]

    while True:
        try:
            with patch_stdout():
                completer = WordCompleter(
                    get_suggestions(db_system), 
                    ignore_case=True,
                    sentence=True
                )
                query = session.prompt(
                    prompt_message,
                    completer=completer,
                    complete_while_typing=True,
                    bottom_toolbar=HTML(
                        f'<style fg="#777777">{LANGUAGES[db_system.language]["user"]}: {user["role"]} | {LANGUAGES[db_system.language]["db"]}: {db_system.current_database or LANGUAGES[db_system.language]["none"]}</style>'
                    ),
                    rprompt=HTML('<style fg="#777777">Ctrl+D pour quitter</style>')
                ).strip()
                
                if query == LANGUAGES[db_system.language]["exit"]:
                    break
                if query:
                    execute_query(query, db_system, user)
        
        except KeyboardInterrupt:
            break
        except EOFError:
            break
        except Exception as e:
            print_error(f"Erreur: {str(e)} (code: {e.__class__.__name__})")

def execute_query(query, db_system, user):
    """
    Execute a query and handle the result.
    """
    try:
        query = query.strip()  # Remove the `.upper()` to preserve case sensitivity
        if query.lower().startswith("select"):
            table_name = query.split("from")[1].strip().split()[0]
            results = db_system.query(table_name, user=user)
            if results:
                print_formatted_text(HTML(f"<b>Résultats :</b> {results}"))
            else:
                print_formatted_text(HTML("<b>Aucun résultat trouvé.</b>"))
        else:
            print_error(LANGUAGES[db_system.language]["command_not_supported"])
    except Exception as e:
        print_error(f"Erreur lors de l'exécution de la requête : {str(e)}")