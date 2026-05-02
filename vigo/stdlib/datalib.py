import json, re, time, datetime, csv, io
from ..runtime.objects import BuiltinFunction, ViGoEnum, ViGoInstance, ViGoClass, LambdaFunction, ViGoFunction
from ..runtime.errors import ViGoError
from ..runtime.environment import Environment
from ..runtime.errors import ReturnException


def _type(v):
    if v is None: return "null"
    if isinstance(v, bool): return "bool"
    if isinstance(v, (int, float)): return "number"
    if isinstance(v, str): return "string"
    if isinstance(v, list): return "list"
    if isinstance(v, dict): return "dict"
    if isinstance(v, set): return "set"
    if isinstance(v, ViGoEnum): return "enum"
    if isinstance(v, ViGoInstance): return v.cls.name
    if isinstance(v, ViGoClass): return "class"
    if isinstance(v, (ViGoFunction, LambdaFunction, BuiltinFunction)): return "function"
    return "unknown"


def register(env):
    env.define('len',     BuiltinFunction(lambda x: len(x) if hasattr(x, '__len__') else 0, 'len'))
    env.define('str',     BuiltinFunction(lambda x: str(x), 'str'))
    env.define('int',     BuiltinFunction(lambda x: int(x) if x is not None else 0, 'int'))
    env.define('float',   BuiltinFunction(lambda x: float(x) if x is not None else 0.0, 'float'))
    env.define('bool',    BuiltinFunction(lambda x: bool(x), 'bool'))
    env.define('type',    BuiltinFunction(_type, 'type'))
    env.define('push',    BuiltinFunction(lambda l, i: l.append(i) or l, 'push'))
    env.define('pop',     BuiltinFunction(lambda l: l.pop() if l else None, 'pop'))
    env.define('insert',  BuiltinFunction(lambda l, p, i: l.insert(p, i) or l, 'insert'))
    env.define('remove',  BuiltinFunction(lambda l, i: (l.remove(i) if i in l else None) or l, 'remove'))
    env.define('sort',    BuiltinFunction(lambda l, key=None: l.sort(key=key) or l, 'sort'))
    env.define('find_idx',BuiltinFunction(lambda l, i: l.index(i) if i in l else -1, 'find_idx'))
    env.define('reverse', BuiltinFunction(lambda l: l.reverse() or l, 'reverse'))
    env.define('copy',    BuiltinFunction(lambda x: x.copy() if hasattr(x, 'copy') else x, 'copy'))
    env.define('clear',   BuiltinFunction(lambda x: x.clear() or x if hasattr(x, 'clear') else x, 'clear'))
    env.define('slice',   BuiltinFunction(lambda lst, s, e: lst[s:e], 'slice'))
    env.define('map',     BuiltinFunction(_map, 'map'))
    env.define('filter',  BuiltinFunction(_filter, 'filter'))
    env.define('reduce',  BuiltinFunction(_reduce, 'reduce'))
    env.define('sum',     BuiltinFunction(lambda lst: sum(lst) if isinstance(lst, list) else 0, 'sum'))
    env.define('unique',  BuiltinFunction(lambda lst: list(dict.fromkeys(lst)) if isinstance(lst, list) else lst, 'unique'))
    env.define('flatten', BuiltinFunction(_flatten, 'flatten'))
    env.define('group_by',BuiltinFunction(_group_by, 'group_by'))
    env.define('chunk',   BuiltinFunction(_chunk, 'chunk'))
    env.define('keys',    BuiltinFunction(lambda d: list(d.keys()) if isinstance(d, dict) else [], 'keys'))
    env.define('values',  BuiltinFunction(lambda d: list(d.values()) if isinstance(d, dict) else [], 'values'))
    env.define('get',     BuiltinFunction(lambda d, k, default=None: d.get(k, default) if isinstance(d, dict) else default, 'get'))
    env.define('set',     BuiltinFunction(lambda d, k, v: d.__setitem__(k, v) or d if isinstance(d, dict) else None, 'set'))
    env.define('delete',  BuiltinFunction(lambda d, k: (d.pop(k, None), d)[1] if isinstance(d, dict) else None, 'delete'))
    env.define('merge',   BuiltinFunction(_merge, 'merge'))
    env.define('has',     BuiltinFunction(lambda d, k: k in d if isinstance(d, (dict, list, str, set)) else False, 'has'))
    env.define('parse_json', BuiltinFunction(lambda s: json.loads(s) if isinstance(s, str) else None, 'parse_json'))
    env.define('to_json', BuiltinFunction(lambda o: json.dumps(o, ensure_ascii=False, default=str), 'to_json'))
    env.define('split',   BuiltinFunction(lambda s, sep=' ': s.split(sep) if isinstance(s, str) else [], 'split'))
    env.define('join',    BuiltinFunction(lambda l, sep='': sep.join(str(x) for x in l) if isinstance(l, list) else '', 'join'))
    env.define('replace', BuiltinFunction(lambda s, o, n: s.replace(o, n) if isinstance(s, str) else s, 'replace'))
    env.define('upper',   BuiltinFunction(lambda s: s.upper() if isinstance(s, str) else s, 'upper'))
    env.define('lower',   BuiltinFunction(lambda s: s.lower() if isinstance(s, str) else s, 'lower'))
    env.define('trim',    BuiltinFunction(lambda s: s.strip() if isinstance(s, str) else s, 'trim'))
    env.define('format_num', BuiltinFunction(lambda v, f='': f"{v:{f}}" if f else str(v), 'format_num'))
    env.define('contains',  BuiltinFunction(lambda s, sub: sub in s if isinstance(s, str) else False, 'contains'))
    env.define('count_str', BuiltinFunction(lambda s, sub: s.count(sub) if isinstance(s, str) else 0, 'count_str'))
    env.define('index_of',  BuiltinFunction(lambda s, sub: s.find(sub) if isinstance(s, str) else -1, 'index_of'))
    env.define('starts',    BuiltinFunction(lambda s, p: s.startswith(p) if isinstance(s, str) else False, 'starts'))
    env.define('ends',      BuiltinFunction(lambda s, p: s.endswith(p) if isinstance(s, str) else False, 'ends'))
    env.define('pad_left',  BuiltinFunction(lambda s, width, ch=' ': s.rjust(width, ch) if isinstance(s, str) else s, 'pad_left'))
    env.define('pad_right', BuiltinFunction(lambda s, width, ch=' ': s.ljust(width, ch) if isinstance(s, str) else s, 'pad_right'))
    env.define('regex_match', BuiltinFunction(_regex_match, 'regex_match'))
    env.define('regex_replace', BuiltinFunction(lambda p, r, t: re.sub(p, r, t), 'regex_replace'))
    env.define('time',    BuiltinFunction(lambda: time.time(), 'time'))
    env.define('now',     BuiltinFunction(lambda: datetime.datetime.now().isoformat(), 'now'))
    env.define('date',    BuiltinFunction(lambda f='%Y-%m-%d': datetime.datetime.now().strftime(f), 'date'))
    env.define('sleep',   BuiltinFunction(lambda s: time.sleep(float(s)), 'sleep'))

    def _parse_csv(text, delimiter=','):
        try:
            reader = csv.reader(io.StringIO(text), delimiter=delimiter)
            return [row for row in reader]
        except Exception as e:
            raise ViGoError(f"CSV parse failed: {e}")

    def _to_csv(data, delimiter=','):
        try:
            output = io.StringIO()
            writer = csv.writer(output, delimiter=delimiter)
            for row in data:
                writer.writerow(row)
            return output.getvalue()
        except Exception as e:
            raise ViGoError(f"CSV generate failed: {e}")

    env.define('parse_csv', BuiltinFunction(_parse_csv, 'parse_csv'))
    env.define('to_csv',    BuiltinFunction(_to_csv, 'to_csv'))

    env.define('null', None); env.define('true', True); env.define('false', False)
    env.define('ok', True); env.define('no', False)


