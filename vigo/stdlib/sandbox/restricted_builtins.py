"""ViGo Sandbox - Restricted Builtins for safe code execution."""
import os


def build_restricted_globals(allowed_dirs=None, allowed_hosts=None, max_steps=None):
    """Build a restricted globals dict for code execution.
    
    Only safe builtins are included. open, __import__, exec, eval, input are
    replaced or disabled. File and network operations are intercepted.
    """
    if allowed_dirs is None:
        allowed_dirs = [os.getcwd()]
    if allowed_hosts is None:
        allowed_hosts = []
    
    safe_builtins = {
        "True": True, "False": False, "None": None,
        "int": int, "float": float, "str": str, "bool": bool,
        "list": list, "dict": dict, "set": set, "tuple": tuple,
        "bytes": bytes, "bytearray": bytearray,
        "print": print, "len": len, "range": range, "enumerate": enumerate,
        "zip": zip, "map": map, "filter": filter, "sorted": sorted,
        "reversed": reversed, "min": min, "max": max, "sum": sum,
        "abs": abs, "round": round, "pow": pow, "divmod": divmod,
        "ord": ord, "chr": chr, "hex": hex, "oct": oct, "bin": bin,
        "isinstance": isinstance, "issubclass": issubclass,
        "hasattr": hasattr, "getattr": getattr, "setattr": setattr,
        "type": type, "object": object, "super": super,
        "Exception": Exception, "ValueError": ValueError,
        "TypeError": TypeError, "KeyError": KeyError,
        "IndexError": IndexError, "StopIteration": StopIteration,
        "ZeroDivisionError": ZeroDivisionError,
        "complex": complex,
    }
    
    def restricted_open(file, mode='r', *args, **kwargs):
        real_path = os.path.realpath(file)
        allowed = any(real_path.startswith(os.path.realpath(d)) for d in allowed_dirs)
        if not allowed:
            raise PermissionError(f"Access denied: {file}")
        return open(file, mode, *args, **kwargs)
    
    safe_builtins["open"] = restricted_open
    
    if max_steps is not None and max_steps > 0:
        class StepLimitExceeded(Exception):
            pass
        
        step_counter = [0]
        
        def check_step():
            step_counter[0] += 1
            if step_counter[0] > max_steps:
                raise StepLimitExceeded(f"Step limit ({max_steps}) exceeded")
        
        safe_builtins["_check_step"] = check_step
        safe_builtins["StepLimitExceeded"] = StepLimitExceeded
    
    safe_builtins["__import__"] = lambda *a, **kw: (_ for _ in ()).throw(
        ImportError("__import__ is disabled in sandbox"))
    safe_builtins["exec"] = lambda *a, **kw: (_ for _ in ()).throw(
        RuntimeError("exec is disabled in sandbox"))
    safe_builtins["eval"] = lambda *a, **kw: (_ for _ in ()).throw(
        RuntimeError("eval is disabled in sandbox"))
    safe_builtins["input"] = lambda *a, **kw: (_ for _ in ()).throw(
        RuntimeError("input is disabled in sandbox"))
    safe_builtins["compile"] = lambda *a, **kw: (_ for _ in ()).throw(
        RuntimeError("compile is disabled in sandbox"))
    
    safe_builtins["_allowed_hosts"] = allowed_hosts
    
    import socket as _socket
    
    class RestrictedSocket(_socket.socket):
        def connect(self, address):
            host = address[0] if isinstance(address, tuple) else address
            if allowed_hosts and host not in allowed_hosts and '*' not in allowed_hosts:
                raise PermissionError(f"Network access denied: {host}")
            super().connect(address)
    
    safe_builtins["_SocketClass"] = RestrictedSocket
    
    safe_builtins["__builtins__"] = safe_builtins
    
    return safe_builtins