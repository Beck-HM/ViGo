import math
import random as rnd
from ..runtime.objects import BuiltinFunction


def register(env):
    env.define('sqrt',    BuiltinFunction(lambda x: math.sqrt(x), 'sqrt'))
    env.define('abs',     BuiltinFunction(lambda x: abs(x), 'abs'))
    env.define('min',     BuiltinFunction(lambda *a: min(a), 'min'))
    env.define('max',     BuiltinFunction(lambda *a: max(a), 'max'))
    env.define('floor',   BuiltinFunction(lambda x: math.floor(x), 'floor'))
    env.define('ceil',    BuiltinFunction(lambda x: math.ceil(x), 'ceil'))
    env.define('round',   BuiltinFunction(lambda x, d=0: round(x, d), 'round'))
    env.define('pow',     BuiltinFunction(lambda x, y: x ** y, 'pow'))
    env.define('random',  BuiltinFunction(lambda a=None, b=None:
                 rnd.random() if a is None else
                 rnd.randint(0, int(a)) if b is None else
                 rnd.randint(int(a), int(b)), 'random'))
    # TrigFunction
    env.define('sin',     BuiltinFunction(lambda x: math.sin(x), 'sin'))
    env.define('cos',     BuiltinFunction(lambda x: math.cos(x), 'cos'))
    env.define('tan',     BuiltinFunction(lambda x: math.tan(x), 'tan'))
    # Logarithm
    env.define('log',     BuiltinFunction(lambda x, base=math.e: math.log(x, base), 'log'))
    env.define('log10',   BuiltinFunction(lambda x: math.log10(x), 'log10'))
    # Angle conversion
    env.define('degrees', BuiltinFunction(lambda r: math.degrees(r), 'degrees'))
    env.define('radians', BuiltinFunction(lambda d: math.radians(d), 'radians'))
    # Random extensions
    env.define('random_choice',  BuiltinFunction(lambda arr: rnd.choice(arr) if arr else None, 'random_choice'))
    env.define('random_shuffle', BuiltinFunction(lambda arr: rnd.shuffle(arr) or arr if arr else [], 'random_shuffle'))
    env.define('random_float',   BuiltinFunction(lambda a=0.0, b=1.0: rnd.uniform(a, b), 'random_float'))
    # Math constants
    env.define('PI',   math.pi)
    env.define('E',    math.e)
    env.define('TAU',  math.tau)
    # Clamp and lerp
    env.define('clamp', BuiltinFunction(lambda x, lo, hi: max(lo, min(hi, x)), 'clamp'))
    env.define('lerp',  BuiltinFunction(lambda a, b, t: a + (b - a) * max(0.0, min(1.0, t)), 'lerp'))