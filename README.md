# ChatBot (Proyecto de ejemplo - Sockets y PDU)

Proyecto pequeño de ejemplo que implementa un sistema de chat entre dos usuarios usando sockets TCP.
El proyecto serializa una PDU (cabecera + payload) para enviar mensajes con control de integridad (CRC32)
y notificaciones de estado (RECIBIDO/LEIDO).

## Contenido

- `cabecera.py`  — Clase `Cabecera` que define el header de la PDU y su serialización.
- `mensaje.py`   — Clase `Mensaje` que agrupa cabecera + payload; incluye codificar/decodificar y generación de IDs.
- `gestorSocket.py` — Abstracción sencilla sobre sockets TCP; puede actuar como servidor o cliente.
- `clienteChat.py`  — Clase `ClienteChat` que maneja envío/recepción y estados de mensajes (ENVIADO/RECIBIDO/LEIDO).
- `chat_gui.py`  — Interfaz gráfica (Tkinter) para conectar/iniciar servidor, enviar mensajes y ver estados.
- `estadoMensaje.py` — Enum con estados posibles de un mensaje.

## Requisitos

- Python 3.8 o superior (probado en CPython 3.x).
- No hay dependencias externas; utiliza módulos de la biblioteca estándar: `socket`, `struct`, `threading`, `zlib`, `tkinter`, `time`.

Nota: en macOS y algunas distribuciones Linux, `tkinter` puede requerir instalación separada (p. ej. `brew install python-tk` o paquete del sistema).

## Concepto rápido

1. Se empacan la cabecera (`Cabecera`) y la carga útil en bytes. La cabecera contiene versión, id de protocolo, tipo de operación, prioridad, marca de tiempo, id de mensaje, longitud y crc32.
2. `Mensaje.codificar()` concatena la cabecera serializada y el payload.
3. `GestorSocket` envía/recibe mensajes precedidos por un entero de 4 bytes con la longitud.
4. `chat_gui.py` ofrece una interfaz que puede iniciar un servidor local o conectar a otro nodo, enviar mensajes y recibir ACK/LEIDO.

## Uso (rápido)

1) Ejecutar la interfaz gráfica (ejemplo local con dos instancias):

```bash
# En una terminal (servidor):
python3 chat_gui.py

# En otra terminal (cliente) — o abre otra instancia GUI y conéctate al host y puerto adecuados:
python3 chat_gui.py
```

En la GUI puedes:
- Especificar un nombre, host (por defecto `127.0.0.1`) y puerto (por defecto `5000`).
- Pulsar `Iniciar Servidor` en una instancia para aceptar una conexión entrante.
- En la otra instancia, introducir el mismo puerto y host y pulsar `Conectar`.
- Escribir en el campo de texto y pulsar `Enviar` o Enter.

2) Uso por código (ejemplo mínimo):

```python
from gestorSocket import GestorSocket
from clienteChat import ClienteChat

# Ejemplo: conectar a un servidor existente
g = GestorSocket(nombre='cli')
g.conectar('127.0.0.1', 5000)
c = ClienteChat('cli', g)
c.iniciar_recepcion()
c.enviar_texto('Hola desde cliente programático')

# Recuerda llamar a c.detener() cuando termines.
```

## Notas y recomendaciones

- La implementación es didáctica: no gestiona múltiples clientes simultáneos (el servidor acepta una sola conexión con `listen(1)` y `accept()`).
- Para pruebas en la misma máquina, abre dos instancias de `chat_gui.py` o ejecuta la GUI y un cliente por separado.
- El protocolo usa CRC32 para comprobar integridad; si el `crc` no coincide, `Mensaje.decodificar()` lanza `ValueError`.
- Esta base se puede ampliar para: manejo de múltiples clientes, reconexión, persistencia de mensajes o cifrado de payload.

## Estructura del proyecto

```
ChatBot/
  cabecera.py
  mensaje.py
  gestorSocket.py
  clienteChat.py
  chat_gui.py
  estadoMensaje.py
```

## Autor / Licencia

Proyecto educativo. Puedes adaptar y usar el código en prácticas y trabajos sin restricciones particulares.

