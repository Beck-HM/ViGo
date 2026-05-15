"""ViGo Bytecode Compiler: AST -> Bytecode"""
from ..parser.ast_nodes import *
from .instructions import *


class BytecodeCompiler:
    def __init__(self):
        self.code = []
        self.constants = []
        self.labels = {}
        self._label_counter = 0

    def _new_label(self):
        self._label_counter += 1
        return f"L{self._label_counter}"

    def emit(self, op, *operands):
        self.code.append((op, *operands))

    def _add_constant(self, value):
        if value not in self.constants:
            self.constants.append(value)
        return self.constants.index(value)

    def compile(self, program):
        for stmt in program.statements:
            self._compile_statement(stmt)
        self.emit(HALT)
        return {
            "code": self.code,
            "constants": self.constants,
            "labels": self.labels
        }

    def _compile_statement(self, node):
        if isinstance(node, VarDecl):
            self._compile_expression(node.value)
            if node.name:
                self.emit(STORE, node.name)
        elif isinstance(node, FuncDef):
            self._compile_function(node)
            self.emit(STORE, node.name)
        elif isinstance(node, AssignStmt):
            self._compile_expression(node.value)
            if isinstance(node.target, Variable):
                self.emit(STORE, node.target.name)
            elif isinstance(node.target, DotAccess):
                self._compile_expression(node.target.object)
                self.emit(SET_ATTR, node.target.attr)
        elif isinstance(node, ReturnStmt):
            self._compile_expression(node.value)
            self.emit(RETURN)
        elif isinstance(node, IfStmt):
            self._compile_if(node)
        elif isinstance(node, LoopStmt):
            self._compile_loop(node)
        elif isinstance(node, ForInStmt):
            self._compile_for_in(node)
        elif isinstance(node, ClassDef):
            self._compile_class(node)
        elif isinstance(node, StaticMethodDef):
            self._compile_function(node.func_def)
        elif isinstance(node, TernaryExpr):
            self._compile_ternary(node)
        elif isinstance(node, SwitchStmt):
            self._compile_switch(node)
        elif isinstance(node, BreakStmt):
            self.emit(JUMP, "__break__")
        elif isinstance(node, ContinueStmt):
            self.emit(JUMP, "__continue__")
        elif isinstance(node, SureStmt):
            self._compile_expression(node.condition)
        elif isinstance(node, ThrowStmt):
            self._compile_expression(node.value)
        elif isinstance(node, TryStmt):
            for s in node.try_body:
                self._compile_statement(s)
        elif isinstance(node, SkipStmt):
            self._compile_if(IfStmt(UnaryOp('not', node.condition), node.body, []))
        elif isinstance(node, DoWhileStmt):
            self._compile_loop(LoopStmt(Literal(True), node.body + [IfStmt(UnaryOp('not', node.condition), [BreakStmt()], [])]))
        elif isinstance(node, PipeExpr):
            self._compile_expression(node)
            self.emit(POP)
        elif isinstance(node, NewExpr):
            self._compile_expression(node)
            self.emit(POP)
        else:
            self._compile_expression(node)
            self.emit(POP)

    def _compile_expression(self, node):
        if isinstance(node, Literal):
            self.emit(PUSH, self._add_constant(node.value))
        elif isinstance(node, Variable):
            self.emit(LOAD, node.name)
        elif isinstance(node, BinaryOp):
            self._compile_expression(node.left)
            self._compile_expression(node.right)
            op_map = {
                '+': ADD, '-': SUB, '*': MUL, '/': DIV,
                '%': MOD, '**': POW, '//': FLOOR_DIV,
                '==': EQ, '!=': NEQ, '<': LT, '>': GT,
                '<=': LE, '>=': GE,
            }
            self.emit(op_map.get(node.op, ADD))
        elif isinstance(node, UnaryOp):
            self._compile_expression(node.operand)
            self.emit(NEG if node.op == '-' else NOT_OP)
        elif isinstance(node, FuncCall):
            if isinstance(node.name, Variable):
                for arg in node.args:
                    self._compile_expression(arg)
                self.emit(CALL, node.name.name, len(node.args))
            elif isinstance(node.name, DotAccess):
                # obj.method(args): push obj first, then args
                self._compile_expression(node.name.object)
                for arg in node.args:
                    self._compile_expression(arg)
                self.emit(CALL_METHOD, node.name.attr, len(node.args))
        elif isinstance(node, ListLiteral):
            for el in node.elements:
                self._compile_expression(el)
            self.emit(MAKE_LIST, len(node.elements))
        elif isinstance(node, DictLiteral):
            for k, v in node.pairs.items():
                self._compile_expression(Literal(k))
                self._compile_expression(v)
            self.emit(MAKE_DICT, len(node.pairs))
        elif isinstance(node, IndexAccess):
            self._compile_expression(node.object)
            self._compile_expression(node.index)
            self.emit(INDEX)
        elif isinstance(node, DotAccess):
            self._compile_expression(node.object)
            self.emit(GET_ATTR, node.attr)
        elif isinstance(node, LogicalOp):
            self._compile_expression(node.left)
            self._compile_expression(node.right)
            self.emit(AND if node.op == 'and' else ADD)
        elif isinstance(node, RangeExpr):
            self._compile_expression(node.start)
            self._compile_expression(node.end)
            self.emit(CALL, "range", 2)
        elif isinstance(node, PipeExpr):
            self._compile_pipe(node)
        elif isinstance(node, NewExpr):
            for arg in node.args:
                self._compile_expression(arg)
            self.emit(CALL, "new_" + node.class_name, len(node.args))
        elif isinstance(node, ThisExpr):
            self.emit(LOAD, "this")
        elif isinstance(node, LambdaExpr):
            self._compile_function(node)
        elif isinstance(node, NullCoalesce):
            else_label = self._new_label()
            end_label = self._new_label()
            self._compile_expression(node.left)
            self.emit(DUP)
            self.emit(PUSH, self._add_constant(None))
            self.emit(EQ)
            self.emit(JUMP_IF_FALSE, else_label)
            self.emit(POP)
            self._compile_expression(node.right)
            self.emit(JUMP, end_label)
            self.emit(LABEL, else_label)
            self.emit(LABEL, end_label)
        else:
            self.emit(PUSH, self._add_constant(None))

    def _compile_if(self, node):
        else_label = self._new_label()
        end_label = self._new_label()

        self._compile_expression(node.condition)
        self.emit(JUMP_IF_FALSE, else_label)

        for stmt in node.then_body:
            self._compile_statement(stmt)
        self.emit(JUMP, end_label)

        self.emit(LABEL, else_label)
        for cond, body in node.else_body:
            if cond is not None:
                next_label = self._new_label()
                self._compile_expression(cond)
                self.emit(JUMP_IF_FALSE, next_label)
                for stmt in body:
                    self._compile_statement(stmt)
                self.emit(JUMP, end_label)
                self.emit(LABEL, next_label)
            else:
                for stmt in body:
                    self._compile_statement(stmt)

        self.emit(LABEL, end_label)

    def _compile_loop(self, node):
        start_label = self._new_label()
        end_label = self._new_label()

        self.emit(LABEL, start_label)
        self._compile_expression(node.condition)
        self.emit(JUMP_IF_FALSE, end_label)

        for stmt in node.body:
            if isinstance(stmt, BreakStmt):
                stmt = None
                self.emit(JUMP, end_label)
            elif isinstance(stmt, ContinueStmt):
                stmt = None
                self.emit(JUMP, start_label)
            if stmt is not None:
                self._compile_statement(stmt)
        self.emit(JUMP, start_label)
        self.emit(LABEL, end_label)

    def _compile_for_in(self, node):
        self._compile_expression(node.iterable)
        self.emit(STORE, "_iter")
        self.emit(PUSH, self._add_constant(0))
        self.emit(STORE, "_idx")

        start_label = self._new_label()
        end_label = self._new_label()

        self.emit(LABEL, start_label)
        self.emit(LOAD, "_idx")
        self.emit(LOAD, "_iter")
        self.emit(CALL, "len", 1)
        self.emit(LT)
        self.emit(JUMP_IF_FALSE, end_label)

        self.emit(LOAD, "_iter")
        self.emit(LOAD, "_idx")
        self.emit(INDEX)
        self.emit(STORE, node.var_name)

        for stmt in node.body:
            if isinstance(stmt, BreakStmt):
                self.emit(JUMP, end_label)
            elif isinstance(stmt, ContinueStmt):
                self.emit(LOAD, "_idx")
                self.emit(PUSH, self._add_constant(1))
                self.emit(ADD)
                self.emit(STORE, "_idx")
                self.emit(JUMP, start_label)
            else:
                self._compile_statement(stmt)

        self.emit(LOAD, "_idx")
        self.emit(PUSH, self._add_constant(1))
        self.emit(ADD)
        self.emit(STORE, "_idx")
        self.emit(JUMP, start_label)
        self.emit(LABEL, end_label)

    def _compile_function(self, node):
        func_compiler = BytecodeCompiler()
        for stmt in node.body:
            func_compiler._compile_statement(stmt)
        func_compiler.emit(RETURN)
        func_bytecode = {
            "code": func_compiler.code,
            "constants": func_compiler.constants,
            "labels": func_compiler.labels,
            "params": node.params if hasattr(node, 'params') else [],
            "name": node.name if hasattr(node, 'name') else '<lambda>',
        }
        self.emit(MAKE_FUNC, self._add_constant(func_bytecode))

    def _compile_class(self, node):
        for stmt in node.body:
            if isinstance(stmt, FuncDef):
                func_compiler = BytecodeCompiler()
                for s in stmt.body:
                    func_compiler._compile_statement(s)
                func_compiler.emit(RETURN)
                func_bytecode = {
                    "code": func_compiler.code,
                    "constants": func_compiler.constants,
                    "labels": func_compiler.labels,
                    "params": stmt.params,
                    "name": stmt.name,
                }
                idx = self._add_constant(func_bytecode)
                self.emit(STORE_METHOD, node.name, stmt.name, idx)
            elif isinstance(stmt, StaticMethodDef):
                func_compiler = BytecodeCompiler()
                for s in stmt.func_def.body:
                    func_compiler._compile_statement(s)
                func_compiler.emit(RETURN)
                func_bytecode = {
                    "code": func_compiler.code,
                    "constants": func_compiler.constants,
                    "labels": func_compiler.labels,
                    "params": stmt.func_def.params,
                    "name": stmt.func_def.name,
                    "is_static": True,
                }
                idx = self._add_constant(func_bytecode)
                self.emit(STORE_METHOD, node.name, stmt.func_def.name, idx)

    def _compile_ternary(self, node):
        else_label = self._new_label()
        end_label = self._new_label()

        self._compile_expression(node.condition)
        self.emit(JUMP_IF_FALSE, else_label)
        self._compile_expression(node.then_expr)
        self.emit(JUMP, end_label)
        self.emit(LABEL, else_label)
        self._compile_expression(node.else_expr)
        self.emit(LABEL, end_label)

    def _compile_switch(self, node):
        end_label = self._new_label()
        cases = node.cases

        for i, (case_val, case_body) in enumerate(cases):
            next_label = self._new_label()

            if isinstance(case_val, tuple) and case_val[0] == 'range':
                self._compile_expression(node.expr)
                self.emit(PUSH, self._add_constant(case_val[1]))
                self.emit(GE)
                self._compile_expression(node.expr)
                self.emit(PUSH, self._add_constant(case_val[2]))
                self.emit(LE)
                self.emit(AND)
            else:
                self._compile_expression(node.expr)
                self.emit(PUSH, self._add_constant(case_val))
                self.emit(EQ)

            self.emit(JUMP_IF_FALSE, next_label)
            for stmt in case_body:
                self._compile_statement(stmt)
            self.emit(JUMP, end_label)
            self.emit(LABEL, next_label)

        if node.default_body:
            for stmt in node.default_body:
                self._compile_statement(stmt)

        self.emit(LABEL, end_label)

    def _compile_pipe(self, node):
        # Compile: left |> right(args)
        # Stack order: left, arg1, arg2, ... → CALL with arg_count + 1
        if isinstance(node.right, FuncCall):
            call = node.right
            if isinstance(call.name, Variable):
                self._compile_expression(node.left)
                for arg in call.args:
                    self._compile_expression(arg)
                self.emit(CALL, call.name.name, len(call.args) + 1)
            elif isinstance(call.name, DotAccess):
                # left |> obj.method(args)
                self._compile_expression(node.left)
                self._compile_expression(call.name.object)
                for arg in call.args:
                    self._compile_expression(arg)
                self.emit(CALL_METHOD, call.name.attr, len(call.args) + 1)
        elif isinstance(node.right, Variable):
            self._compile_expression(node.left)
            self.emit(CALL, node.right.name, 1)