# ── InternalFunction ──

def _reduce(lst, fn, initial=None):
    it = iter(lst)
    result = initial if initial is not None else next(it)
    for item in it:
        if isinstance(fn, BuiltinFunction):
            result = fn.func(result, item)
        elif isinstance(fn, (ViGoFunction, LambdaFunction)):
            call_env = Environment(fn.closure)
            call_env.define(fn.params[0], result)
            call_env.define(fn.params[1], item) if len(fn.params) > 1 else None
            interpreter = None
            from ..runtime.interpreter import Interpreter
            interpreter = Interpreter()
            try:
                for s in fn.body:
                    result = interpreter.eval(s, call_env)
            except ReturnException as r:
                result = r.value
    return result


def _map(lst, fn):
    if not isinstance(lst, list): raise ViGoError("map requires a list")
    result = []
    for item in lst:
        if isinstance(fn, BuiltinFunction):
            result.append(fn.func(item))
        elif isinstance(fn, (ViGoFunction, LambdaFunction)):
            call_env = Environment(fn.closure)
            call_env.define(fn.params[0], item)
            from ..runtime.interpreter import Interpreter
            interpreter = Interpreter()
            try:
                for s in fn.body:
                    res = interpreter.eval(s, call_env)
            except ReturnException as r:
                res = r.value
            result.append(res)
    return result


def _filter(lst, fn):
    if not isinstance(lst, list): raise ViGoError("filter requires a list")
    result = []
    for item in lst:
        if isinstance(fn, BuiltinFunction):
            if fn.func(item):
                result.append(item)
        elif isinstance(fn, (ViGoFunction, LambdaFunction)):
            call_env = Environment(fn.closure)
            call_env.define(fn.params[0], item)
            from ..runtime.interpreter import Interpreter
            interpreter = Interpreter()
            try:
                for s in fn.body:
                    res = interpreter.eval(s, call_env)
            except ReturnException as r:
                res = r.value
            if interpreter.is_truthy(res):
                result.append(item)
    return result


def _merge(d1, d2):
    return {**(d1 if isinstance(d1, dict) else {}), **(d2 if isinstance(d2, dict) else {})}


def _regex_match(pattern, text):
    m = re.search(pattern, text)
    return [m.group(0)] + list(m.groups()) if m else None


def _flatten(lst):
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(_flatten(item))
        else:
            result.append(item)
    return result


def _group_by(lst, size):
    if not isinstance(lst, list) or size <= 0: return []
    return [lst[i:i + size] for i in range(0, len(lst), size)]


def _chunk(lst, size):
    return _group_by(lst, size)