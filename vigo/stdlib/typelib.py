"""ViGo Type Checking Library"""
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


class TypeChecker:
    def __init__(self):
        self.checks_enabled = True

    def enable(self, enabled=True):
        self.checks_enabled = enabled
        return True

    def check(self, value, expected_type):
        if not self.checks_enabled:
            return value

        type_map = {
            "number": (int, float),
            "int": int,
            "float": float,
            "string": str,
            "bool": bool,
            "list": list,
            "dict": dict,
            "set": set,
            "null": type(None),
            "function": "function",
        }

        expected = type_map.get(expected_type)
        if expected is None:
            raise ViGoError(f"Unknown type: {expected_type}")

        if expected == "function":
            if not callable(value) and not hasattr(value, '__call__') and not hasattr(value, 'func'):
                raise ViGoError(f"Type error: expected function, got {type(value).__name__}")
            return value

        if not isinstance(value, expected):
            raise ViGoError(f"Type error: expected {expected_type}, got {type(value).__name__}")
        return value

    def is_type(self, value, type_name):
        type_map = {"number": (int, float), "int": int, "float": float, "string": str,
                     "bool": bool, "list": list, "dict": dict, "set": set, "null": type(None)}
        expected = type_map.get(type_name)
        if expected is None: return False
        return isinstance(value, expected)

    def type_of(self, value):
        if value is None: return "null"
        if isinstance(value, bool): return "bool"
        if isinstance(value, int): return "int"
        if isinstance(value, float): return "float"
        if isinstance(value, str): return "string"
        if isinstance(value, list): return "list"
        if isinstance(value, dict): return "dict"
        if isinstance(value, set): return "set"
        return "unknown"


_tc = TypeChecker()


def register(env):
    env.define('type_check', BuiltinFunction(
        lambda v, t: _tc.check(v, t), 'type_check'))
    env.define('type_is', BuiltinFunction(
        lambda v, t: _tc.is_type(v, t), 'type_is'))
    env.define('type_of', BuiltinFunction(
        lambda v: _tc.type_of(v), 'type_of'))
    env.define('type_enable', BuiltinFunction(
        lambda e=True: _tc.enable(e) and True, 'type_enable'))