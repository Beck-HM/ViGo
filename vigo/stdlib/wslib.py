"""ViGo WebSocket Library"""
import json
import threading
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


class WebSocketServer:
    def __init__(self):
        self.host = "localhost"
        self.port = 8765
        self._running = False
        self._thread = None
        self._clients = []
        self._on_message = None
        self._on_connect = None
        self._on_disconnect = None

    def configure(self, host="localhost", port=8765):
        self.host = host
        self.port = int(port)
        return True

    def on_message(self, callback):
        self._on_message = callback
        return True

    def on_connect(self, callback):
        self._on_connect = callback
        return True

    def on_disconnect(self, callback):
        self._on_disconnect = callback
        return True

    def start(self):
        if self._running:
            return "Already running."

        import asyncio

        async def handler(websocket):
            if self._on_connect and hasattr(self._on_connect, 'func'):
                self._on_connect.func()
            try:
                async for message in websocket:
                    if self._on_message and hasattr(self._on_message, 'func'):
                        self._on_message.func(message)
                    await websocket.send(f"Echo: {message}")
            except:
                pass
            finally:
                if self._on_disconnect and hasattr(self._on_disconnect, 'func'):
                    self._on_disconnect.func()

        async def main_async():
            import websockets
            async with websockets.serve(handler, self.host, self.port):
                await asyncio.Future()

        def run_server():
            asyncio.run(main_async())

        self._running = True
        self._thread = threading.Thread(target=run_server, daemon=True)
        self._thread.start()
        return f"WebSocket server started on ws://{self.host}:{self.port}"

    def stop(self):
        self._running = False
        return "WebSocket server stopped."

    def broadcast(self, message):
        return f"Broadcast: {message} (simulated)"


_ws = WebSocketServer()


def register(env):
    env.define('ws_configure', BuiltinFunction(
        lambda h="localhost", p=8765: _ws.configure(h, p),
        'ws_configure'))
    env.define('ws_on_message', BuiltinFunction(
        lambda cb: _ws.on_message(cb),
        'ws_on_message'))
    env.define('ws_on_connect', BuiltinFunction(
        lambda cb: _ws.on_connect(cb),
        'ws_on_connect'))
    env.define('ws_start', BuiltinFunction(
        lambda: _ws.start(),
        'ws_start'))
    env.define('ws_stop', BuiltinFunction(
        lambda: _ws.stop(),
        'ws_stop'))
    env.define('ws_broadcast', BuiltinFunction(
        lambda msg: _ws.broadcast(msg),
        'ws_broadcast'))