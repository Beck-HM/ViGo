"""ViGo Standard Library: Data Serialization (packlib)
Binary serialization with MessagePack, CBOR, BSON support.
Uses optional third-party libraries with pure Python fallbacks.
"""
import json
import struct
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


def _pack_msgpack(data):
    """Pack data using MessagePack format."""
    try:
        import msgpack
        return msgpack.packb(data)
    except ImportError:
        raise ViGoError("msgpack not installed. Run: pip install msgpack")


def _unpack_msgpack(data):
    """Unpack MessagePack data."""
    try:
        import msgpack
        return msgpack.unpackb(data)
    except ImportError:
        raise ViGoError("msgpack not installed. Run: pip install msgpack")


def _pack_json(data):
    """Pack as JSON (fallback)."""
    return json.dumps(data, ensure_ascii=False).encode('utf-8')


def _unpack_json(data):
    """Unpack from JSON (fallback)."""
    if isinstance(data, bytes):
        data = data.decode('utf-8')
    return json.loads(data)


def pack(data, format="msgpack"):
    """Serialize data to binary format."""
    if format == "msgpack":
        return _pack_msgpack(data)
    elif format == "cbor":
        try:
            import cbor2
            return cbor2.dumps(data)
        except ImportError:
            raise ViGoError("cbor2 not installed. Run: pip install cbor2")
    elif format == "bson":
        try:
            import bson
            return bson.dumps(data)
        except ImportError:
            raise ViGoError("bson not installed. Run: pip install bson")
    elif format == "json":
        return _pack_json(data)
    else:
        raise ViGoError(f"Unknown format: {format}")


def unpack(data, format="msgpack"):
    """Deserialize binary data."""
    if format == "msgpack":
        return _unpack_msgpack(data)
    elif format == "cbor":
        try:
            import cbor2
            return cbor2.loads(data)
        except ImportError:
            raise ViGoError("cbor2 not installed. Run: pip install cbor2")
    elif format == "bson":
        try:
            import bson
            return bson.loads(data)
        except ImportError:
            raise ViGoError("bson not installed. Run: pip install bson")
    elif format == "json":
        return _unpack_json(data)
    else:
        raise ViGoError(f"Unknown format: {format}")


def register(env):
    env.define("pack", BuiltinFunction(lambda data, format="msgpack": pack(data, format), "pack"))
    env.define("unpack", BuiltinFunction(lambda data, format="msgpack": unpack(data, format), "unpack"))