import uuid
import time

import config.config as conf
from config.language import LANGUAGES
from utils.logger_utils import print_success

class SessionManager:
    def __init__(self):
        self.sessions = {}

    def create_session(self, username):
        token = uuid.uuid4().hex
        expiry = time.time() + 3600
        self.sessions[token] = {"username": username, "expiry": expiry}
        print_success(LANGUAGES[conf.global_language]["session_started"].format(token=token))
        return token

    def validate_session(self, token):
        session = self.sessions.get(token)
        if session and session["expiry"] > time.time():
            return session["username"]
        return None

    def cleanup_sessions(self):
        current_time = time.time()
        expired_tokens = [token for token, session in self.sessions.items() if session["expiry"] <= current_time]
        for token in expired_tokens:
            del self.sessions[token]
        print_success(f"Cleaned up {len(expired_tokens)} expired sessions.")