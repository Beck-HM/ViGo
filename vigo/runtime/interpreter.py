import os, time
from ..lexer.lexer import Lexer
from ..parser.parser import Parser
from ..parser.ast_nodes import *
from .environment import Environment
from .objects import (BuiltinFunction, ViGoFunction, LambdaFunction, ViGoClass, ViGoInstance, ViGoEnum)
from .errors import (ViGoError, ReturnException, BreakException, ContinueException, AwaitException)
from .builtins import register as register_builtins


class Interpreter:
    MAX_CALL_DEPTH = 500

    def __init__(self, source_file='<script>'):
        self.global_env = Environment()
        register_builtins(self.global_env)
        self.call_depth = 0; self.source_file = source_file
        self.call_trace = []; self.timeout = None; self.start_time = None
        self.constants = set()

    def register(self, name, func): self.global_env.define(name, BuiltinFunction(func, name))
    def register_object(self, name, obj): self.global_env.define(name, obj)

    def reset(self):
        self.global_env = Environment(); register_builtins(self.global_env)
        self.call_depth = 0; self.call_trace = []; self.constants = set()

    def set_timeout(self, sec): self.timeout = sec

    def _check_timeout(self):
        if self.timeout and self.start_time and time.time() - self.start_time > self.timeout:
            raise ViGoError("Script execution timeout")

    def interpret(self, program):
        self.start_time = time.time(); result = None
        for stmt in program.statements: result = self.eval(stmt)
        return result

    def eval(self, node, env=None):
        self._check_timeout()
        if env is None: env = self.global_env
        try:
            if isinstance(node, Program): return self.eval_block(node.statements, env)
            elif isinstance(node, VarDecl):
                if node.name in self.constants:
                    raise ViGoError(f"Cannot modify constant '{node.name}'")
                val = self.eval(node.value, env)
                if node.is_const: self.constants.add(node.name)
                if env.has(node.name) and not node.is_const:
                    env.assign(node.name, val)
                else:
                    env.define(node.name, val)
                return val
            elif isinstance(node, DestructureDecl): return self._destructure(node, env)
            elif isinstance(node, AssignStmt):
                if isinstance(node.target, Variable) and node.target.name in self.constants:
                    raise ViGoError(f"Cannot modify constant '{node.target.name}'")
                return self._assign(node, env)
            elif isinstance(node, IfStmt): return self._if(node, env)
            elif isinstance(node, SkipStmt):
                if not self.is_truthy(self.eval(node.condition, env)):
                    return self.eval_block(node.body, Environment(env))
                return None
            elif isinstance(node, TernaryExpr):
                return self.eval(node.then_expr, env) if self.is_truthy(self.eval(node.condition, env)) else self.eval(node.else_expr, env)
            elif isinstance(node, SwitchStmt): return self._switch(node, env)
            elif isinstance(node, ForInStmt): return self._for_in(node, env)
            elif isinstance(node, LoopStmt): return self._loop(node, env)
            elif isinstance(node, DoWhileStmt): return self._do_while(node, env)
            elif isinstance(node, BreakStmt): raise BreakException()
            elif isinstance(node, ContinueStmt): raise ContinueException()
            elif isinstance(node, SureStmt):
                if not self.is_truthy(self.eval(node.condition, env)):
                    raise ViGoError(f"Assertion failed: {node.message or 'Condition not satisfied'}")
                return True
            elif isinstance(node, StaticMethodDef):
                func = ViGoFunction(node.func_def.name, node.func_def.params,
                                    node.func_def.defaults, node.func_def.rest_param,
                                    node.func_def.body, env, self.source_file)
                func.is_static = True; env.define(node.func_def.name, func); return func
            elif isinstance(node, AbstractMethodDef): return node
            elif isinstance(node, InterfaceDef):
                env.define(node.name, {'__vigo_interface__': True, 'name': node.name, 'methods': node.methods}); return node
            elif isinstance(node, FuncDef):
                func = ViGoFunction(node.name, node.params, node.defaults, node.rest_param, node.body, env, self.source_file)
                env.define(node.name, func); return func
            elif isinstance(node, LambdaExpr): return LambdaFunction(node.params, node.body, env)
            elif isinstance(node, ReturnStmt): raise ReturnException(self.eval(node.value, env))
            elif isinstance(node, FuncCall): return self._func_call(node, env)
            elif isinstance(node, PipeExpr): return self._pipe(node, env)
            elif isinstance(node, RangeExpr):
                return list(range(int(self.eval(node.start, env)), int(self.eval(node.end, env)) + 1))
            elif isinstance(node, ExpandExpr): return self.eval(node.expr, env)
            elif isinstance(node, OptionalChain):
                try:
                    obj = self.eval(node.object, env)
                    return None if obj is None else self.eval(node.chain, Environment(env))
                except ViGoError: return None
            elif isinstance(node, NullCoalesce):
                left = self.eval(node.left, env); return left if left is not None else self.eval(node.right, env)
            elif isinstance(node, ListCompExpr): return self._listcomp(node, env)
            elif isinstance(node, ChainedCompare): return self._chained_compare(node, env)
            elif isinstance(node, InExpr): return self._in_expr(node, env)
            elif isinstance(node, BinaryOp): return self._binary_op(node, env)
            elif isinstance(node, LogicalOp): return self._logical_op(node, env)
            elif isinstance(node, UnaryOp): return self._unary_op(node, env)
            elif isinstance(node, Literal): return node.value
            elif isinstance(node, Variable): return env.lookup(node.name)
            elif isinstance(node, ListLiteral): return [self.eval(el, env) for el in node.elements]
            elif isinstance(node, DictLiteral): return {k: self.eval(v, env) for k, v in node.pairs.items()}
            elif isinstance(node, SetLiteral): return {self.eval(el, env) for el in node.elements}
            elif isinstance(node, IndexAccess): return self._index(node, env)
            elif isinstance(node, SliceAccess): return self._slice(node, env)
            elif isinstance(node, DotAccess): return self._dot(node, env)
            elif isinstance(node, InterpolatedString): return self._interp_str(node, env)
            elif isinstance(node, LoadStmt): return self._load(node, env)
            elif isinstance(node, ClassDef): return self._class_def(node, env)
            elif isinstance(node, EnumDef): return self._enum_def(node, env)
            elif isinstance(node, NewExpr): return self._new(node, env)
            elif isinstance(node, ThisExpr): return env.lookup('this')
            elif isinstance(node, TryStmt): return self._try(node, env)
            elif isinstance(node, ThrowStmt): raise ViGoError(str(self.eval(node.value, env)))
            elif isinstance(node, AwaitExpr): raise AwaitException(float(self.eval(node.value, env)))
            else: raise ViGoError(f"Unknown AST node: {type(node).__name__}")
        except (ReturnException, BreakException, ContinueException, AwaitException): raise
        except ViGoError: raise
        except Exception as e: raise ViGoError(str(e), self.call_trace.copy())

    def _switch(self, node, env):
        val = self.eval(node.expr, env)
        for cv, cb in node.cases:
            if isinstance(cv, tuple) and len(cv) == 3 and cv[0] == 'range':
                if cv[1] <= val <= cv[2]:
                    return self.eval_block(cb, env)
            elif val == cv:
                return self.eval_block(cb, env)
        if node.default_body:
            return self.eval_block(node.default_body, env)
        return None

    def _class_def(self, node, env):
        parent = env.lookup(node.parent) if node.parent else None
        cls_env = Environment(parent.closure if isinstance(parent, ViGoClass) else env)
        body = (parent.body + node.body) if isinstance(parent, ViGoClass) else node.body
        for stmt in body:
            if isinstance(stmt, FuncDef):
                cls_env.define(stmt.name, ViGoFunction(stmt.name, stmt.params, stmt.defaults, stmt.rest_param, stmt.body, cls_env, self.source_file))
            elif isinstance(stmt, StaticMethodDef):
                func = ViGoFunction(stmt.func_def.name, stmt.func_def.params, stmt.func_def.defaults, stmt.func_def.rest_param, stmt.func_def.body, cls_env, self.source_file)
                func.is_static = True; cls_env.define(stmt.func_def.name, func)
            elif isinstance(stmt, AbstractMethodDef): cls_env.define(stmt.name, stmt)
            elif isinstance(stmt, InterfaceDef): cls_env.define(stmt.name, stmt)
            elif isinstance(stmt, VarDecl): cls_env.define(stmt.name, self.eval(stmt.value, cls_env))
        cls = ViGoClass(node.name, parent, body, cls_env, self.source_file)
        env.define(node.name, cls); return cls

    def _func_call(self, node, env):
        args = [self.eval(a, env) for a in node.args]
        func = None; func_name = '<unknown>'; this_obj = None
        if isinstance(node.name, DotAccess):
            obj = self.eval(node.name.object, env); mn = node.name.attr; func_name = f".{mn}"
            if isinstance(obj, ViGoInstance):
                func = obj.env.lookup(mn) if mn in obj.env.variables else obj.cls.closure.lookup(mn)
                this_obj = obj
            elif isinstance(obj, ViGoClass):
                func = obj.closure.lookup(mn)
            elif isinstance(obj, dict):
                if mn in obj:
                    func = obj[mn]
                else:
                    func = self._dot(DotAccess(Literal(obj), mn), env)
            else:
                func = self._dot(DotAccess(Literal(obj), mn), env)
        elif isinstance(node.name, Variable):
            func = env.lookup(node.name.name); func_name = node.name.name
        else:
            func = self.eval(node.name, env)
        return self._call(func, args, env, func_name, this_obj)

    def _call(self, func, args, env, func_name, this_obj=None):
        if self.call_depth > self.MAX_CALL_DEPTH: raise ViGoError("Maximum call depth exceeded")
        if isinstance(func, BuiltinFunction):
            return func.func(*args)
        elif isinstance(func, (ViGoFunction, LambdaFunction)):
            final_args = list(args); expected = len(func.params)
            while len(final_args) < expected:
                pn = func.params[len(final_args)]
                if pn in func.defaults: final_args.append(self.eval(func.defaults[pn], env))
                else: raise ViGoError(f"Function '{func_name}' Missing parameter '{pn}'")
            if func.rest_param and len(final_args) > expected:
                final_args = final_args[:expected] + [final_args[expected:]]
            call_env = Environment(func.closure)
            if this_obj is not None:
                call_env.define('this', this_obj)
            for p, a in zip(func.params, final_args[:expected]): call_env.define(p, a)
            if func.rest_param: call_env.define(func.rest_param, final_args[expected] if len(final_args) > expected else [])
            self.call_depth += 1; self.call_trace.append(f"{func_name}()")
            try: return self.eval_block(func.body, call_env)
            except ReturnException as r: return r.value
            finally:
                self.call_depth -= 1
                if self.call_trace: self.call_trace.pop()
        elif isinstance(func, ViGoClass):
            inst = ViGoInstance(func, Environment(func.closure))
            if 'init' in func.closure.variables:
                init_f = func.closure.lookup('init')
                if isinstance(init_f, ViGoFunction):
                    ce = Environment(inst.env); ce.define('this', inst)
                    fa = list(args); exp = len(init_f.params)
                    while len(fa) < exp:
                        pn = init_f.params[len(fa)]
                        if pn in init_f.defaults: fa.append(self.eval(init_f.defaults[pn], env))
                        else: break
                    for p, a in zip(init_f.params, fa[:exp]): ce.define(p, a)
                    self.call_depth += 1; self.call_trace.append(f"{func.name}.init()")
                    try:
                        self.eval_block(init_f.body, ce)
                    except ReturnException:
                        pass
                    finally:
                        for k, v in ce.variables.items():
                            if k not in inst.env.variables and k != 'this':
                                inst.env.define(k, v)
                        self.call_depth -= 1
                        if self.call_trace: self.call_trace.pop()
            return inst
        raise ViGoError(f"'{func_name}' is not callable")

    def _pipe(self, node, env):
        left = self.eval(node.left, env)
        right = node.right
        if isinstance(right, FuncCall):
            func = self.eval(right.name, env)
            args = [left] + [self.eval(a, env) for a in right.args]
            return self._call(func, args, env, str(right.name))
        elif isinstance(right, Variable):
            func = env.lookup(right.name)
            return self._call(func, [left], env, right.name)
        raise ViGoError("Right side of pipe must be a function call")

    def _destructure(self, node, env):
        val = self.eval(node.value, env)
        if not isinstance(val, (list, tuple)): raise ViGoError("Right side of destructure must be a list")
        for i, name in enumerate(node.names):
            if isinstance(name, tuple) and name[0] == 'tuple':
                sub = val[i] if i < len(val) else []
                for j, sn in enumerate(name[1]): env.define(sn, sub[j] if j < len(sub) else None)
            else: env.define(name, val[i] if i < len(val) else None)
        return val

    def _assign(self, node, env):
        if isinstance(node.target, Variable):
            if node.target.name in self.constants:
                raise ViGoError(f"Cannot modify constant '{node.target.name}'")
            cur = env.lookup(node.target.name)
            nv = self._apply_assign_op(cur, self.eval(node.value, env), node.op)
            env.assign(node.target.name, nv); return nv
        elif isinstance(node.target, (DotAccess, IndexAccess)):
            return self._complex_assign(node.target, node.op, self.eval(node.value, env), env)

    def _complex_assign(self, target, op, value, env):
        if isinstance(target, DotAccess):
            obj = self.eval(target.object, env)
            cur = obj.get(target.attr, None) if isinstance(obj, dict) else (
                obj.env.lookup(target.attr) if isinstance(obj, ViGoInstance) and target.attr in obj.env.variables else None)
            nv = self._apply_assign_op(cur if cur is not None else 0 if op != '=' else None, value, op)
            if isinstance(obj, dict): obj[target.attr] = nv
            elif isinstance(obj, ViGoInstance): obj.env.variables[target.attr] = nv
            return nv
        elif isinstance(target, IndexAccess):
            obj = self.eval(target.object, env); idx = self.eval(target.index, env)
            cur = obj.get(idx, 0) if isinstance(obj, dict) else (obj[idx] if isinstance(obj, list) and idx < len(obj) else 0)
            nv = self._apply_assign_op(cur, value, op)
            if isinstance(obj, dict): obj[idx] = nv
            elif isinstance(obj, list):
                if idx < len(obj): obj[idx] = nv
                else: obj.append(nv)
            return nv

    def _apply_assign_op(self, cur, right, op):
        if op == '=': return right
        if cur is None: cur = 0
        if op == '+=': return str(cur) + str(right) if isinstance(cur, str) or isinstance(right, str) else cur + right
        elif op == '-=': return cur - right
        elif op == '*=': return cur * right
        elif op == '/=':
            if right == 0: raise ViGoError("Division by zero"); return cur / right
        elif op == '%=':
            if right == 0: raise ViGoError("Modulo by zero"); return cur % right
        return right

    def _if(self, node, env):
        if self.is_truthy(self.eval(node.condition, env)):
            return self.eval_block(node.then_body, env)
        for bc, bb in node.else_body:
            if bc is None or self.is_truthy(self.eval(bc, env)):
                return self.eval_block(bb, env)
        return None

    def _for_in(self, node, env):
        it = self.eval(node.iterable, env)
        result = None
        items = it if isinstance(it, (list, str)) else (it.keys() if isinstance(it, dict) else [])
        for item in items:
            env.define(node.var_name, item)
            try:
                result = self.eval_block(node.body, env)
            except BreakException:
                break
            except ContinueException:
                continue
        return result

    def _loop(self, node, env):
        result = None
        while self.is_truthy(self.eval(node.condition, env)):
            try:
                result = self.eval_block(node.body, env)
            except BreakException:
                break
            except ContinueException:
                continue
        return result

    def _do_while(self, node, env):
        result = None
        while True:
            try: result = self.eval_block(node.body, env)
            except BreakException: break
            except ContinueException: continue
            if not self.is_truthy(self.eval(node.condition, env)): break
        return result

    def _listcomp(self, node, env):
        it = self.eval(node.iterable, env); result = []
        items = it if isinstance(it, (list, str)) else (it.keys() if isinstance(it, dict) else [])
        for item in items:
            ie = Environment(env); ie.define(node.var, item)
            if node.condition is None or self.is_truthy(self.eval(node.condition, ie)):
                result.append(self.eval(node.expr, ie))
        return result

    def _chained_compare(self, node, env):
        operands = [self.eval(o, env) for o in node.operands]
        for i, op in enumerate(node.ops):
            left = operands[i]
            right = operands[i+1]
            if left is None or right is None:
                if op == '==': return left is None and right is None
                if op == '!=': return left is not right
                return False
            if op == '<' and not (left < right): return False
            elif op == '<=' and not (left <= right): return False
            elif op == '>' and not (left > right): return False
            elif op == '>=' and not (left >= right): return False
            elif op == '==' and not (left == right): return False
            elif op == '!=' and not (left != right): return False
        return True

    def _in_expr(self, node, env):
        left = self.eval(node.left, env); right = self.eval(node.right, env)
        result = left in right if isinstance(right, (list, str, dict, set)) else False
        return not result if node.negated else result

    def _binary_op(self, node, env):
        left = self.eval(node.left, env); right = self.eval(node.right, env); op = node.op
        if op in ('==', '!=', '<', '>', '<=', '>='):
            if op in ('==', '!='):
                if left is None and right is None:
                    return op == '=='
                if left is None or right is None:
                    return op == '!='
            if left is None or right is None:
                return False
            return {'==': left == right, '!=': left != right, '<': left < right,
                    '>': left > right, '<=': left <= right, '>=': left >= right}[op]
        if op == '+':
            if isinstance(left, str) or isinstance(right, str): return str(left) + str(right)
            if isinstance(left, list) and isinstance(right, list): return left + right
            if isinstance(left, set) and isinstance(right, set): return left | right
            return left + right
        elif op == '-':
            if isinstance(left, set) and isinstance(right, set): return left - right
            return left - right
        elif op == '*': return str(left) * right if isinstance(left, str) and isinstance(right, int) else (left * right if isinstance(left, list) and isinstance(right, int) else left * right)
        elif op == '/':
            if right == 0: raise ViGoError("Division by zero")
            return left / right
        elif op == '//':
            if right == 0: raise ViGoError("Division by zero")
            return left // right
        elif op == '%':
            if right == 0: raise ViGoError("Modulo by zero")
            return left % right
        elif op == '**': return left ** right
        elif op == '&':
            if isinstance(left, set) and isinstance(right, set): return left & right
            return int(left) & int(right)
        elif op == '|':
            if isinstance(left, set) and isinstance(right, set): return left | right
            return int(left) | int(right)
        elif op == '^':
            if isinstance(left, set) and isinstance(right, set): return left ^ right
            return int(left) ^ int(right)
        elif op == '<<': return int(left) << int(right)
        elif op == '>>': return int(left) >> int(right)
        raise ViGoError(f"Unknown operator: '{op}'")

    def _logical_op(self, node, env):
        left = self.eval(node.left, env)
        if node.op == 'and': return left if not self.is_truthy(left) else self.eval(node.right, env)
        return left if self.is_truthy(left) else self.eval(node.right, env)

    def _unary_op(self, node, env):
        opd = self.eval(node.operand, env)
        return {'!': not self.is_truthy(opd), '-': -opd, 'not': not self.is_truthy(opd), '~': ~int(opd) if opd is not None else 0}[node.op]

    def _index(self, node, env):
        obj = self.eval(node.object, env); idx = self.eval(node.index, env)
        if isinstance(obj, (str, list)):
            try: return obj[int(idx)]
            except: raise ViGoError(f"Subscript {idx} Out of range")
        elif isinstance(obj, dict): return obj.get(idx, None)
        elif isinstance(obj, ViGoInstance):
            k = str(idx)
            try: return obj.env.lookup(k)
            except ViGoError: return obj.cls.closure.lookup(k) if k in obj.cls.closure.variables else None
        raise ViGoError("Type does not support index access")

    def _slice(self, node, env):
        obj = self.eval(node.object, env)
        start = self.eval(node.start, env) if node.start else 0
        end = self.eval(node.end, env) if node.end else None
        if isinstance(obj, (list, str)): return obj[start:end]
        raise ViGoError("Slice only supported for lists and strings")

    def _dot(self, node, env):
        obj = self.eval(node.object, env); attr = node.attr
        if isinstance(obj, ViGoInstance):
            try: return obj.env.lookup(attr)
            except ViGoError: return obj.cls.closure.lookup(attr) if attr in obj.cls.closure.variables else None
        if isinstance(obj, ViGoClass): return obj.closure.lookup(attr)
        if isinstance(obj, ViGoEnum):
            for m, v in obj.members:
                if m == attr:
                    return v
            raise ViGoError(f"Enum '{obj.name}' has no member '{attr}'")
        if isinstance(obj, list):
            if attr == 'push': return BuiltinFunction(lambda item: obj.append(item) or obj, 'push')
            if attr == 'pop': return BuiltinFunction(lambda: obj.pop() if obj else None, 'pop')
            if attr == 'reverse': return BuiltinFunction(lambda: obj.reverse() or obj, 'reverse')
        if isinstance(obj, str):
            if attr == 'upper': return BuiltinFunction(lambda: obj.upper(), 'upper')
            if attr == 'lower': return BuiltinFunction(lambda: obj.lower(), 'lower')
            if attr == 'trim': return BuiltinFunction(lambda: obj.strip(), 'trim')
            if attr == 'split': return BuiltinFunction(lambda delim: obj.split(delim), 'split')
            if attr == 'join': return BuiltinFunction(lambda items: obj.join(items), 'join')
            if attr == 'replace': return BuiltinFunction(lambda old, new: obj.replace(old, new), 'replace')
        if isinstance(obj, dict):
            if attr == 'keys': return BuiltinFunction(lambda: list(obj.keys()), 'keys')
            if attr == 'values': return BuiltinFunction(lambda: list(obj.values()), 'values')
            return obj.get(attr, None)
        raise ViGoError(f"Dot access '{attr}' not supported on {type(obj).__name__}")

    def _interp_str(self, node, env):
        result = ''
        for part in node.parts:
            if isinstance(part, tuple):
                val = self.eval(part[0], env); fmt = part[1]
                result += f"{val:{fmt}}" if fmt else str(val)
            else: result += str(part.value) if isinstance(part, Literal) else str(self.eval(part, env))
        return result

    def _enum_def(self, node, env):
        e = ViGoEnum(node.name, node.members); env.define(node.name, e)
        for m, v in node.members: env.define(f"{node.name}.{m}", v)
        return e

    def _new(self, node, env):
        cls = env.lookup(node.class_name)
        if not isinstance(cls, ViGoClass): raise ViGoError(f"'{node.class_name}' is not a class")
        return self._call(cls, [self.eval(a, env) for a in node.args], env, cls.name)

    def _try(self, node, env):
        try:
            return self.eval_block(node.try_body, env)
        except ReturnException:
            raise
        except ViGoError as e:
            if node.catch_var:
                env.variables[node.catch_var] = str(e).replace("ViGo Error: ", "")
            if node.catch_body:
                return self.eval_block(node.catch_body, env)
        except Exception as e:
            if node.catch_var:
                env.variables[node.catch_var] = str(e).replace("ViGo Error: ", "")
            if node.catch_body:
                return self.eval_block(node.catch_body, env)

    def _load(self, node, env):
        fp = node.filepath
        for d in ['.', os.path.dirname(self.source_file) if self.source_file != '<script>' else '.']:
            c = os.path.join(d, fp)
            if os.path.exists(c): fp = c; break
        with open(fp, 'r', encoding='utf-8') as f: src = f.read()
        sub = Interpreter(source_file=fp); sub.global_env = Environment(self.global_env)
        result = sub.interpret(Parser(Lexer(src)).parse_program())
        if node.alias: env.define(node.alias, {k: v for k, v in sub.global_env.variables.items()})
        else:
            for k, v in sub.global_env.variables.items(): env.define(k, v)
        return result

    def eval_block(self, stmts, env):
        result = None
        for s in stmts: result = self.eval(s, env)
        return result

    def is_truthy(self, v):
        if v is None: return False
        if isinstance(v, bool): return v
        if isinstance(v, (int, float)): return v != 0
        if isinstance(v, str): return v != ''
        if isinstance(v, (list, tuple, dict, set)): return len(v) > 0
        return True


def run_vigo(source_code, source_file='<script>'):
    return Interpreter(source_file=source_file).interpret(Parser(Lexer(source_code)).parse_program())

def run_vigo_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f: return run_vigo(f.read(), filepath)