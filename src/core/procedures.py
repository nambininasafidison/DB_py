# Module pour la gestion des procédures stockées et fonctions utilisateur
import os
import pickle

class ProcedureManager:
    def __init__(self, procedures_dir):
        self.procedures_dir = procedures_dir
        os.makedirs(self.procedures_dir, exist_ok=True)

    def save_procedure(self, name, code, is_function=False):
        path = os.path.join(self.procedures_dir, f"{name}.proc")
        with open(path, "wb") as f:
            pickle.dump({"code": code, "is_function": is_function}, f)

    def load_procedure(self, name):
        path = os.path.join(self.procedures_dir, f"{name}.proc")
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return pickle.load(f)

    def list_procedures(self):
        return [f[:-5] for f in os.listdir(self.procedures_dir) if f.endswith(".proc")]

    def execute_procedure(self, name, context=None):
        proc = self.load_procedure(name)
        if not proc:
            raise Exception(f"Procédure {name} non trouvée.")
        local_ctx = context or {}
        exec(proc["code"], {}, local_ctx)
        return local_ctx.get("result", None)
