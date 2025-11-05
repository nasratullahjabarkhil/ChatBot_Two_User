"""Pequeño módulo que define los estados posibles de un mensaje.

aquí enumero las etapas por las que puede pasar un mensaje
desde que se envía hasta que es leído, más un estado de error.
"""

from enum import Enum, auto


class EstadoMensaje(Enum):
    """Estados de vida de un mensaje dentro del protocolo."""
    ENVIADO = auto()
    RECIBIDO = auto()
    LEIDO = auto()
    ERROR = auto()
