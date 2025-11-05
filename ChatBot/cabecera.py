"""Módulo que define la estructura de la cabecera (header) usada en las PDU.

la `Cabecera` agrupa metadatos necesarios para
enviar/recibir mensajes (identificador de protocolo, tipo, prioridad,
marca temporal, id de mensaje y campos de integridad como CRC32).

La cabecera se serializa con struct en big-endian para consistencia en red.
"""

import struct  # módulo para empaquetar y desempaquetar datos binarios
import time    # módulo para obtener la hora actual (marca temporal)


class Cabecera:  # clase que representa la cabecera (header) de la PDU
    """Representa la cabecera (header) de la PDU.

    Campos (resumen en mis palabras):
    - version (1 byte)
    - id_protocolo (2 bytes)
    - tipo_operacion (1 byte)
    - prioridad (1 byte)
    - marca_tiempo (8 bytes)
    - id_mensaje (4 bytes)
    - longitud_carga (2 bytes)
    - crc32 (4 bytes)

    Total: 23 bytes empacados en formato big-endian.
    """

    # Formato usado para pack/unpack: big-endian, tipos y tamaños fijos
    STRUCT_FMT = '!B H B B d I H I'  # formato struct en big-endian para pack/unpack
    # campos:      B H B B d I H I -> 1 2 1 1 8 4 2 4 bytes respectivamente

    def __init__(self,
                 version=1,               # versión del protocolo 1 byte
                 id_protocolo=0x0000,     # identificador del protocolo 2 bytes
                 tipo_operacion=1,        # tipo de operación 1 byte
                 prioridad=0,             # prioridad del mensaje 1 byte
                 marca_tiempo=None,      # marca de tiempo float -> 8 bytes
                 id_mensaje=0,           # identificador del mensaje 4 bytes
                 longitud_carga=0,       # longitud de la carga útil 2 bytes
                 crc32=0):               # CRC32 de la carga 4 bytes
        # Asignaciones simples, con marca temporal por defecto si no se suministra
        self.version = version
        self.id_protocolo = id_protocolo
        self.tipo_operacion = tipo_operacion
        self.prioridad = prioridad
        # Si no dan marca_tiempo, usar el tiempo actual (float de segundos)
        self.marca_tiempo = marca_tiempo if marca_tiempo else time.time()
        self.id_mensaje = id_mensaje
        self.longitud_carga = longitud_carga
        self.crc32 = crc32

    def a_bytes(self):
        """Convierte la cabecera en bytes lista para concatenar con la carga.

        Explicación corta: usamos struct.pack con STRUCT_FMT para obtener una
        representación binaria portátil en red (big-endian).
        """
        return struct.pack(
            self.STRUCT_FMT,
            self.version,
            self.id_protocolo,
            self.tipo_operacion,
            self.prioridad,
            self.marca_tiempo,
            self.id_mensaje,
            self.longitud_carga,
            self.crc32
        )

    @classmethod
    def desde_bytes(cls, data):
        """Reconstruye una Cabecera a partir de la secuencia de bytes recibida.

        Nota: se espera que `data` tenga exactamente el tamaño de la cabecera.
        """
        campos = struct.unpack(cls.STRUCT_FMT, data)
        return cls(*campos)

    @classmethod
    def tamaño(cls):
        """Devuelve el tamaño en bytes de la cabecera serializada."""
        return struct.calcsize(cls.STRUCT_FMT)

    def __repr__(self):
        # Representación breve para depuración y logs
        return (f"Cabecera(v={self.version}, proto=0x{self.id_protocolo:04X}, "
                f"tipo={self.tipo_operacion}, prio={self.prioridad}, "
                f"id={self.id_mensaje}, len={self.longitud_carga}, crc=0x{self.crc32:08X})")
