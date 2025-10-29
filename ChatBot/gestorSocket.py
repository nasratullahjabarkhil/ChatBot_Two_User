import socket
import struct
import threading

class GestorSocket:
    """
    Se encarga de gestionar la conexión por socket entre dos usuarios.
    Puede actuar como servidor o cliente.
    """

    def __init__(self, nombre="nodo"):
        self.sock = None
        self.conn = None
        self.nombre = nombre
        self.lock_send = threading.Lock()

    def iniciar_servidor(self, host='0.0.0.0', puerto=5000):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, puerto))
        self.sock.listen(1)
        print(f"[{self.nombre}] Servidor esperando conexión en {host}:{puerto}")
        self.conn, _ = self.sock.accept()
        print(f"[{self.nombre}] Cliente conectado")

    def conectar(self, host, puerto):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, puerto))
        self.conn = self.sock
        print(f"[{self.nombre}] Conectado a {host}:{puerto}")

    def enviar_bytes(self, data: bytes):
        """Envía los datos precedidos por su longitud (4 bytes)."""
        with self.lock_send:
            longitud = struct.pack("!I", len(data))
            self.conn.sendall(longitud + data)

    def recibir_bytes(self) -> bytes:
        """Recibe los datos respetando el prefijo de longitud."""
        cabecera = self._recibir_exactamente(4)
        if not cabecera:
            return b''
        longitud = struct.unpack("!I", cabecera)[0]
        return self._recibir_exactamente(longitud)

    def _recibir_exactamente(self, n):
        """Recibe exactamente n bytes."""
        datos = b''
        while len(datos) < n:
            parte = self.conn.recv(n - len(datos))
            if not parte:
                return b''
            datos += parte
        return datos

    def cerrar(self):
        """Cierra la conexión."""
        if self.conn:
            self.conn.close()
        if self.sock and self.sock is not self.conn:
            self.sock.close()
