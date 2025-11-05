"""Cliente de chat (lógica de envío/recepción) con control de turnos.

Este módulo define la clase ClienteChat que interactúa con un
`GestorSocket` (pasado como `gestor`) para enviar y recibir mensajes
seguros mediante la clase `Mensaje`. Incluye control de turnos para
evitar que ambas partes envíen peticiones simultáneas.
"""

import threading
import zlib
from mensaje import Mensaje
from estadoMensaje import EstadoMensaje


class ClienteChat:
    """Representa a un participante del chat.

    Gestiona el envío/recepción de mensajes, estados (ENVIADO/RECIBIDO/LEIDO)
    y la lógica de turnos para asegurar que sólo haya una petición pendiente.
    """

    def __init__(self, nombre_usuario, gestor, protocol_id=0x215A):
        """Inicializa el cliente.

        nombre_usuario: nombre mostrado del participante.
        gestor: instancia de GestorSocket que realiza I/O de red.
        protocol_id: identificador de protocolo para los mensajes.
        """
        self.nombre = nombre_usuario
        self.gestor = gestor
        self.protocol_id = protocol_id
        # Mapa de estados por id de mensaje (EstadoMensaje)
        self.estados = {}
        # Evento para detener el hilo receptor
        self.stop_event = threading.Event()
        # Control de turnos: sólo una petición pendiente a la vez
        self.waiting_for_response_id = None  # id si envié una solicitud y espero RESPUESTA
        self.pending_request_id = None       # id si recibí una solicitud y debo responder

    def iniciar_recepcion(self):
        """Lanza un hilo daemon que ejecuta el bucle de recepción.

        No bloquea el hilo principal. El hilo terminará cuando se llame a
        `detener()` o `gestor.recibir_bytes()` devuelva None/empty.
        """
        hilo = threading.Thread(target=self._bucle_recepcion, daemon=True)
        hilo.start()

    def _bucle_recepcion(self):
        """Bucle que procesa mensajes entrantes.

        Para cada mensaje recibido:
        - decodifica usando Mensaje.decodificar
        - responde con ACK (TIPO_RECIBIDO) para mensajes de tipo ENVIO
        - gestiona turnos: marca `pending_request_id` cuando debe responder
        - actualiza `estados` para RECIBIDO/LEIDO
        - procesa RESPUESTA liberando `waiting_for_response_id` cuando corresponda
        """
        while not self.stop_event.is_set():
            data = self.gestor.recibir_bytes()
            if not data:
                print(f"[{self.nombre}] Conexión cerrada.")
                break

            try:
                mensaje = Mensaje.decodificar(data)
            except Exception as e:
                print(f"[{self.nombre}] Error al decodificar mensaje: {e}")
                continue

            tipo = mensaje.cabecera.tipo_operacion

            if tipo == Mensaje.TIPO_ENVIO:
                # Mensaje que solicita respuesta. Mostrar y enviar ACK (RECIBIDO).
                print(f"\n[{self.nombre}] Recibido: {mensaje.texto()}")
                ack = self._crear_control(mensaje.id_mensaje, Mensaje.TIPO_RECIBIDO)
                self.gestor.enviar_bytes(ack.codificar())

                # Enforzar turno: no aceptar nueva petición si ya hay una pendiente
                if self.pending_request_id is not None:
                    print(f"[{self.nombre}] Solicitud ya pendiente (id={self.pending_request_id}). Ignorando nueva.")
                elif self.waiting_for_response_id is not None:
                    print(f"[{self.nombre}] Esperando respuesta (id={self.waiting_for_response_id}). No se acepta nueva solicitud.")
                else:
                    # Guardar id para indicar que debemos responder a esta petición
                    self.pending_request_id = mensaje.id_mensaje
                    print(f"[{self.nombre}] Debe responder a id={self.pending_request_id}.")

            elif tipo == Mensaje.TIPO_RECIBIDO:
                # Confirmación de que un mensaje enviado fue recibido por el otro extremo
                self.estados[mensaje.id_mensaje] = EstadoMensaje.RECIBIDO
                print(f"[{self.nombre}] Confirmación: mensaje {mensaje.id_mensaje} recibido.")

            elif tipo == Mensaje.TIPO_LEIDO:
                # Confirmación de lectura
                self.estados[mensaje.id_mensaje] = EstadoMensaje.LEIDO
                print(f"[{self.nombre}] Confirmación: mensaje {mensaje.id_mensaje} leído.")

            elif tipo == Mensaje.TIPO_RESPUESTA:
                # Respuesta a una petición que nosotros enviamos previamente
                if self.waiting_for_response_id == mensaje.id_mensaje:
                    print(f"[{self.nombre}] Respuesta recibida para {mensaje.id_mensaje}: {mensaje.texto()}")
                    # Liberar bloqueo de espera
                    self.waiting_for_response_id = None
                else:
                    # Respuesta inesperada (puede corresponder a un id antiguo)
                    print(f"[{self.nombre}] RESPUESTA inesperada para id {mensaje.id_mensaje}: {mensaje.texto()}")

    def enviar_texto(self, texto):
        """Envía una nueva solicitud o responde si hay una pendiente.

        - Si `pending_request_id` está presente, envía una RESPUESTA a ese id.
        - Si no, crea y envía un Mensaje nuevo (ENVIO) si no estamos esperando respuesta.
        """
        try:
            if self.pending_request_id is not None:
                # Responder a la petición pendiente
                resp = Mensaje(texto, id_protocolo=self.protocol_id, id_mensaje=self.pending_request_id, tipo_operacion=Mensaje.TIPO_RESPUESTA)
                self.gestor.enviar_bytes(resp.codificar())
                print(f"[{self.nombre}] Respuesta enviada a (id={self.pending_request_id})")
                # Liberar el pending_request_id tras responder
                self.pending_request_id = None
            else:
                # Enviar nueva solicitud sólo si no estamos esperando respuesta
                if self.waiting_for_response_id is not None:
                    print(f"[{self.nombre}] Bloqueado. Esperando respuesta (id={self.waiting_for_response_id}).")
                    return
                mensaje = Mensaje(texto, id_protocolo=self.protocol_id)
                self.gestor.enviar_bytes(mensaje.codificar())
                # Marcar estado local y guardar id para esperar respuesta
                self.estados[mensaje.id_mensaje] = EstadoMensaje.ENVIADO
                self.waiting_for_response_id = mensaje.id_mensaje
                print(f"[{self.nombre}] Mensaje enviado (id={mensaje.id_mensaje}), esperando respuesta.")
        except Exception as e:
            # Manejo sencillo de errores: informar
            print(f"[{self.nombre}] Error al enviar mensaje: {e}")

    def _crear_control(self, id_mensaje, tipo):
        """Crea y retorna un mensaje de control (sin payload) para un id dado.

        No consume un nuevo id global: reutiliza `id_mensaje` suministrado.
        Se calcula la CRC32 del payload vacío.
        """
        msg = Mensaje("", id_protocolo=self.protocol_id, id_mensaje=id_mensaje, tipo_operacion=tipo)
        msg.payload = b''
        msg.cabecera.longitud_carga = 0
        msg.cabecera.crc32 = zlib.crc32(msg.payload) & 0xffffffff
        return msg

    # Eliminada simulación de lectura para respetar turnos estrictos

    def detener(self):
        """Detiene la recepción y cierra la conexión gestionada por `gestor`."""
        self.stop_event.set()
        self.gestor.cerrar()

