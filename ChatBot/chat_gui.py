import tkinter as tk
from tkinter import scrolledtext
import threading
import random
import zlib

from gestorSocket import GestorSocket
from mensaje import Mensaje


class ChatGUI:
    def __init__(self, root):
        self.root = root
        root.title('ChatBot')

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

        self.start_srv_btn = tk.Button(top, text='Iniciar Servidor', command=self.start_server)
        self.start_srv_btn.grid(row=1, column=0, columnspan=2, pady=6)

        self.connect_btn = tk.Button(top, text='Conectar', command=self.connect)
        self.connect_btn.grid(row=1, column=2, columnspan=2, pady=6)

        self.status_label = tk.Label(top, text='Desconectado', fg='red')
        self.status_label.grid(row=1, column=4, columnspan=2)

        self.text = scrolledtext.ScrolledText(root, state='disabled', width=70, height=20)
        self.text.pack(padx=8, pady=6)

        bottom = tk.Frame(root)
        bottom.pack(padx=8, pady=6, fill='x')

        self.msg_entry = tk.Entry(bottom)
        self.msg_entry.pack(side='left', expand=True, fill='x', padx=(0, 6))
        self.msg_entry.bind('<Return>', lambda e: self.send_message())

        self.send_btn = tk.Button(bottom, text='Enviar', command=self.send_message, state='disabled')
        self.send_btn.pack(side='right')

        self.gestor = None
        self.recv_thread = None
        self.stop_event = threading.Event()
        self.protocol_id = 0x215A

    def log(self, text):
        def _insert():
            self.text['state'] = 'normal'
            self.text.insert('end', text + '\n')
            self.text.see('end')
            self.text['state'] = 'disabled'
        self.root.after(0, _insert)

    def start_server(self):
        if self.gestor:
            return
        host = '127.0.0.1'
        puerto = int(self.port_entry.get())
        self.gestor = GestorSocket(nombre=self.name_entry.get())

        def srv_thread():
            try:
                usuario = self.name_entry.get()
                self.log(f'[{usuario}] Esperando conexión en {host}:{puerto}...')
                self.gestor.iniciar_servidor(host=host, puerto=puerto)
                self.on_connected()
            except Exception as e:
                self.log(f'[{usuario}] Error: {e}')

        threading.Thread(target=srv_thread, daemon=True).start()
        self.start_srv_btn['state'] = 'disabled'

    def connect(self):
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
        usuario = self.name_entry.get()
        self.log(f'[{usuario}] Conectado')
        self.status_label['text'] = 'Conectado'
        self.status_label['fg'] = 'green'
        self.send_btn['state'] = 'normal'
        # Deshabilitar la posibilidad de iniciar otro servidor en esta instancia
        self.start_srv_btn['state'] = 'disabled'
        # iniciar hilo de recepción
        self.stop_event.clear()
        self.recv_thread = threading.Thread(target=self._bucle_recepcion, daemon=True)
        self.recv_thread.start()

    def _bucle_recepcion(self):
        usuario = self.name_entry.get()
        while not self.stop_event.is_set():
            try:
                data = self.gestor.recibir_bytes()
                if not data:
                    self.log(f'[{usuario}] Conexión cerrada por el otro extremo')
                    break
                mensaje = Mensaje.decodificar(data)
            except Exception as e:
                self.log(f'[{usuario}] Error al recibir/decodificar: {e}')
                continue

            tipo = mensaje.cabecera.tipo_operacion
            if tipo == Mensaje.TIPO_ENVIO:
                self.log(f"[{mensaje.cabecera.id_mensaje}] {mensaje.texto()}")
                # enviar ACK recibido
                ack = Mensaje("", id_protocolo=self.protocol_id, id_mensaje=mensaje.id_mensaje, tipo_operacion=Mensaje.TIPO_RECIBIDO)
                ack.payload = b''
                ack.cabecera.longitud_carga = 0
                ack.cabecera.crc32 = zlib.crc32(ack.payload) & 0xffffffff
                try:
                    self.gestor.enviar_bytes(ack.codificar())
                except Exception as e:
                    self.log(f'[{usuario}] Error enviando ACK: {e}')

                # simular lectura aleatoria
                threading.Timer(random.uniform(1, 5), self._simular_lectura, args=(mensaje.cabecera.id_mensaje,)).start()

            elif tipo == Mensaje.TIPO_RECIBIDO:
                self.log(f'[{usuario}] Confirmación: mensaje {mensaje.cabecera.id_mensaje} recibido')
            elif tipo == Mensaje.TIPO_LEIDO:
                self.log(f'[{usuario}] Confirmación: mensaje {mensaje.cabecera.id_mensaje} leído')

        # cierre
        self.stop()

    def _simular_lectura(self, id_mensaje):
        usuario = self.name_entry.get()

        if not self.gestor:
            return
        noti = Mensaje("", id_protocolo=self.protocol_id, id_mensaje=id_mensaje, tipo_operacion=Mensaje.TIPO_LEIDO)
        noti.payload = b''
        noti.cabecera.longitud_carga = 0
        noti.cabecera.crc32 = zlib.crc32(noti.payload) & 0xffffffff
        try:
            self.gestor.enviar_bytes(noti.codificar())
            self.log(f'[{usuario}] Mensaje {id_mensaje} marcado como leído (simulado)')
        except Exception as e:
            self.log(f'[{usuario}] Error enviando notificación LEIDO: {e}')

    def send_message(self):
        usuario = self.name_entry.get()

        texto = self.msg_entry.get()
        if not texto or not self.gestor:
            return
        msg = Mensaje(texto, id_protocolo=self.protocol_id)
        try:
            self.gestor.enviar_bytes(msg.codificar())
            self.log(f'[{usuario}] ({msg.id_mensaje}) {texto}')
        except Exception as e:
            self.log(f'[{usuario}] Error al enviar: {e}')
        finally:
            self.msg_entry.delete(0, 'end')

    def stop(self):
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
    root = tk.Tk()
    gui = ChatGUI(root)

    def on_close():
        gui.stop()
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', on_close)
    root.mainloop()


if __name__ == '__main__':
    main()
