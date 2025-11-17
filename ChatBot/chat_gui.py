"""
Interfaz gráfica de chat (Tkinter) con control de turno de mensajes.

Este módulo define la clase ChatGUI que gestiona la ventana, la entrada
de usuario, la conexión de red mediante GestorSocket y el protocolo de
mensajería (envío, ACK, respuesta, leido).
"""

import tkinter as tk
from tkinter import scrolledtext
import threading
import zlib
import random

from gestorSocket import GestorSocket
from mensaje import Mensaje


class ChatGUI:
    """Interfaz gráfica para el cliente/servidor del chat.

    Atributos clave:
    - gestor: instancia de GestorSocket que maneja la conexión.
    - stop_event: evento para detener el hilo de recepción.
    - protocol_id: id del protocolo usado en los mensajes.
    - waiting_for_response_id: id del mensaje enviado para el que se espera respuesta.
    - pending_request_id: id de la petición entrante que aún no se ha respondido.
    """

    def __init__(self, root):
        """Inicializa la interfaz, widgets y variables internas.

        root: objeto Tk principal.
        """
        self.root = root
        root.title('ChatBot')

        # Panel superior con configuraciones (nombre, host, puerto)
        top = tk.Frame(root)
        top.pack(padx=8, pady=6, fill='x')

        tk.Label(top, text='Nombre:').grid(row=0, column=0)
        self.name_entry = tk.Entry(top, width=12)
        self.name_entry.insert(0, 'Usuario')
        self.name_entry.grid(row=0, column=1, padx=4)

        tk.Label(top, text='Host:').grid(row=0, column=2)
        self.host_entry = tk.Entry(top, width=12)
        self.host_entry.insert(0, '127.0.0.1')
        self.host_entry.grid(row=0, column=3, padx=4)

        tk.Label(top, text='Puerto:').grid(row=0, column=4)
        self.port_entry = tk.Entry(top, width=6)
        self.port_entry.insert(0, '5000')
        self.port_entry.grid(row=0, column=5, padx=4)

        # Botones de control
        self.start_srv_btn = tk.Button(top, text='Iniciar Servidor', command=self.start_server)
        self.start_srv_btn.grid(row=1, column=0, columnspan=2, pady=6)

        self.connect_btn = tk.Button(top, text='Conectar', command=self.connect)
        self.connect_btn.grid(row=1, column=2, columnspan=2, pady=6)

        # Etiqueta de estado
        self.status_label = tk.Label(top, text='Desconectado', fg='red')
        self.status_label.grid(row=1, column=4, columnspan=2)

        # Área de texto para mostrar mensajes (solo lectura desde el UI)
        self.text = scrolledtext.ScrolledText(root, state='disabled', width=70, height=20)
        self.text.pack(padx=8, pady=6)

        # Panel inferior con entrada de mensaje y botón enviar
        bottom = tk.Frame(root)
        bottom.pack(padx=8, pady=6, fill='x')

        self.msg_entry = tk.Entry(bottom)
        self.msg_entry.pack(side='left', expand=True, fill='x', padx=(0, 6))
        # Permitir enviar con Enter
        self.msg_entry.bind('<Return>', lambda e: self.send_message())

        self.send_btn = tk.Button(bottom, text='Enviar', command=self.send_message, state='disabled')
        self.send_btn.pack(side='right')

        # Variables de red y control de hilos
        self.gestor = None
        self.recv_thread = None
        self.stop_event = threading.Event()
        # Identificador de protocolo: DNI 40609084A -> suma=31(0x1F) + letra A=65(0x41) = 0x1F41
        self.protocol_id = 0x1F41
        # Estado de turnos: solo un mensaje pendiente a la vez
        self.waiting_for_response_id = None  # si envié, espero RESPUESTA con este id
        self.pending_request_id = None       # si recibí ENVIO, debo responder a este id

    def log(self, text):
        """Inserta una línea en el área de texto de forma segura desde cualquier hilo.

        Usamos root.after para ejecutar la inserción en el hilo principal de Tk.
        """
        def _insert():
            self.text['state'] = 'normal'
            self.text.insert('end', text + '\n')
            self.text.see('end')
            self.text['state'] = 'disabled'
        self.root.after(0, _insert)

    def start_server(self):
        """Crea un GestorSocket que escucha como servidor en el puerto indicado.

        Inicia un hilo daemon para no bloquear la UI.
        """
        if self.gestor:
            return
        host = '127.0.0.1'
        puerto = int(self.port_entry.get())
        self.gestor = GestorSocket(nombre=self.name_entry.get())

        def srv_thread():
            try:
                usuario = self.name_entry.get()
                self.log(f'[{usuario}] Esperando conexión en {host}:{puerto}...')
                # Este método bloquea hasta aceptar una conexión
                self.gestor.iniciar_servidor(host=host, puerto=puerto)
                # Al aceptar la conexión, actualizamos la UI
                self.on_connected()
            except Exception as e:
                self.log(f'[{usuario}] Error: {e}')

        threading.Thread(target=srv_thread, daemon=True).start()
        # Evitar iniciar varios servidores desde la misma interfaz
        self.start_srv_btn['state'] = 'disabled'

    def connect(self):
        """Conecta como cliente al host/puerto configurado.

        Si la conexión falla, deja `self.gestor` a None y registra el error.
        """
        usuario = self.name_entry.get()
        if self.gestor:
            return
        host = self.host_entry.get()
        puerto = int(self.port_entry.get())
        self.gestor = GestorSocket(self.name_entry.get())

        try:
            self.gestor.conectar(host, puerto)
            self.on_connected()
        except Exception as e:
            self.log(f'[{usuario}] Error al conectar: {e}')
            self.gestor = None

    def on_connected(self):
        """Configuraciones tras establecer la conexión: habilitar UI y lanzar el hilo receptor."""
        usuario = self.name_entry.get()
        self.log(f'[{usuario}] Conectado')
        self.status_label['text'] = 'Conectado'
        self.status_label['fg'] = 'green'
        # Habilitar botón enviar (se controlará antes del envío si es permiso real)
        self.send_btn['state'] = 'normal'
        # Deshabilitar la posibilidad de iniciar otro servidor en esta instancia
        self.start_srv_btn['state'] = 'disabled'
        # iniciar hilo de recepción
        self.stop_event.clear()
        self.recv_thread = threading.Thread(target=self._bucle_recepcion, daemon=True)
        self.recv_thread.start()

    def _bucle_recepcion(self):
        """Bucle que corre en hilo separado para recibir mensajes y procesarlos.

        - Decodifica el mensaje usando Mensaje.decodificar
        - Maneja tipos: ENVIO (solicitud), RECIBIDO (ACK), LEIDO, RESPUESTA
        - Controla el turno: no aceptar nuevas peticiones si hay una pendiente
        """
        usuario = self.name_entry.get()
        while not self.stop_event.is_set():
            try:
                data = self.gestor.recibir_bytes()
                if not data:
                    # conexión cerrada desde el otro extremo
                    self.log(f'[{usuario}] Conexión cerrada por el otro extremo')
                    break
                mensaje = Mensaje.decodificar(data)
            except Exception as e:
                self.log(f'[{usuario}] Error al recibir/decodificar: {e}')
                continue

            tipo = mensaje.cabecera.tipo_operacion
            if tipo == Mensaje.TIPO_ENVIO:
                # Mensaje entrante que requiere respuesta (turno de quien recibe)
                self.log(f"[{mensaje.cabecera.id_mensaje}] {mensaje.texto()}")
                # enviar ACK (tipo RECIBIDO) para confirmar recepción
                ack = Mensaje("", id_protocolo=self.protocol_id, id_mensaje=mensaje.id_mensaje, tipo_operacion=Mensaje.TIPO_RECIBIDO)
                ack.payload = b''
                ack.cabecera.longitud_carga = 0
                ack.cabecera.crc32 = zlib.crc32(ack.payload) & 0xffffffff
                try:
                    self.gestor.enviar_bytes(ack.codificar())
                except Exception as e:
                    self.log(f'[{usuario}] Error enviando ACK: {e}')

                # Programar envío automático de confirmación de lectura (LEIDO)
                def _send_leido():
                    try:
                        leido = Mensaje("", id_protocolo=self.protocol_id, id_mensaje=mensaje.id_mensaje, tipo_operacion=Mensaje.TIPO_LEIDO)
                        leido.payload = b''
                        leido.cabecera.longitud_carga = 0
                        leido.cabecera.crc32 = zlib.crc32(leido.payload) & 0xffffffff
                        self.gestor.enviar_bytes(leido.codificar())
                        self.log(f'[{usuario}] Enviado LEIDO para {mensaje.cabecera.id_mensaje}')
                    except Exception as e:
                        self.log(f'[{usuario}] Error enviando LEIDO: {e}')

                delay = random.uniform(1, 5)
                threading.Timer(delay, _send_leido).start()

                # Enforzar turno: no aceptar una nueva petición si ya hay una pendiente
                if self.pending_request_id is not None:
                    self.log(f'[{usuario}] Ya existe una solicitud pendiente (id={self.pending_request_id}). Ignorando nueva petición.')
                elif self.waiting_for_response_id is not None:
                    # No deberíamos recibir nuevas solicitudes si estamos esperando una respuesta
                    self.log(f'[{usuario}] Esperando respuesta (id={self.waiting_for_response_id}). No se acepta nueva solicitud.')
                else:
                    # Marcar que debemos responder a este id; permitir teclear respuesta
                    self.pending_request_id = mensaje.cabecera.id_mensaje
                    self.root.after(0, lambda: self.status_label.config(text=f'Responder a {self.pending_request_id}', fg='blue'))
                    # habilitar enviar para poder responder
                    self.root.after(0, lambda: self.send_btn.config(state='normal'))

            elif tipo == Mensaje.TIPO_RECIBIDO:
                # ACK de que un mensaje enviado por nosotros fue recibido
                self.log(f'[{usuario}] Confirmación: mensaje {mensaje.cabecera.id_mensaje} recibido')
            elif tipo == Mensaje.TIPO_LEIDO:
                # Confirmación de lectura
                self.log(f'[{usuario}] Confirmación: mensaje {mensaje.cabecera.id_mensaje} leído')
            elif tipo == Mensaje.TIPO_RESPUESTA:
                # Respuesta a una petición que nosotros enviamos
                if self.waiting_for_response_id == mensaje.cabecera.id_mensaje:
                    self.log(f'[{usuario}] Respuesta recibida para {mensaje.cabecera.id_mensaje}: {mensaje.texto()}')
                    # Liberar el bloqueo de turno
                    self.waiting_for_response_id = None
                    # habilitar envío de nuevas peticiones y restaurar estado
                    self.root.after(0, lambda: self.send_btn.config(state='normal'))
                    self.root.after(0, lambda: self.status_label.config(text='Conectado', fg='green'))
                else:
                    # Respuesta inesperada (puede ser de un id antiguo o erróneo)
                    self.log(f'[{usuario}] RESPUESTA inesperada para id {mensaje.cabecera.id_mensaje}: {mensaje.texto()}')

        # cierre del bucle: limpiar recursos y actualizar UI
        self.stop()

    def send_message(self):
        """Envía un mensaje o una respuesta dependiendo del estado de turnos.

        - Si hay `pending_request_id`, enviamos una RESPUESTA a ese id.
        - Si no, enviamos una nueva petición (TIPO_ENVIO) siempre que no esperemos respuesta.
        """
        usuario = self.name_entry.get()

        texto = self.msg_entry.get()
        if not texto or not self.gestor:
            return
        try:
            if self.pending_request_id is not None:
                # Debemos responder a una solicitud pendiente
                resp = Mensaje(texto, id_protocolo=self.protocol_id, id_mensaje=self.pending_request_id, tipo_operacion=Mensaje.TIPO_RESPUESTA)
                self.gestor.enviar_bytes(resp.codificar())
                self.log(f'[{usuario}] Respuesta enviada a ({self.pending_request_id}): {texto}')
                self.pending_request_id = None
                # tras responder, quedamos libres para iniciar nueva petición
                self.root.after(0, lambda: self.status_label.config(text='Conectado', fg='green'))
                # botón enviar queda habilitado (ya lo estaba para responder)
            else:
                # Solo enviar nueva petición si no esperamos respuesta previa
                if self.waiting_for_response_id is not None:
                    self.log(f'[{usuario}] Aún esperando respuesta del mensaje {self.waiting_for_response_id}. No puedes enviar.')
                    return
                msg = Mensaje(texto, id_protocolo=self.protocol_id)
                self.gestor.enviar_bytes(msg.codificar())
                # Guardar id del mensaje para saber que estamos a la espera
                self.waiting_for_response_id = msg.id_mensaje
                self.log(f'[{usuario}] ({msg.id_mensaje}) {texto} [esperando respuesta]')
                # deshabilitar para bloquear hasta recibir respuesta
                self.root.after(0, lambda: self.send_btn.config(state='disabled'))
                self.root.after(0, lambda: self.status_label.config(text=f'Esperando respuesta {msg.id_mensaje}', fg='orange'))
        except Exception as e:
            self.log(f'[{usuario}] Error al enviar: {e}')
        finally:
            # Limpiar entrada de texto siempre
            self.msg_entry.delete(0, 'end')

    def stop(self):
        """Cierra la conexión y actualiza la interfaz para reflejar el estado desconectado."""
        self.stop_event.set()
        try:
            if self.gestor:
                self.gestor.cerrar()
        except Exception:
            pass
        self.gestor = None
        self.root.after(0, lambda: self.status_label.config(text='Desconectado', fg='red'))
        self.root.after(0, lambda: self.send_btn.config(state='disabled'))
        # Permitir iniciar servidor de nuevo cuando la conexión se cierra
        self.root.after(0, lambda: self.start_srv_btn.config(state='normal'))


def main():
    """Punto de entrada para ejecutar la interfaz de chat como programa principal."""
    root = tk.Tk()
    gui = ChatGUI(root)

    def on_close():
        # Asegurar el cierre ordenado de sockets/hilos antes de destruir la ventana
        gui.stop()
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', on_close)
    root.mainloop()


if __name__ == '__main__':
    main()
