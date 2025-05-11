from utils.logger_utils import print_error, print_success


class TransactionManager:
    def __init__(self):
        self.transactions = {}

    def create_savepoint(self, savepoint_name, user):
        if user["username"] not in self.transactions:
            self.transactions[user["username"]] = {"savepoints": {}}
        self.transactions[user["username"]]["savepoints"][savepoint_name] = list(self.transactions[user["username"]].get("operations", []))
        print_success(f"Savepoint {savepoint_name} created.")

    def rollback_to_savepoint(self, savepoint_name, user):
        if user["username"] not in self.transactions or savepoint_name not in self.transactions[user["username"]]["savepoints"]:
            print_error(f"Savepoint {savepoint_name} not found.")
            return
        self.transactions[user["username"]]["operations"] = self.transactions[user["username"]]["savepoints"][savepoint_name]
        print_success(f"Rolled back to savepoint {savepoint_name}.")

    def release_savepoint(self, savepoint_name, user):
        if user["username"] not in self.transactions or savepoint_name not in self.transactions[user["username"]]["savepoints"]:
            print_error(f"Savepoint {savepoint_name} not found.")
            return
        del self.transactions[user["username"]]["savepoints"][savepoint_name]
        print_success(f"Savepoint {savepoint_name} released.")

    def begin_nested_transaction(self, user):
        if user["username"] not in self.transactions:
            self.transactions[user["username"]] = {"savepoints": {}, "nested": []}
        self.transactions[user["username"]]["nested"].append(list(self.transactions[user["username"]].get("operations", [])))
        print_success("Nested transaction started.")

    def commit_nested_transaction(self, user):
        if user["username"] not in self.transactions or not self.transactions[user["username"]]["nested"]:
            print_error("No nested transaction to commit.")
            return
        self.transactions[user["username"]]["nested"].pop()
        print_success("Nested transaction committed.")

    def rollback_nested_transaction(self, user):
        if user["username"] not in self.transactions or not self.transactions[user["username"]]["nested"]:
            print_error("No nested transaction to rollback.")
            return
        try:
            self.transactions[user["username"]]["operations"] = self.transactions[user["username"]]["nested"].pop()
            print_success("Nested transaction rolled back.")
        except Exception as e:
            print_error(f"Erreur lors du rollback de la transaction imbriquée : {str(e)}")
