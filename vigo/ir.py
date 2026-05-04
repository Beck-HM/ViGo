"""ViGo Intermediate Representation — AST → IR → Optimized IR"""
from .parser.ast_nodes import *
from .bytecode.instructions import (
    IR_LOAD_CONST, IR_ADD, IR_SUB, IR_MUL, IR_DIV,
    IR_STORE, IR_LOAD, IR_JUMP_IF_FALSE, IR_CALL, IR_RETURN
)


class IRInstruction:
    """A single IR instruction: (opcode, operands, result_temp)."""
    def __init__(self, opcode, operands=None, result=None):
        self.opcode = opcode
        self.operands = operands or []
        self.result = result  # temp variable name

    def __repr__(self):
        ops = ", ".join(str(o) for o in self.operands)
        if self.result:
            return f"{self.result} = {self.opcode} {ops}"
        return f"{self.opcode} {ops}"


class IRBuilder:
    """Translate an AST program into a flat list of IR instructions."""
    def __init__(self):
        self.instructions = []
        self._temp_counter = 0

    def _new_temp(self):
        self._temp_counter += 1
        return f"t{self._temp_counter}"

    def build(self, program):
        self.instructions = []
        for stmt in program.statements:
            self._visit(stmt)
        return self.instructions

    def _emit(self, opcode, operands=None, result=None):
        inst = IRInstruction(opcode, operands, result)
        self.instructions.append(inst)
        return inst

    def _visit(self, node):
        """Dispatch AST node to the appropriate visitor."""
        if isinstance(node, VarDecl):
            return self._visit_vardecl(node)
        elif isinstance(node, AssignStmt):
            return self._visit_assign(node)
        elif isinstance(node, IfStmt):
            return self._visit_if(node)
        elif isinstance(node, ForInStmt):
            return self._visit_for(node)
        elif isinstance(node, LoopStmt):
            return self._visit_loop(node)
        elif isinstance(node, ReturnStmt):
            return self._visit_return(node)
        elif isinstance(node, FuncCall):
            return self._visit_call(node)
        elif isinstance(node, BinaryOp):
            return self._visit_binary(node)
        elif isinstance(node, Literal):
            return self._visit_literal(node)
        elif isinstance(node, Variable):
            return self._visit_variable(node)
        elif isinstance(node, ListLiteral):
            return self._visit_list(node)
        elif isinstance(node, FuncDef):
            return self._visit_funcdef(node)
        elif isinstance(node, UnaryOp):
            return self._visit_unary(node)
        else:
            # For unsupported nodes, emit a comment-like placeholder
            self._emit("IR_COMMENT", [f"unsupported: {type(node).__name__}"])

    def _visit_expr(self, node):
        """Visit an expression node and return the temp variable holding its result."""
        if isinstance(node, Literal):
            return self._visit_literal(node)
        elif isinstance(node, Variable):
            return self._visit_variable(node)
        elif isinstance(node, BinaryOp):
            return self._visit_binary(node)
        elif isinstance(node, FuncCall):
            return self._visit_call(node)
        elif isinstance(node, UnaryOp):
            return self._visit_unary(node)
        elif isinstance(node, ListLiteral):
            t = self._new_temp()
            self._emit(IR_LOAD_CONST, [node.elements], t)
            return t
        else:
            t = self._new_temp()
            self._emit("IR_COMMENT", [f"unsupported expr: {type(node).__name__}"], t)
            return t

    def _visit_literal(self, node):
        t = self._new_temp()
        self._emit(IR_LOAD_CONST, [node.value], t)
        return t

    def _visit_variable(self, node):
        t = self._new_temp()
        self._emit(IR_LOAD, [node.name], t)
        return t

    def _visit_binary(self, node):
        left_temp = self._visit_expr(node.left)
        right_temp = self._visit_expr(node.right)

        # Constant folding: if both operands are known constants, compute at build time
        if self._is_const(left_temp) and self._is_const(right_temp):
            left_val = self._get_const(left_temp)
            right_val = self._get_const(right_temp)
            try:
                result = self._compute(left_val, right_val, node.op)
                t = self._new_temp()
                self._emit(IR_LOAD_CONST, [result], t)
                return t
            except Exception:
                pass

        op_map = {
            '+': IR_ADD, '-': IR_SUB, '*': IR_MUL, '/': IR_DIV,
            '//': IR_DIV, '%': IR_DIV, '**': IR_MUL, '^': IR_MUL,
            '&': IR_MUL, '|': IR_MUL,
        }
        opcode = op_map.get(node.op, IR_ADD)
        t = self._new_temp()
        self._emit(opcode, [left_temp, right_temp], t)
        return t

    def _visit_unary(self, node):
        operand_temp = self._visit_expr(node.operand)
        t = self._new_temp()
        self._emit("IR_NEG" if node.op == '-' else "IR_NOT", [operand_temp], t)
        return t

    def _visit_call(self, node):
        args_temps = [self._visit_expr(a) for a in node.args]
        name = node.name.name if isinstance(node.name, Variable) else str(node.name)
        t = self._new_temp()
        self._emit(IR_CALL, [name] + args_temps, t)
        return t

    def _visit_list(self, node):
        t = self._new_temp()
        self._emit(IR_LOAD_CONST, [node.elements], t)
        return t

    def _visit_vardecl(self, node):
        val_temp = self._visit_expr(node.value)
        self._emit(IR_STORE, [node.name, val_temp])

    def _visit_assign(self, node):
        val_temp = self._visit_expr(node.value)
        target = node.target.name if isinstance(node.target, Variable) else str(node.target)
        self._emit(IR_STORE, [target, val_temp])

    def _visit_if(self, node):
        cond_temp = self._visit_expr(node.condition)
        else_label = f"else_{self._temp_counter}"
        end_label = f"end_{self._temp_counter}"
        self._temp_counter += 1
        self._emit(IR_JUMP_IF_FALSE, [cond_temp, else_label])
        for s in node.then_body:
            self._visit(s)
        self._emit("IR_JUMP", [end_label])
        self._emit("IR_LABEL", [else_label])
        for cond, body in node.else_body:
            if cond:
                c_temp = self._visit_expr(cond)
                next_label = f"elif_{self._temp_counter}"
                self._temp_counter += 1
                self._emit(IR_JUMP_IF_FALSE, [c_temp, next_label])
                for s in body:
                    self._visit(s)
                self._emit("IR_JUMP", [end_label])
                self._emit("IR_LABEL", [next_label])
            else:
                for s in body:
                    self._visit(s)
        self._emit("IR_LABEL", [end_label])

    def _visit_for(self, node):
        it_temp = self._visit_expr(node.iterable)
        loop_start = f"for_start_{self._temp_counter}"
        loop_end = f"for_end_{self._temp_counter}"
        self._temp_counter += 1
        self._emit(IR_LOAD, [f"iter({it_temp})"], node.var_name)
        self._emit("IR_LABEL", [loop_start])
        self._emit(IR_LOAD, [f"next({node.var_name}_iter)"], node.var_name)
        self._emit(IR_JUMP_IF_FALSE, [f"{node.var_name}_done", loop_end])
        for s in node.body:
            self._visit(s)
        self._emit("IR_JUMP", [loop_start])
        self._emit("IR_LABEL", [loop_end])

    def _visit_loop(self, node):
        loop_start = f"loop_{self._temp_counter}"
        loop_end = f"loop_end_{self._temp_counter}"
        self._temp_counter += 1
        self._emit("IR_LABEL", [loop_start])
        cond_temp = self._visit_expr(node.condition)
        self._emit(IR_JUMP_IF_FALSE, [cond_temp, loop_end])
        for s in node.body:
            self._visit(s)
        self._emit("IR_JUMP", [loop_start])
        self._emit("IR_LABEL", [loop_end])

    def _visit_return(self, node):
        val_temp = self._visit_expr(node.value)
        self._emit(IR_RETURN, [val_temp])

    def _visit_funcdef(self, node):
        self._emit("IR_LABEL", [f"func_{node.name}"])
        for s in node.body:
            self._visit(s)
        self._emit(IR_RETURN, ["None"])

    # ── Constant folding helpers ──

    def _is_const(self, temp_name):
        """Check if a temp was loaded from a literal constant."""
        for inst in reversed(self.instructions):
            if inst.result == temp_name:
                return inst.opcode == IR_LOAD_CONST
        return False

    def _get_const(self, temp_name):
        """Get the constant value from a temp."""
        for inst in reversed(self.instructions):
            if inst.result == temp_name and inst.opcode == IR_LOAD_CONST:
                return inst.operands[0] if inst.operands else None
        return None

    def _compute(self, left, right, op):
        if op == '+': return left + right
        if op == '-': return left - right
        if op == '*': return left * right
        if op == '/':
            if right == 0: return 0
            return left / right
        if op == '//':
            if right == 0: return 0
            return left // right
        if op == '%':
            if right == 0: return 0
            return left % right
        if op == '**': return left ** right
        return left


class IROptimizer:
    """Optimize IR: constant folding, dead code elimination."""

    def optimize(self, instructions):
        # Pass 1: Dead code elimination — remove temps never used
        optimized = self._eliminate_dead_code(instructions)
        return optimized

    def _eliminate_dead_code(self, instructions):
        """Remove instructions whose result temp is never used by any later instruction."""
        # Collect all temps that are used as operands
        used_temps = set()
        for inst in instructions:
            for op in inst.operands:
                if isinstance(op, str) and op.startswith('t'):
                    used_temps.add(op)

        # Keep only instructions whose result is used, or that have side effects
        result = []
        for inst in instructions:
            # Always keep instructions with side effects (STORE, CALL, RETURN, JUMP, LABEL)
            if inst.opcode in (IR_STORE, IR_CALL, IR_RETURN, "IR_JUMP", "IR_JUMP_IF_FALSE", "IR_LABEL", "IR_COMMENT"):
                result.append(inst)
            elif inst.result is None:
                # No result — keep it
                result.append(inst)
            elif inst.result in used_temps:
                # Result is used — keep it
                result.append(inst)
            # else: result not used — drop it (dead code)

        return result