"""IR → Bytecode Compiler — translates optimized IR to VM bytecode."""
from .instructions import *


class IRToBytecode:
    """Compile IR instruction list to VM-executable bytecode."""

    def compile(self, ir_instructions):
        """Convert IR instructions to bytecode dict with code, constants, labels."""
        code = []
        constants = []
        const_map = {}
        label_pos = {}

        def add_constant(val):
            if val not in const_map:
                const_map[val] = len(constants)
                constants.append(val)
            return const_map[val]

        # First pass: record label positions
        for inst in ir_instructions:
            if inst.opcode == "IR_LABEL":
                label_pos[inst.operands[0]] = len(code)

        # Second pass: translate instructions
        for inst in ir_instructions:
            op = inst.opcode

            if op == IR_LOAD_CONST:
                val = inst.operands[0] if inst.operands else None
                idx = add_constant(val)
                code.append([PUSH, idx])
                if inst.result:
                    code.append([STORE, inst.result])

            elif op == IR_LOAD:
                name = inst.operands[0]
                code.append([LOAD, name])
                if inst.result:
                    code.append([STORE, inst.result])

            elif op == IR_ADD:
                code.append([ADD])

            elif op == IR_SUB:
                code.append([SUB])

            elif op == IR_MUL:
                code.append([MUL])

            elif op == IR_DIV:
                code.append([DIV])

            elif op == IR_STORE:
                name = inst.operands[0]
                code.append([STORE, name])

            elif op == IR_JUMP_IF_FALSE:
                cond_temp = inst.operands[0]
                label = inst.operands[1]
                code.append([LOAD, cond_temp])
                code.append([JUMP_IF_FALSE, label])

            elif op == "IR_JUMP":
                label = inst.operands[0]
                code.append([JUMP, label])

            elif op == IR_CALL:
                func_name = inst.operands[0]
                args = inst.operands[1:]
                for arg in args:
                    code.append([LOAD, arg])
                code.append([CALL, func_name, len(args)])
                if inst.result:
                    code.append([STORE, inst.result])

            elif op in ("IR_SQRT", "IR_ABS", "IR_LEN", "IR_TO_INT",
                        "IR_TO_FLOAT", "IR_TO_STR", "IR_ROUND",
                        "IR_FLOOR", "IR_CEIL"):
                # Inlined builtins: map to CALL
                name_map = {
                    "IR_SQRT": "sqrt", "IR_ABS": "abs", "IR_LEN": "len",
                    "IR_TO_INT": "int", "IR_TO_FLOAT": "float",
                    "IR_TO_STR": "str", "IR_ROUND": "round",
                    "IR_FLOOR": "floor", "IR_CEIL": "ceil",
                }
                builtin_name = name_map.get(op, op[3:].lower())
                code.append([CALL, builtin_name, len(inst.operands)])
                if inst.result:
                    code.append([STORE, inst.result])

            elif op == IR_RETURN:
                val_temp = inst.operands[0] if inst.operands else None
                if val_temp:
                    code.append([LOAD, val_temp])
                code.append([RETURN])

            elif op == "IR_LABEL":
                code.append([LABEL, inst.operands[0]])

            elif op == "IR_COMMENT":
                pass

            elif op == "IR_NEG":
                code.append([NEG])

            elif op == "IR_NOT":
                code.append([NOT_OP])

        code.append([HALT])

        return {
            "code": code,
            "constants": constants,
            "labels": label_pos,
        }