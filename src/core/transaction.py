import os
import threading
import time

from config.config import CONFIG
from query.query_parser import execute_query
from utils.logger_utils import print_error


class Transaction:
    def __init__(self, log_file=os.path.join(CONFIG.get("DATA_DIR", ""), "wal.log")):
        self.log_file = log_file
        self.operations = []
        self.committed = False
        self.lock = threading.Lock()

    def execute(self, operation):
        with self.lock:
            self.operations.append(operation)
            with open(self.log_file, "ab") as f:
                f.write(f"{time.time()}:{operation}\n".encode())

    def commit(self, db_system, user):
        with self.lock:
            if self.committed:
                print_error("Transaction already committed")
                return
            if not self.operations:
                print_error("No operations to commit")
                return
            for op in self.operations:
                execute_query(op, db_system, user)
            self.committed = True
            open(self.log_file, "wb").close()

    def rollback(self):
        with self.lock:
            if not self.operations:
                print_error("No operations to rollback")
                return
            if not self.committed:
                self.operations.clear()
                open(self.log_file, "wb").close()