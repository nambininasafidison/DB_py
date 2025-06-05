#!/usr/bin/env python3
import sys
import argparse
import getpass
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
from interface.cli import user_prompt
from config.language import LANGUAGES
import config.config as conf
from config.initialization import initialize_system
from managers.session_manager import SessionManager
from utils.logger_utils import print_error, print_success

def main():
    parser = argparse.ArgumentParser(description="Système de base de données")
    parser.add_argument("-u", "--user", help="Nom d'utilisateur")
    parser.add_argument("-p", "--password", help="Mot de passe")
    args = parser.parse_args()

    try:
        db_system = initialize_system()
        if not db_system:
            print_error(LANGUAGES[conf.global_language]["initialization_failed"].format(error="System initialization failed."))
            sys.exit(1)

        session_manager = SessionManager()
        created_admin = False
        admin_pass = None

        if not db_system.user_manager.user_exists("admin"):
            admin_pass = getpass.getpass(LANGUAGES[conf.global_language]["create_admin_password"])
            db_system.user_manager.create_user("admin", admin_pass, role="admin", caller_role="admin")
            print_success(LANGUAGES[conf.global_language]["admin_created"])
            created_admin = True

        try:
            if args.user and args.password:
                user = db_system.user_manager.authenticate(args.user, args.password)
                if user:
                    token = session_manager.create_session(user["username"])
                    print_success(LANGUAGES[db_system.language]["welcome"].format(username=user["username"]))
                    user_prompt(user, db_system)
                else:
                    print_error(LANGUAGES[conf.global_language]["auth_failed"])
            else:
                if created_admin:
                    user = db_system.user_manager.authenticate("admin", admin_pass)
                else:
                    # Demander le mot de passe admin si l'utilisateur admin existe déjà
                    admin_pass = getpass.getpass(LANGUAGES[conf.global_language]["admin_password"])
                    user = db_system.user_manager.authenticate("admin", admin_pass)
                if user:
                    token = session_manager.create_session(user["username"])
                    print_success(LANGUAGES[db_system.language]["welcome"].format(username=user["username"]))
                    user_prompt(user, db_system)
                else:
                    print_error(LANGUAGES[conf.global_language]["auth_failed"])
        except Exception as e:
            print_error(LANGUAGES[conf.global_language]["critical_error"].format(error=str(e)))
    except Exception as e:
        print_error(LANGUAGES[conf.global_language]["initialization_failed"].format(error=str(e)))
        sys.exit(1)

if __name__ == "__main__":
    main()
