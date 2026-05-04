from vigo.stdlib.ailib import _ai, register
from vigo.runtime.environment import Environment

# Simulate ViGo env
env = Environment()
register(env)

# Setup callback
received = []
def collect(chunk):
    received.append(chunk)
    print(f"CHUNK: {chunk}", end="")

_ai.set_stream_callback(collect)
result = _ai.ask("Count from 1 to 3.", "gemma-4b", 0.7, 200, "ollama", True)
print(f"\nFull: {result}")
print(f"Chunks: {len(received)}")