import threading
import random
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
                # Simular lectura aleatoria
                threading.Timer(random.uniform(1, 5),
                                self._simular_lectura, args=(mensaje,)).start()

            elif tipo == Mensaje.TIPO_RECIBIDO:
                self.estados[mensaje.id_mensaje] = EstadoMensaje.RECIBIDO
                print(f"[{self.nombre}] Confirmación: mensaje {mensaje.id_mensaje} recibido.")

            elif tipo == Mensaje.TIPO_LEIDO:
                self.estados[mensaje.id_mensaje] = EstadoMensaje.LEIDO
                print(f"[{self.nombre}] Confirmación: mensaje {mensaje.id_mensaje} leído.")

    def enviar_texto(self, texto):
        """Crea y envía un mensaje."""
        mensaje = Mensaje(texto, id_protocolo=self.protocol_id)
        try:
            self.gestor.enviar_bytes(mensaje.codificar())
            self.estados[mensaje.id_mensaje] = EstadoMensaje.ENVIADO
            print(f"[{self.nombre}] Mensaje enviado (id={mensaje.id_mensaje})")
        except Exception as e:
            self.estados[mensaje.id_mensaje] = EstadoMensaje.ERROR
            print(f"[{self.nombre}] Error al enviar mensaje: {e}")

    def _crear_control(self, id_mensaje, tipo):
        """Crea un mensaje de control (sin texto)."""
        # Create a control message without consuming a new global id
        msg = Mensaje("", id_protocolo=self.protocol_id, id_mensaje=id_mensaje, tipo_operacion=tipo)
        msg.payload = b''
        msg.cabecera.longitud_carga = 0
        msg.cabecera.crc32 = zlib.crc32(msg.payload) & 0xffffffff
        return msg

    def _simular_lectura(self, mensaje):
        """Simula la lectura del mensaje y notifica."""
        notificacion = self._crear_control(mensaje.id_mensaje, Mensaje.TIPO_LEIDO)
        self.gestor.enviar_bytes(notificacion.codificar())
        print(f"[{self.nombre}] Mensaje {mensaje.id_mensaje} marcado como leído.")

    def detener(self):
        """Detiene la recepción y cierra conexión."""
        self.stop_event.set()
        self.gestor.cerrar()

