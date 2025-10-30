import zlib
import time
import threading
from cabecera import Cabecera

class Mensaje:
    """
    Representa una PDU (cabecera + carga útil).
    """

    # Tipos de operación
    TIPO_ENVIO = 1
    TIPO_RECIBIDO = 2
    TIPO_LEIDO = 3
    TIPO_ERROR = 4
    TIPO_RESPUESTA = 5

    # Contador de clase protegido por lock para generar IDs incrementales
    _id_lock = threading.Lock()
    _next_id = 1

    def __init__(self, texto="", id_protocolo=0x0000, prioridad=0, id_mensaje=None, tipo_operacion=None):
        """Permite opcionalmente especificar id_mensaje y tipo_operacion para crear
        mensajes de control sin consumir IDs del generador."""
        self.payload = texto.encode('utf-8') if isinstance(texto, str) else texto
        self.id_protocolo = id_protocolo
        self.prioridad = prioridad
        if id_mensaje is None:
            # Generar un id único por instancia de forma thread-safe
            with Mensaje._id_lock:
                self.id_mensaje = Mensaje._next_id
                Mensaje._next_id += 1
        else:
            self.id_mensaje = id_mensaje

        self.crc32 = zlib.crc32(self.payload) & 0xffffffff

        op = tipo_operacion if tipo_operacion is not None else Mensaje.TIPO_ENVIO

        self.cabecera = Cabecera(
            version=1,
            id_protocolo=self.id_protocolo,
            tipo_operacion=op,
            prioridad=self.prioridad,
            marca_tiempo=time.time(),
            id_mensaje=self.id_mensaje,
            longitud_carga=len(self.payload),
            crc32=self.crc32
        )

    def codificar(self):
        """Devuelve los bytes del mensaje completo (cabecera + payload)."""
        return self.cabecera.a_bytes() + self.payload

    @classmethod
    def decodificar(cls, data):
        """Convierte bytes en una instancia de Mensaje."""
        header_size = Cabecera.tamaño()
        header = Cabecera.desde_bytes(data[:header_size])
        payload = data[header_size: header_size + header.longitud_carga]

        # Verificar integridad
        if zlib.crc32(payload) & 0xffffffff != header.crc32:
            raise ValueError("Error: CRC no coincide")

        instancia = cls.__new__(cls)
        instancia.payload = payload
        instancia.cabecera = header
        instancia.id_protocolo = header.id_protocolo
        instancia.prioridad = header.prioridad
        instancia.id_mensaje = header.id_mensaje
        instancia.crc32 = header.crc32
        return instancia

    def texto(self):
        """Devuelve el texto decodificado del payload."""
        try:
            return self.payload.decode('utf-8')
        except:
            return "<binario>"

    def __repr__(self):
        return f"Mensaje(id={self.id_mensaje}, len={len(self.payload)}, texto={self.texto()})"
