import struct  # módulo para empaquetar y desempaquetar datos binarios
import time    # módulo para obtener la hora actual (marca temporal)

class Cabecera:  # clase que representa la cabecera (header) de la PDU
    # Documentación de la clase: describe los campos y el tamaño total
    """Representa la cabecera (header) de la PDU.
    Contiene la información de control del mensaje.
    Campos:
    - version (1 byte)
    - id_protocolo (2 bytes)
    - tipo_operacion (1 byte)
    - prioridad (1 byte)
    - marca_tiempo (8 bytes)
    - id_mensaje (4 bytes)
    - longitud_carga (2 bytes)
    - crc32 (4 bytes)
    Total: 23 bytes
    """

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
        self.version = version                  # asigna versión
        self.id_protocolo = id_protocolo        # asigna id de protocolo
        self.tipo_operacion = tipo_operacion    # asigna tipo de operación
        self.prioridad = prioridad              # asigna prioridad
        self.marca_tiempo = marca_tiempo if marca_tiempo else time.time()  # asigna marca temporal si no se proporciona, usa time.time()
        self.id_mensaje = id_mensaje            # asigna id del mensaje
        self.longitud_carga = longitud_carga    # asigna longitud de la carga útil
        self.crc32 = crc32                      # asigna crc32

    def a_bytes(self):  # convierte la instancia en una secuencia de bytes lista para enviar
        """Convierte la cabecera en bytes para su envío."""
        return struct.pack(
            self.STRUCT_FMT,     # usa el formato definido arriba
            self.version,        # empaqueta version
            self.id_protocolo,   # empaqueta id_protocolo
            self.tipo_operacion, # empaqueta tipo_operacion
            self.prioridad,      # empaqueta prioridad
            self.marca_tiempo,   # empaqueta marca_tiempo float
            self.id_mensaje,     # empaqueta id_mensaje
            self.longitud_carga, # empaqueta longitud_carga
            self.crc32           # empaqueta crc32
        )

    @classmethod
    def desde_bytes(cls, data):  # recrea una Cabecera desde bytes recibidos
        """Reconstruye una cabecera a partir de bytes recibidos."""
        campos = struct.unpack(cls.STRUCT_FMT, data)  # desempaqueta según STRUCT_FMT
        return cls(*campos)  # crea y devuelve una instancia usando los campos desempaquetados

    @classmethod
    def tamaño(cls):  # devuelve el tamaño en bytes que ocupa la cabecera serializada
        """Devuelve el tamaño de la cabecera en bytes."""
        return struct.calcsize(cls.STRUCT_FMT)  # calcula el tamaño usando calcsize

    def __repr__(self):  # representación legible para debugging
        return (f"Cabecera(v={self.version}, proto=0x{self.id_protocolo:04X}, "
                f"tipo={self.tipo_operacion}, prio={self.prioridad}, "
                f"id={self.id_mensaje}, len={self.longitud_carga}, crc=0x{self.crc32:08X})")
