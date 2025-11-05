"""Módulo que define la estructura de los mensajes (PDU) usados en el chat.

Un `Mensaje` es la unión de una `Cabecera` y una carga
útil (payload). El módulo cuida generación de ids thread-safe, cómputo de
CRC32 e (de)serialización.
"""

import zlib
import time
import threading
from cabecera import Cabecera


class Mensaje:
    """Representa una PDU (cabecera + carga útil).

    Notas del autor:
    - Tiene tipos fijos (ENVIO, RECIBIDO, LEIDO, ERROR, RESPUESTA).
    - Genera ids incrementales protegidos por un lock para seguridad entre hilos.
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
        """Crea un Mensaje.

        - `texto` puede ser str o bytes (se convierte a bytes si es str).
        - Si `id_mensaje` se suministra, se reutiliza (útil para ACKs/controles).
        - `tipo_operacion` por defecto es TIPO_ENVIO si no se indica.
        """
        # Aceptar texto como str o bytes; almacenar siempre bytes en payload
        self.payload = texto.encode('utf-8') if isinstance(texto, str) else texto
        self.id_protocolo = id_protocolo
        self.prioridad = prioridad

        # Generación de id único si no se proporciona (thread-safe)
        if id_mensaje is None:
            with Mensaje._id_lock:
                self.id_mensaje = Mensaje._next_id
                Mensaje._next_id += 1
        else:
            self.id_mensaje = id_mensaje

        # CRC32 sobre el payload para verificar integridad en el receptor
        self.crc32 = zlib.crc32(self.payload) & 0xffffffff

        op = tipo_operacion if tipo_operacion is not None else Mensaje.TIPO_ENVIO

        # Construir la cabecera con los metadatos calculados
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
        """Convierte bytes en una instancia de Mensaje.

        Valida CRC y reconstruye la instancia sin pasar por __init__ (para
        no generar un nuevo id automáticamente).
        """
        header_size = Cabecera.tamaño()
        header = Cabecera.desde_bytes(data[:header_size])
        payload = data[header_size: header_size + header.longitud_carga]

        # Verificar integridad con CRC32
        if zlib.crc32(payload) & 0xffffffff != header.crc32:
            raise ValueError("Error: CRC no coincide")

        # Crear la instancia manualmente para evitar la lógica de generación de id
        instancia = cls.__new__(cls)
        instancia.payload = payload
        instancia.cabecera = header
        instancia.id_protocolo = header.id_protocolo
        instancia.prioridad = header.prioridad
        instancia.id_mensaje = header.id_mensaje
        instancia.crc32 = header.crc32
        return instancia

    def texto(self):
        """Devuelve el texto decodificado del payload o una marca si es binario."""
        try:
            return self.payload.decode('utf-8')
        except:
            return "<binario>"

    def __repr__(self):
        return f"Mensaje(id={self.id_mensaje}, len={len(self.payload)}, texto={self.texto()})"
