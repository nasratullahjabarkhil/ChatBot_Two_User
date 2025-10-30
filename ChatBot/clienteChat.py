import threading
import zlib
from mensaje import Mensaje
from estadoMensaje import EstadoMensaje

class ClienteChat:
    """
    Clase que representa al usuario del sistema de chat.
    Maneja envío, recepción y simulación de lectura.
    """

    def __init__(self, nombre_usuario, gestor, protocol_id=0x215A):
        self.nombre = nombre_usuario
        self.gestor = gestor
        self.protocol_id = protocol_id
        self.estados = {}
        self.stop_event = threading.Event()
        # Estado de turnos
        self.waiting_for_response_id = None  # si envié solicitud
        self.pending_request_id = None       # si debo responder

    def iniciar_recepcion(self):
        """Lanza un hilo para recibir mensajes."""
        hilo = threading.Thread(target=self._bucle_recepcion, daemon=True)
        hilo.start()

    def _bucle_recepcion(self):
        """Escucha continuamente mensajes entrantes."""
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
                print(f"\n[{self.nombre}] Recibido: {mensaje.texto()}")
                # Notificación RECIBIDO
                ack = self._crear_control(mensaje.id_mensaje, Mensaje.TIPO_RECIBIDO)
                self.gestor.enviar_bytes(ack.codificar())
                # Enforzar turno
                if self.pending_request_id is not None:
                    print(f"[{self.nombre}] Solicitud ya pendiente (id={self.pending_request_id}). Ignorando nueva.")
                elif self.waiting_for_response_id is not None:
                    print(f"[{self.nombre}] Esperando respuesta (id={self.waiting_for_response_id}). No se acepta nueva solicitud.")
                else:
                    self.pending_request_id = mensaje.id_mensaje
                    print(f"[{self.nombre}] Debe responder a id={self.pending_request_id}.")

            elif tipo == Mensaje.TIPO_RECIBIDO:
                self.estados[mensaje.id_mensaje] = EstadoMensaje.RECIBIDO
                print(f"[{self.nombre}] Confirmación: mensaje {mensaje.id_mensaje} recibido.")

            elif tipo == Mensaje.TIPO_LEIDO:
                self.estados[mensaje.id_mensaje] = EstadoMensaje.LEIDO
                print(f"[{self.nombre}] Confirmación: mensaje {mensaje.id_mensaje} leído.")
            elif tipo == Mensaje.TIPO_RESPUESTA:
                if self.waiting_for_response_id == mensaje.id_mensaje:
                    print(f"[{self.nombre}] Respuesta recibida para {mensaje.id_mensaje}: {mensaje.texto()}")
                    self.waiting_for_response_id = None
                else:
                    print(f"[{self.nombre}] RESPUESTA inesperada para id {mensaje.id_mensaje}: {mensaje.texto()}")

    def enviar_texto(self, texto):
        """Envía una nueva solicitud o responde si hay una pendiente."""
        try:
            if self.pending_request_id is not None:
                # responder
                resp = Mensaje(texto, id_protocolo=self.protocol_id, id_mensaje=self.pending_request_id, tipo_operacion=Mensaje.TIPO_RESPUESTA)
                self.gestor.enviar_bytes(resp.codificar())
                print(f"[{self.nombre}] Respuesta enviada a (id={self.pending_request_id})")
                self.pending_request_id = None
            else:
                if self.waiting_for_response_id is not None:
                    print(f"[{self.nombre}] Bloqueado. Esperando respuesta (id={self.waiting_for_response_id}).")
                    return
                mensaje = Mensaje(texto, id_protocolo=self.protocol_id)
                self.gestor.enviar_bytes(mensaje.codificar())
                self.estados[mensaje.id_mensaje] = EstadoMensaje.ENVIADO
                self.waiting_for_response_id = mensaje.id_mensaje
                print(f"[{self.nombre}] Mensaje enviado (id={mensaje.id_mensaje}), esperando respuesta.")
        except Exception as e:
            # si había un mensaje creado anteriormente, márcalo como error si aplica
            print(f"[{self.nombre}] Error al enviar mensaje: {e}")

    def _crear_control(self, id_mensaje, tipo):
        """Crea un mensaje de control (sin texto)."""
        # Create a control message without consuming a new global id
        msg = Mensaje("", id_protocolo=self.protocol_id, id_mensaje=id_mensaje, tipo_operacion=tipo)
        msg.payload = b''
        msg.cabecera.longitud_carga = 0
        msg.cabecera.crc32 = zlib.crc32(msg.payload) & 0xffffffff
        return msg

    # Eliminada simulación de lectura para respetar turnos estrictos

    def detener(self):
        """Detiene la recepción y cierra conexión."""
        self.stop_event.set()
        self.gestor.cerrar()

