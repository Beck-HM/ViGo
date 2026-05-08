import os, time
from ..lexer.lexer import Lexer
from ..parser.parser import Parser
from ..parser.ast_nodes import *
from .environment import Environment
from .objects import (BuiltinFunction, ViGoFunction, LambdaFunction, ViGoClass, ViGoInstance, ViGoEnum)
from .errors import (ViGoError, ReturnException, BreakException, ContinueException, AwaitException)
from .builtins import register as register_builtins
from .blocks import eval_block, is_truthy, eval_if, eval_for_in, eval_loop, eval_do_while, eval_switch, eval_try, eval_listcomp


class Interpreter:
    MAX_CALL_DEPTH = 500

    def __init__(self, source_file='<script>'):
        self.global_env = Environment()
        register_builtins(self.global_env)
        self.call_depth = 0; self.source_file = source_file
        self.call_trace = []; self.timeout = None; self.start_time = None
        self.constants = set()
        # Hook system for community extensions
        self.hooks = {
            "before_eval": [],       # (node, env) -> None
            "after_eval": [],        # (node, result, env) -> None
            "before_func_call": [],  # (call_node, args, env) -> None
            "after_func_call": [],   # (call_node, result, env) -> None
            "on_error": [],          # (exception, node, env) -> None
        }

    def register(self, name, func): self.global_env.define(name, BuiltinFunction(func, name))
    def register_object(self, name, obj): self.global_env.define(name, obj)

    def reset(self):
        self.global_env = Environment(); register_builtins(self.global_env)
        self.call_depth = 0; self.call_trace = []; self.constants = set()

    def set_timeout(self, sec): self.timeout = sec

    def register_hook(self, hook_name, callback):
        """Register a hook callback. Supported hooks: before_eval, after_eval,
        before_func_call, after_func_call, on_error."""
        if hook_name in self.hooks:
            self.hooks[hook_name].append(callback)

    def unregister_hook(self, hook_name, callback):
        """Remove a previously registered hook callback."""
        if hook_name in self.hooks and callback in self.hooks[hook_name]:
            self.hooks[hook_name].remove(callback)

    def _check_timeout(self):
        if self.timeout and self.start_time and time.time() - self.start_time > self.timeout:
            raise ViGoError("Script execution timeout")

    def interpret(self, program):
        self.start_time = time.time(); result = None
        for stmt in program.statements: result = self.eval(stmt)
        return result

    def interpret_ir(self, program):
        """Execute via IR: AST → IR → optimized IR → interpret."""
        from ..ir import IRBuilder, IROptimizer
        builder = IRBuilder()
        ir = builder.build(program)
        optimizer = IROptimizer()
        ir = optimizer.optimize(ir)
        self._exec_ir(ir)

    def _exec_ir(self, instructions):
        """Execute a list of IR instructions using a value stack and temp store."""
        temps = {}
        pc = 0
        while pc < len(instructions):
            inst = instructions[pc]

            if inst.opcode == IR_LOAD_CONST:
                temps[inst.result] = inst.operands[0] if inst.operands else None

            elif inst.opcode == IR_ADD:
                left = self._ir_value(inst.operands[0], temps)
                right = self._ir_value(inst.operands[1], temps)
                temps[inst.result] = left + right

            elif inst.opcode == IR_SUB:
                left = self._ir_value(inst.operands[0], temps)
                right = self._ir_value(inst.operands[1], temps)
                temps[inst.result] = left - right

            elif inst.opcode == IR_MUL:
                left = self._ir_value(inst.operands[0], temps)
                right = self._ir_value(inst.operands[1], temps)
                temps[inst.result] = left * right

            elif inst.opcode == IR_DIV:
                left = self._ir_value(inst.operands[0], temps)
                right = self._ir_value(inst.operands[1], temps)
                temps[inst.result] = left / right if right != 0 else 0

            elif inst.opcode in ("IR_SQRT", "IR_ABS", "IR_LEN", "IR_TO_INT",
                                 "IR_TO_FLOAT", "IR_TO_STR", "IR_ROUND",
                                 "IR_FLOOR", "IR_CEIL"):
                import math
                args = [self._ir_value(o, temps) for o in inst.operands]
                op = inst.opcode
                if op == "IR_SQRT": result = math.sqrt(self._n(args[0]))
                elif op == "IR_ABS": result = abs(self._n(args[0]))
                elif op == "IR_LEN": result = len(args[0]) if args[0] is not None else 0
                elif op == "IR_TO_INT": result = int(self._n(args[0]))
                elif op == "IR_TO_FLOAT": result = float(self._n(args[0]))
                elif op == "IR_TO_STR": result = str(args[0])
                elif op == "IR_ROUND": result = round(self._n(args[0]), int(self._n(args[1])) if len(args) > 1 else 0)
                elif op == "IR_FLOOR": result = math.floor(self._n(args[0]))
                elif op == "IR_CEIL": result = math.ceil(self._n(args[0]))
                temps[inst.result] = result

            elif inst.opcode == IR_STORE:
                var_name = inst.operands[0]
                val = self._ir_value(inst.operands[1], temps)
                self.global_env.define(var_name, val)

            elif inst.opcode == IR_LOAD:
                var_name = inst.operands[0]
                temps[inst.result] = self.global_env.lookup(var_name)

            elif inst.opcode == IR_JUMP_IF_FALSE:
                cond = self._ir_value(inst.operands[0], temps)
                if not cond:
                    # Find the label
                    label = inst.operands[1]
                    for j, i2 in enumerate(instructions):
                        if i2.opcode == "IR_LABEL" and i2.operands and i2.operands[0] == label:
                            pc = j
                            break

            elif inst.opcode == "IR_JUMP":
                label = inst.operands[0]
                for j, i2 in enumerate(instructions):
                    if i2.opcode == "IR_LABEL" and i2.operands and i2.operands[0] == label:
                        pc = j
                        break

            elif inst.opcode == IR_CALL:
                func_name = inst.operands[0]
                args = [self._ir_value(a, temps) for a in inst.operands[1:]]
                func = self.global_env.lookup(func_name)
                if isinstance(func, BuiltinFunction):
                    temps[inst.result] = func.func(*args)

            elif inst.opcode == IR_RETURN:
                # Return value is stored in temps; we just stop here for simple IR
                pass

            elif inst.opcode == "IR_LABEL" or inst.opcode == "IR_COMMENT":
                pass

            pc += 1

    def _ir_value(self, operand, temps):
        """Resolve an IR operand: if it's a temp name, look it up; otherwise return as-is."""
        if isinstance(operand, str) and operand in temps:
            return temps[operand]
        return operand

    # ── Block execution helpers (delegated to runtime/blocks.py) ──

    def eval_block(self, stmts, env):
        return eval_block(self, stmts, env)

    def is_truthy(self, v):
        return is_truthy(v)

    # ── AST node dispatch table ──
    _EVAL_DISPATCH = None

    def _init_dispatch(self):
        self._EVAL_DISPATCH = {
            'Program':             self._eval_Program,
            'VarDecl':             self._eval_VarDecl,
            'DestructureDecl':     self._eval_DestructureDecl,
            'AssignStmt':          self._eval_AssignStmt,
            'IfStmt':              self._eval_IfStmt,
            'SkipStmt':            self._eval_SkipStmt,
            'TernaryExpr':         self._eval_TernaryExpr,
            'SwitchStmt':          self._eval_SwitchStmt,
            'ForInStmt':           self._eval_ForInStmt,
            'LoopStmt':            self._eval_LoopStmt,
            'DoWhileStmt':         self._eval_DoWhileStmt,
            'BreakStmt':           self._eval_BreakStmt,
            'ContinueStmt':        self._eval_ContinueStmt,
            'SureStmt':            self._eval_SureStmt,
            'StaticMethodDef':     self._eval_StaticMethodDef,
            'AbstractMethodDef':   self._eval_AbstractMethodDef,
            'InterfaceDef':        self._eval_InterfaceDef,
            'FuncDef':             self._eval_FuncDef,
            'LambdaExpr':          self._eval_LambdaExpr,
            'ReturnStmt':          self._eval_ReturnStmt,
            'FuncCall':            self._eval_FuncCall,
            'PipeExpr':            self._eval_PipeExpr,
            'RangeExpr':           self._eval_RangeExpr,
            'ExpandExpr':          self._eval_ExpandExpr,
            'OptionalChain':       self._eval_OptionalChain,
            'NullCoalesce':        self._eval_NullCoalesce,
            'ListCompExpr':        self._eval_ListCompExpr,
            'ChainedCompare':      self._eval_ChainedCompare,
            'InExpr':              self._eval_InExpr,
            'BinaryOp':            self._eval_BinaryOp,
            'LogicalOp':           self._eval_LogicalOp,
            'UnaryOp':             self._eval_UnaryOp,
            'Literal':             self._eval_Literal,
            'Variable':            self._eval_Variable,
            'ListLiteral':         self._eval_ListLiteral,
            'DictLiteral':         self._eval_DictLiteral,
            'SetLiteral':          self._eval_SetLiteral,
            'IndexAccess':         self._eval_IndexAccess,
            'SliceAccess':         self._eval_SliceAccess,
            'DotAccess':           self._eval_DotAccess,
            'InterpolatedString':  self._eval_InterpolatedString,
            'LoadStmt':            self._eval_LoadStmt,
            'ClassDef':            self._eval_ClassDef,
            'EnumDef':             self._eval_EnumDef,
            'NewExpr':             self._eval_NewExpr,
            'ThisExpr':            self._eval_ThisExpr,
            'TryStmt':             self._eval_TryStmt,
            'ThrowStmt':           self._eval_ThrowStmt,
            'AwaitExpr':           self._eval_AwaitExpr,
            'SpawnStmt':           self._eval_SpawnStmt,
            'RegexLiteral':        self._eval_RegexLiteral,
        }

    def eval(self, node, env=None):
        self._check_timeout()
        if env is None:
            env = self.global_env

        if self._EVAL_DISPATCH is None:
            self._init_dispatch()

        node_type = type(node).__name__
        handler = self._EVAL_DISPATCH.get(node_type)
        if handler is None:
            raise ViGoError(f"Unknown AST node: {node_type}")

        # before_eval hook
        for hook in self.hooks.get("before_eval", []):
            try:
                hook(node, env)
            except Exception:
                pass

        try:
            result = handler(node, env)

            # after_eval hook
            for hook in self.hooks.get("after_eval", []):
                try:
                    hook(node, result, env)
                except Exception:
                    pass

            return result
        except (ReturnException, BreakException, ContinueException, AwaitException):
            raise
        except ViGoError:
            raise
        except Exception as e:
            # on_error hook
            for hook in self.hooks.get("on_error", []):
                try:
                    hook(e, node, env)
                except Exception:
                    pass
            raise ViGoError(str(e), self.call_trace.copy())

    # ═══════════════════════════════════════════════
    #  Eval handlers — one per AST node type
    # ═══════════════════════════════════════════════

    def _eval_Program(self, node, env):
        return eval_block(self, node.statements, env)

    def _eval_VarDecl(self, node, env):
        if node.name in self.constants:
            raise ViGoError(f"Cannot modify constant '{node.name}'")
        val = self.eval(node.value, env)
        if node.is_const:
            self.constants.add(node.name)
        if env.has(node.name) and not node.is_const:
            env.assign(node.name, val)
        else:
            env.define(node.name, val)
        return val

    def _eval_DestructureDecl(self, node, env):
        return self._destructure(node, env)

    def _eval_AssignStmt(self, node, env):
        if isinstance(node.target, Variable) and node.target.name in self.constants:
            raise ViGoError(f"Cannot modify constant '{node.target.name}'")
        return self._assign(node, env)

    def _eval_IfStmt(self, node, env):
        return eval_if(self, node, env)

    def _eval_SkipStmt(self, node, env):
        result = None
        while not is_truthy(self.eval(node.condition, env)):
            result = eval_block(self, node.body, Environment(env))
        return result

    def _eval_TernaryExpr(self, node, env):
        return self.eval(node.then_expr, env) if is_truthy(self.eval(node.condition, env)) else self.eval(node.else_expr, env)

    def _eval_SwitchStmt(self, node, env):
        return eval_switch(self, node, env)

    def _eval_ForInStmt(self, node, env):
        return eval_for_in(self, node, env)

    def _eval_LoopStmt(self, node, env):
        return eval_loop(self, node, env)

    def _eval_DoWhileStmt(self, node, env):
        return eval_do_while(self, node, env)

    def _eval_BreakStmt(self, node, env):
        raise BreakException()

    def _eval_ContinueStmt(self, node, env):
        raise ContinueException()

    def _eval_SureStmt(self, node, env):
        if not is_truthy(self.eval(node.condition, env)):
            raise ViGoError(f"Assertion failed: {node.message or 'Condition not satisfied'}")
        return True

    def _eval_StaticMethodDef(self, node, env):
        func = ViGoFunction(node.func_def.name, node.func_def.params,
                            node.func_def.defaults, node.func_def.rest_param,
                            node.func_def.body, env, self.source_file)
        func.is_static = True
        env.define(node.func_def.name, func)
        return func

    def _eval_AbstractMethodDef(self, node, env):
        return node

    def _eval_InterfaceDef(self, node, env):
        env.define(node.name, {'__vigo_interface__': True, 'name': node.name, 'methods': node.methods})
        return node

    def _eval_FuncDef(self, node, env):
        func = ViGoFunction(node.name, node.params, node.defaults, node.rest_param, node.body, env, self.source_file)
        env.define(node.name, func)
        return func

    def _eval_LambdaExpr(self, node, env):
        return LambdaFunction(node.params, node.body, env)

    def _eval_ReturnStmt(self, node, env):
        raise ReturnException(self.eval(node.value, env))

    def _eval_FuncCall(self, node, env):
        return self._func_call(node, env)

    def _eval_PipeExpr(self, node, env):
        return self._pipe(node, env)

    def _eval_RangeExpr(self, node, env):
        return list(range(int(self.eval(node.start, env)), int(self.eval(node.end, env)) + 1))

    def _eval_ExpandExpr(self, node, env):
        return self.eval(node.expr, env)

    def _eval_OptionalChain(self, node, env):
        try:
            obj = self.eval(node.object, env)
            if obj is None:
                return None
            result = self.eval(node.chain, Environment(env))
            return None if result is None else result
        except ViGoError:
            return None

    def _eval_NullCoalesce(self, node, env):
        left = self.eval(node.left, env)
        if left is None:
            return self.eval(node.right, env)
        return left

    def _eval_ListCompExpr(self, node, env):
        return eval_listcomp(self, node, env)

    def _eval_ChainedCompare(self, node, env):
        return self._chained_compare(node, env)

    def _eval_InExpr(self, node, env):
        needle = self.eval(node.left, env)
        haystack = self.eval(node.right, env)
        result = needle in haystack if isinstance(haystack, (str, list, set, tuple, dict)) else False
        return not result if node.negated else result

    def _eval_BinaryOp(self, node, env):
        return self._binary_op(node, env)

    def _eval_LogicalOp(self, node, env):
        return self._logical_op(node, env)

    def _eval_UnaryOp(self, node, env):
        return self._unary_op(node, env)

    def _eval_Literal(self, node, env):
        return node.value

    def _eval_Variable(self, node, env):
        return env.lookup(node.name)

    def _eval_ListLiteral(self, node, env):
        result = []
        for el in node.elements:
            val = self.eval(el, env)
            if isinstance(el, ExpandExpr):
                if isinstance(val, list):
                    result.extend(val)
                else:
                    result.append(val)
            else:
                result.append(val)
        return result

    def _eval_DictLiteral(self, node, env):
        return {k: self.eval(v, env) for k, v in node.pairs.items()}

    def _eval_SetLiteral(self, node, env):
        return {self.eval(el, env) for el in node.elements}

    def _eval_IndexAccess(self, node, env):
        return self._index(node, env)

    def _eval_SliceAccess(self, node, env):
        return self._slice(node, env)

    def _eval_DotAccess(self, node, env):
        return self._dot(node, env)

    def _eval_InterpolatedString(self, node, env):
        return self._interp_str(node, env)

    def _eval_LoadStmt(self, node, env):
        return self._load(node, env)

    def _eval_ClassDef(self, node, env):
        return self._class_def(node, env)

    def _eval_EnumDef(self, node, env):
        return self._enum_def(node, env)

    def _eval_NewExpr(self, node, env):
        return self._new(node, env)

    def _eval_ThisExpr(self, node, env):
        return env.lookup('this')

    def _eval_TryStmt(self, node, env):
        return eval_try(self, node, env)

    def _eval_ThrowStmt(self, node, env):
        raise ViGoError(str(self.eval(node.value, env)))

    def _eval_AwaitExpr(self, node, env):
        val = self.eval(node.value, env)
        # Numeric sleep
        if isinstance(val, (int, float)):
            raise AwaitException(float(val))
        # List of task names
        if isinstance(val, list):
            from .eventloop import get_event_loop
            loop = get_event_loop()
            return loop.await_all(val)
        # Single task name
        if isinstance(val, str):
            from .eventloop import get_event_loop
            loop = get_event_loop()
            return loop.await_all([val])
        raise AwaitException(float(val) if isinstance(val, (int, float)) else 0)

    def _eval_SpawnStmt(self, node, env):
        from .eventloop import get_event_loop
        loop = get_event_loop()
        if isinstance(node.expr, FuncCall):
            func = self.eval(node.expr.name, env)
            evaluated_args = [self.eval(a, env) for a in node.expr.args]
            name = node.name or f"task_{len(loop.tasks)}"
            if isinstance(func, BuiltinFunction):
                loop.spawn(name, func.func, evaluated_args)
            else:
                loop.spawn(name, func, evaluated_args)
        return node.name or "task"

    def _eval_RegexLiteral(self, node, env):
        import re
        flags = 0
        if 'i' in node.flags: flags |= re.IGNORECASE
        if 'm' in node.flags: flags |= re.MULTILINE
        if 's' in node.flags: flags |= re.DOTALL
        return re.compile(node.pattern, flags)

    # ═══════════════════════════════════════════════
    #  Expression & object logic (remain in interpreter)
    # ═══════════════════════════════════════════════

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
            elif isinstance(obj, (list, str, set)):
                func = self._dot(DotAccess(Literal(obj), mn), env)
            else:
                func = self._dot(DotAccess(Literal(obj), mn), env)
        elif isinstance(node.name, Variable):
            func = env.lookup(node.name.name); func_name = node.name.name
        else:
            func = self.eval(node.name, env)

        # before_func_call hook
        for hook in self.hooks.get("before_func_call", []):
            try:
                hook(node, args, env)
            except Exception:
                pass

        result = self._call(func, args, env, func_name, this_obj)

        # after_func_call hook
        for hook in self.hooks.get("after_func_call", []):
            try:
                hook(node, result, env)
            except Exception:
                pass

        return result

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
            # Attach symbol table for fast variable lookup
            if hasattr(func, 'symbol_table') and func.symbol_table is not None:
                call_env.symbol_table = func.symbol_table
            if this_obj is not None:
                call_env.define('this', this_obj)
            for p, a in zip(func.params, final_args[:expected]): call_env.define(p, a)
            if func.rest_param: call_env.define(func.rest_param, final_args[expected] if len(final_args) > expected else [])
            self.call_depth += 1; self.call_trace.append(f"{func_name}()")
            try: return eval_block(self, func.body, call_env)
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
                        eval_block(self, init_f.body, ce)
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

    @staticmethod
    def _null_safe_compare(left, right, op):
        """Compare two values with null safety. Returns comparison result or False on TypeError."""
        if left is None or right is None:
            if op == '==':
                return left is None and right is None
            if op == '!=':
                return left is not right
            return False
        try:
            if op == '<':   return left < right
            if op == '<=':  return left <= right
            if op == '>':   return left > right
            if op == '>=':  return left >= right
            if op == '==':  return left == right
            if op == '!=':  return left != right
        except TypeError:
            return False
        return False

    def _chained_compare(self, node, env):
        try:
            operands = [self.eval(o, env) for o in node.operands]
        except ViGoError:
            return False
        for i, op in enumerate(node.ops):
            left = operands[i]
            right = operands[i+1]
            if not self._null_safe_compare(left, right, op):
                return False
        return True

    def _binary_op(self, node, env):
        left = self.eval(node.left, env)
        right = self.eval(node.right, env)
        op = node.op

        if op in ('==', '!=', '<', '>', '<=', '>='):
            return self._null_safe_compare(left, right, op)

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
        if node.op == 'and': return left if not is_truthy(left) else self.eval(node.right, env)
        return left if is_truthy(left) else self.eval(node.right, env)

    def _unary_op(self, node, env):
        opd = self.eval(node.operand, env)
        return {'!': not is_truthy(opd), '-': -opd, 'not': not is_truthy(opd), '~': ~int(opd) if opd is not None else 0}[node.op]

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
            if attr == 'extend': return BuiltinFunction(lambda other: obj.extend(other) or obj, 'extend')
            if attr == 'insert': return BuiltinFunction(lambda idx, item: obj.insert(int(idx), item) or obj, 'insert')
            if attr == 'remove': return BuiltinFunction(lambda item: obj.remove(item) if item in obj else None or obj, 'remove')
            if attr == 'find': return BuiltinFunction(lambda item: obj.index(item) if item in obj else -1, 'find')
            if attr == 'sort': return BuiltinFunction(lambda key=None, reverse=False: obj.sort(key=key, reverse=reverse) or obj, 'sort')
        if isinstance(obj, str):
            if attr == 'upper': return BuiltinFunction(lambda: obj.upper(), 'upper')
            if attr == 'lower': return BuiltinFunction(lambda: obj.lower(), 'lower')
            if attr == 'trim': return BuiltinFunction(lambda: obj.strip(), 'trim')
            if attr == 'split': return BuiltinFunction(lambda delim: obj.split(delim), 'split')
            if attr == 'join': return BuiltinFunction(lambda items: obj.join(items), 'join')
            if attr == 'replace': return BuiltinFunction(lambda old, new: obj.replace(old, new), 'replace')
            if attr == 'startswith': return BuiltinFunction(lambda prefix: obj.startswith(prefix), 'startswith')
            if attr == 'endswith': return BuiltinFunction(lambda suffix: obj.endswith(suffix), 'endswith')
            if attr == 'contains': return BuiltinFunction(lambda sub: sub in obj, 'contains')
            if attr == 'find': return BuiltinFunction(lambda sub: obj.find(sub), 'find')
            if attr == 'count': return BuiltinFunction(lambda sub: obj.count(sub), 'count')
        if hasattr(obj, 'pattern'):  # compiled regex object
            if attr == 'test':
                return BuiltinFunction(lambda s: obj.search(s) is not None, 'test')
            if attr == 'exec':
                return BuiltinFunction(lambda s: obj.search(s), 'exec')
            if attr == 'findall':
                return BuiltinFunction(lambda s: obj.findall(s), 'findall')
        if isinstance(obj, dict):
            if attr == 'keys': return BuiltinFunction(lambda: list(obj.keys()), 'keys')
            if attr == 'values': return BuiltinFunction(lambda: list(obj.values()), 'values')
            if attr == 'get': return BuiltinFunction(lambda key, default=None: obj.get(key, default), 'get')
            if attr == 'items': return BuiltinFunction(lambda: list(obj.items()), 'items')
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


def run_vigo(source_code, source_file='<script>'):
    return Interpreter(source_file=source_file).interpret(Parser(Lexer(source_code)).parse_program())

def run_vigo_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f: return run_vigo(f.read(), filepath)