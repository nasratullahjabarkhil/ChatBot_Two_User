"""Módulo que encapsula operaciones básicas de socket para el chat.
`GestorSocket` es una capa fina sobre sockets TCP que
facilita aceptar conexiones (modo servidor) o conectarse a un servidor
(modo cliente), enviar/recibir bloques de bytes con prefijo de longitud y
cerrar la conexión de forma segura. Incluye un lock para que múltiples
hilos no intercalen llamadas a send.
"""

import socket
import struct
import threading


class GestorSocket:
    """Administra la conexión TCP entre dos nodos.

    Uso típico (mis palabras):
    - Crear instancia: GestorSocket(nombre='mi-nodo')
    - Si actúa como servidor: llamar a `iniciar_servidor(host, puerto)`
      (bloquea hasta aceptar una conexión) y luego usar `enviar_bytes`/`recibir_bytes`.
    - Si actúa como cliente: llamar a `conectar(host, puerto)` y usar los mismos métodos.

    Atributos principales:
    - sock: socket de escucha o socket de cliente
    - conn: socket de conexión usable para I/O (aceptado o el mismo sock)
    - lock_send: lock para serializar envíos desde varios hilos
    """

    def __init__(self, nombre="nodo"):
        # sock: socket usado para escuchar o el socket cliente
        self.sock = None
        # conn: socket con el que realmente se envían/reciben bytes
        self.conn = None
        self.nombre = nombre
        # Lock para evitar mezclas de bytes cuando varios hilos llaman a enviar
        self.lock_send = threading.Lock()

    def iniciar_servidor(self, host='0.0.0.0', puerto=5000):
        """Pone el proceso en modo servidor y espera una conexión entrante.

        Nota: este método bloquea en accept() hasta que un cliente se conecta.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Permitir reusar la dirección para evitar 'address already in use' en pruebas rápidas
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, puerto))
        self.sock.listen(1)
        print(f"[{self.nombre}] Servidor esperando conexión en {host}:{puerto}")
        # accept devuelve (conn, addr); guardamos la conexión para I/O
        self.conn, _ = self.sock.accept()
        print(f"[{self.nombre}] Cliente conectado")

    def conectar(self, host, puerto):
        """Conecta como cliente a un servidor remoto.

        Después de llamar, `self.conn` estará listo para enviar/recibir.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, puerto))
        # En modo cliente usamos el mismo socket para conn
        self.conn = self.sock
        print(f"[{self.nombre}] Conectado a {host}:{puerto}")

    def enviar_bytes(self, data: bytes):
        """Envía `data` precedido por su longitud en 4 bytes (network order).

        Uso: empaquetamos la longitud con struct '!I' y hacemos sendall para
        garantizar que todos los bytes lleguen. El lock evita que varios
        hilos mezclen prefijo+payload.
        """
        with self.lock_send:
            longitud = struct.pack("!I", len(data))
            self.conn.sendall(longitud + data)

    def recibir_bytes(self) -> bytes:
        """Recibe un bloque de bytes cuya longitud viene prefijada (4 bytes).

        Devuelve b'' si la conexión se cerró (EOF).
        """
        cabecera = self._recibir_exactamente(4)
        if not cabecera:
            return b''
        longitud = struct.unpack("!I", cabecera)[0]
        return self._recibir_exactamente(longitud)

    def _recibir_exactamente(self, n):
        """Recibe exactamente `n` bytes o b'' si la conexión se corta.

        Implementación clásica que acumula `recv()` hasta completar `n` bytes.
        """
        datos = b''
        while len(datos) < n:
            parte = self.conn.recv(n - len(datos))
            if not parte:
                # EOF; el otro extremo cerró la conexión
                return b''
            datos += parte
        return datos

    def cerrar(self):
        """Cierra la conexión y el socket de escucha si procede.

        Se asegura de no cerrar dos veces el mismo descriptor cuando
        `conn` y `sock` apuntan al mismo objeto (modo cliente).
        """
        if self.conn:
            self.conn.close()
        if self.sock and self.sock is not self.conn:
            self.sock.close()
