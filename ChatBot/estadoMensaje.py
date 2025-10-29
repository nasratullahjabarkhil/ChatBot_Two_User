from enum import Enum, auto

class EstadoMensaje(Enum):
    """
    Representa los posibles estados de un mensaje
    dentro del protocolo de mensajería.
    """
    ENVIADO = auto()
    RECIBIDO = auto()
    LEIDO = auto()
    ERROR = auto()
