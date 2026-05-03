from ..stdlib import register_all
from .objects import BuiltinFunction


def register(env):
    env.define('sorted', BuiltinFunction(lambda arr: sorted(arr) if arr else [], 'sorted'))
    register_all(env)