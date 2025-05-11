import json
import threading
import socket
import ssl

import config.config as conf
from config.language import LANGUAGES
from utils.logger_utils import print_error

class Replicator:
    def __init__(self, nodes, ssl_cert, ssl_key):
        self.nodes = nodes
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.context.load_cert_chain(certfile=ssl_cert, keyfile=ssl_key)

    def replicate(self, data):
        for node in self.nodes:
            threading.Thread(target=self._send_to_node, args=(node, data), daemon=True).start()

    def _send_to_node(self, node, data):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                conn = self.context.wrap_socket(sock, server_hostname=node[0])
                conn.connect(node)
                conn.sendall(json.dumps(data).encode())
                conn.close()
        except Exception as e:
            print_error(LANGUAGES[conf.global_language]["replication_error"].format(node=node, error=str(e)))