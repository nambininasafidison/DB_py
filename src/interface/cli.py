import os
try:
    from prompt_toolkit import PromptSession, print_formatted_text
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.patch_stdout import patch_stdout
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.styles import Style
    _PTK_AVAILABLE = True
except Exception:
    PromptSession = None
    WordCompleter = None
    FileHistory = None
    patch_stdout = lambda: (lambda: None)
    class HTML:
        def __init__(self, text):
            self.text = text
    class Style:
        @staticmethod
        def from_dict(d):
            return None
    _PTK_AVAILABLE = False
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
            if metadata:
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

def is_exit(query, lang):
    """Return True if query should be treated as an exit command.
    Accepts localized 'exit' from LANGUAGES, plus common variants (exit, quit, q), case-insensitive.
    """
    if not query:
        return False
    q = query.strip().lower()
    variants = {"exit", "quit", "q"}
    try:
        loc = LANGUAGES.get(lang, {}).get('exit', '')
        if loc:
            variants.add(loc.strip().lower())
    except Exception:
        pass
    return q in variants


def user_prompt(user, db_system):
    version = "1.2.1"
    import sys

    use_ptk = _PTK_AVAILABLE and sys.stdin.isatty()

    if use_ptk:
        try:
            history = FileHistory(CONFIG["HISTORY_FILE"])
        except Exception:
            use_ptk = False

    if use_ptk:
        session = PromptSession(history=history, style=box_style)

        while True:
            try:
                with patch_stdout():
                    completer = WordCompleter(
                        get_suggestions(db_system), 
                        ignore_case=True,
                        sentence=True
                    )
                    query = session.prompt(
                        prompt_message(db_system.language, db_system.current_database, user['username'], version, db_system),
                        completer=completer,
                        complete_while_typing=True,
                        bottom_toolbar=HTML(
                            f'<style fg="#777777">{LANGUAGES[db_system.language]["user"]}: {user["role"]} | {LANGUAGES[db_system.language]["db"]}: {db_system.current_database or LANGUAGES[db_system.language]["none"]}</style>'
                        ),
                        rprompt=HTML('<style fg="#777777">Ctrl+D pour quitter</style>')
                    ).strip()
                    
                    if is_exit(query, db_system.language):
                        break
                    if query:
                        try:
                            print_formatted_text('')
                        except Exception:
                            print('')
                        execute_query(query, db_system, user)

            except KeyboardInterrupt:
                break
            except EOFError:
                break
            except Exception as e:
                print_error(f"Erreur: {str(e)} (code: {e.__class__.__name__})")
    else:
        print_formatted = print
        prompt_str = "db> "
        while True:
            try:
                query = input(prompt_str).strip()
                if not query:
                    continue
                if is_exit(query, db_system.language):
                    break
                try:
                    print_formatted('', end='')
                except Exception:
                    try:
                        print('')
                    except Exception:
                        pass
                execute_query(query, db_system, user)
            except (KeyboardInterrupt, EOFError):
                print_formatted("\nBye.")
                break
            except Exception as e:
                print_error(f"Erreur: {str(e)} (code: {e.__class__.__name__})")

def prompt_message(lang, db, user, version, db_system):
    if lang not in LANGUAGES:
        lang = "en"
    return [
        ("class:border", "┏"), 
        ("class:border", "━" * 60), 
        ("class:border", "┓\n"),
        ("class:border", "┃ "),
        ("class:title", "λ Database Pro "),
        ("class:version", f"[Version {version}] (lang='{lang}')"),
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
        ("class:database", user),
        ("class:border", "@"),
        ("class:database", db or LANGUAGES[db_system.language]["none"]),
        ("class:border", " $ "),
    ]