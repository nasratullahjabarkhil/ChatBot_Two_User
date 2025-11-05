# ChatBot_Two_User

Proyecto educativo de chat entre dos usuarios usando sockets TCP (cliente a cliente) con protocolo propio
basado en PDU (cabecera + payload), verificación de integridad con CRC32 y notificaciones de estado
(RECIBIDO/LEÍDO). El código principal está en la carpeta `ChatBot/`.

## Contenido (carpeta `ChatBot/`)

- `cabecera.py`          — Clase `Cabecera` que define el header de la PDU y su serialización (struct pack/unpack).
- `mensaje.py`           — Clase `Mensaje` (cabecera + payload); incluye codificar/decodificar y generación de IDs.
- `gestorSocket.py`      — Envoltura de sockets TCP; actúa como servidor o cliente. Mensajes con prefijo de longitud (4 bytes).
- `clienteChat.py`       — Clase `ClienteChat` que maneja envío/recepción y estados (ENVIADO/RECIBIDO/LEÍDO).
- `chat_gui.py`          — Interfaz gráfica (Tkinter) para iniciar servidor, conectar, enviar mensajes y ver confirmaciones.
- `estadoMensaje.py`     — Enum con los estados posibles de un mensaje.

## Requisitos

- Python 3.8 o superior (probado en CPython 3.x).
- Sin dependencias externas; usa biblioteca estándar: `socket`, `struct`, `threading`, `zlib`, `tkinter`, `time`.

Nota: en macOS y algunas distribuciones Linux, `tkinter` puede requerir instalación adicional (p. ej. `brew install python-tk` o paquete del sistema).

## Concepto rápido

1. Se empacan la cabecera (`Cabecera`) y la carga útil en bytes. La cabecera contiene versión, id de protocolo, tipo de operación, prioridad, marca de tiempo, id de mensaje, longitud y CRC32.
2. `Mensaje.codificar()` concatena la cabecera serializada y el payload.
3. `GestorSocket` envía/recibe mensajes con prefijo de longitud (entero de 4 bytes, big-endian).
4. `chat_gui.py` ofrece una interfaz que puede iniciar un servidor local o conectar a otro nodo, enviar mensajes y recibir confirmaciones (RECIBIDO/LEÍDO).

## Cómo ejecutar

Recomendado ejecutar desde la carpeta `ChatBot/`.

```bash
cd ChatBot

# En una terminal (servidor):
python3 chat_gui.py

# En otra terminal (cliente) — abre otra instancia GUI y conéctate al host y puerto del servidor:
cd ChatBot
python3 chat_gui.py
```

En la GUI puedes:
- Especificar un nombre, host (por defecto `127.0.0.1`) y puerto (por defecto `5000`).
- Pulsar `Iniciar Servidor` en una instancia para aceptar una conexión entrante.
- En la otra instancia, introducir el mismo puerto y host y pulsar `Conectar`.
- Escribir en el campo de texto y pulsar `Enviar` o Enter.

Consejos:
- Solo una instancia debe iniciar el servidor; la otra se conecta como cliente.
- El botón de iniciar servidor se deshabilita al estar conectados para evitar conflictos.

### Uso por código

```python
from gestorSocket import GestorSocket
from clienteChat import ClienteChat

# Ejecuta este código desde la carpeta ChatBot/ (donde están los módulos)
g = GestorSocket(nombre='cli')
g.conectar('127.0.0.1', 5000)
c = ClienteChat('cli', g)
c.iniciar_recepcion()
c.enviar_texto('Hola desde cliente programático')

# Recuerda llamar a c.detener() cuando termines.
```

## Notas y recomendaciones

- Implementación didáctica: no gestiona múltiples clientes simultáneos (el servidor acepta una sola conexión con `listen(1)`).
- Para pruebas en la misma máquina, abre dos instancias de `chat_gui.py` o ejecuta la GUI y un cliente por separado.
- El protocolo usa CRC32 para comprobar integridad; si el CRC no coincide, `Mensaje.decodificar()` lanza `ValueError`.
- Ampliaciones posibles: soporte multi-cliente, reconexión, persistencia de mensajes, cifrado del payload.

## Estructura del repositorio

```
PEC2/
  README.md               # Este archivo
  ChatBot/
    cabecera.py
    mensaje.py
    gestorSocket.py
    clienteChat.py
    chat_gui.py
    estadoMensaje.py
```



