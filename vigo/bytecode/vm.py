"""ViGo Bytecode Virtual Machine - Call stack edition"""
from .instructions import *


class CallFrame:
    def __init__(self, code, constants, labels, ip=0):
        self.code = code
        self.constants = constants
        self.labels = labels
        self.ip = ip
        self.stack = []
        self.variables = {}


class VirtualMachine:
    def __init__(self):
        self.frames = []
        self.globals = {}
        self.classes = {}
        self._dispatch = {
            HALT:           self._op_halt,
            PUSH:           self._op_push,
            POP:            self._op_pop,
            DUP:            self._op_dup,
            LOAD:           self._op_load,
            STORE:          self._op_store,
            STORE_METHOD:   self._op_store_method,
            ADD:            self._op_add,
            SUB:            self._op_sub,
            MUL:            self._op_mul,
            DIV:            self._op_div,
            FLOOR_DIV:      self._op_floordiv,
            MOD:            self._op_mod,
            POW:            self._op_pow,
            NEG:            self._op_neg,
            NOT_OP:         self._op_not,
            AND:            self._op_and,
            EQ:             self._op_eq,
            LT:             self._op_lt,
            GT:             self._op_gt,
            LE:             self._op_le,
            GE:             self._op_ge,
            NEQ:            self._op_neq,
            JUMP:           self._op_jump,
            JUMP_IF_FALSE:  self._op_jump_if_false,
            JUMP_IF_TRUE:   self._op_jump_if_true,
            CALL:           self._op_call,
            CALL_METHOD:    self._op_call_method,
            RETURN:         self._op_return,
            MAKE_LIST:      self._op_make_list,
            MAKE_DICT:      self._op_make_dict,
            INDEX:          self._op_index,
            GET_ATTR:       self._op_get_attr,
            SET_ATTR:       self._op_set_attr,
            MAKE_FUNC:      self._op_make_func,
            LABEL:          self._op_label,
        }
        self._builtins = {
            "print": self._builtin_print,
            "len":   self._builtin_len,
            "str":   self._builtin_str,
            "int":   self._builtin_int,
            "float": self._builtin_float,
            "range": self._builtin_range,
            "sum":   self._builtin_sum,
        }

    def load(self, bytecode):
        frame = CallFrame(
            bytecode["code"],
            bytecode["constants"],
            bytecode.get("labels", {}),
        )
        self.frames = [frame]

    def _current(self):
        return self.frames[-1]

    def run(self):
        while self.frames:
            f = self._current()
            label_pos = self._compute_labels(f)

            while f.ip < len(f.code):
                instr = f.code[f.ip]
                op = instr[0]
                handler = self._dispatch.get(op)
                if handler:
                    result = handler(f, instr, label_pos)
                    if result is not None:
                        return result
                f.ip += 1
        return None

    # ── Instruction handlers ──

    def _op_halt(self, f, instr, label_pos):
        if len(self.frames) == 1:
            return f.stack[-1] if f.stack else None
        result = f.stack[-1] if f.stack else None
        self.frames.pop()
        self._current().stack.append(result)
        f.ip = len(f.code)  # break inner loop
        return None

    def _op_push(self, f, instr, label_pos):
        f.stack.append(f.constants[instr[1]])

    def _op_pop(self, f, instr, label_pos):
        if f.stack:
            f.stack.pop()

    def _op_dup(self, f, instr, label_pos):
        if f.stack:
            f.stack.append(f.stack[-1])

    def _op_load(self, f, instr, label_pos):
        name = instr[1]
        val = f.variables.get(name)
        if val is None:
            for frame in reversed(self.frames):
                val = frame.variables.get(name)
                if val is not None:
                    break
        if val is None:
            val = self.globals.get(name)
        f.stack.append(val)

    def _op_store(self, f, instr, label_pos):
        name = instr[1]
        if f.stack:
            f.variables[name] = f.stack.pop()

    def _op_store_method(self, f, instr, label_pos):
        class_name, method_name, const_idx = instr[1], instr[2], instr[3]
        func_obj = f.constants[const_idx]
        if class_name not in self.classes:
            self.classes[class_name] = {}
        self.classes[class_name][method_name] = func_obj

    def _op_add(self, f, instr, label_pos):
        b = f.stack.pop() if f.stack else 0
        a = f.stack.pop() if f.stack else 0
        if isinstance(a, str) or isinstance(b, str):
            f.stack.append(str(a) + str(b))
        elif isinstance(a, list) and isinstance(b, list):
            f.stack.append(a + b)
        else:
            f.stack.append(self._n(a) + self._n(b))

    def _op_sub(self, f, instr, label_pos):
        b = f.stack.pop() if f.stack else 0
        a = f.stack.pop() if f.stack else 0
        f.stack.append(self._n(a) - self._n(b))

    def _op_mul(self, f, instr, label_pos):
        b = f.stack.pop() if f.stack else 1
        a = f.stack.pop() if f.stack else 1
        if isinstance(a, str) and isinstance(b, int):
            f.stack.append(a * b)
        elif isinstance(a, list) and isinstance(b, int):
            f.stack.append(a * b)
        else:
            f.stack.append(self._n(a) * self._n(b))

    def _op_div(self, f, instr, label_pos):
        b = f.stack.pop() if f.stack else 1
        a = f.stack.pop() if f.stack else 0
        denom = self._n(b)
        f.stack.append(self._n(a) / denom if denom != 0 else 0)

    def _op_floordiv(self, f, instr, label_pos):
        b = f.stack.pop() if f.stack else 1
        a = f.stack.pop() if f.stack else 0
        denom = self._n(b)
        f.stack.append(self._n(a) // denom if denom != 0 else 0)

    def _op_mod(self, f, instr, label_pos):
        b = f.stack.pop() if f.stack else 1
        a = f.stack.pop() if f.stack else 0
        denom = self._n(b)
        f.stack.append(self._n(a) % denom if denom != 0 else 0)

    def _op_pow(self, f, instr, label_pos):
        b = f.stack.pop() if f.stack else 1
        a = f.stack.pop() if f.stack else 0
        f.stack.append(self._n(a) ** self._n(b))

    def _op_neg(self, f, instr, label_pos):
        a = f.stack.pop() if f.stack else 0
        f.stack.append(-self._n(a))

    def _op_not(self, f, instr, label_pos):
        a = f.stack.pop() if f.stack else None
        f.stack.append(not a)

    def _op_and(self, f, instr, label_pos):
        b = f.stack.pop() if f.stack else False
        a = f.stack.pop() if f.stack else False
        f.stack.append(a and b)

    def _op_eq(self, f, instr, label_pos):
        b = f.stack.pop(); a = f.stack.pop()
        f.stack.append(a == b)

    def _op_lt(self, f, instr, label_pos):
        b = f.stack.pop(); a = f.stack.pop()
        f.stack.append(self._n(a) < self._n(b))

    def _op_gt(self, f, instr, label_pos):
        b = f.stack.pop(); a = f.stack.pop()
        f.stack.append(self._n(a) > self._n(b))

    def _op_le(self, f, instr, label_pos):
        b = f.stack.pop(); a = f.stack.pop()
        f.stack.append(self._n(a) <= self._n(b))

    def _op_ge(self, f, instr, label_pos):
        b = f.stack.pop(); a = f.stack.pop()
        f.stack.append(self._n(a) >= self._n(b))

    def _op_neq(self, f, instr, label_pos):
        b = f.stack.pop(); a = f.stack.pop()
        f.stack.append(a != b)

    def _op_jump(self, f, instr, label_pos):
        label = instr[1]
        if label in label_pos:
            f.ip = label_pos[label]

    def _op_jump_if_false(self, f, instr, label_pos):
        label = instr[1]
        cond = f.stack.pop() if f.stack else False
        if not cond and label in label_pos:
            f.ip = label_pos[label]

    def _op_jump_if_true(self, f, instr, label_pos):
        label = instr[1]
        cond = f.stack.pop() if f.stack else False
        if cond and label in label_pos:
            f.ip = label_pos[label]

    def _op_call(self, f, instr, label_pos):
        func_name = instr[1]
        arg_count = instr[2]
        args = [f.stack.pop() for _ in range(arg_count)][::-1]

        # Fast path: builtin function
        handler = self._builtins.get(func_name)
        if handler:
            handler(f, args)
            return

        # new_ClassName: constructor call
        if func_name.startswith("new_"):
            class_name = func_name[4:]
            instance = {"__class__": class_name, "__methods__": self.classes.get(class_name, {})}
            methods = self.classes.get(class_name, {})
            init_method = methods.get("init")
            if init_method and "code" in init_method:
                init_frame = CallFrame(init_method["code"], init_method["constants"], init_method.get("labels", {}))
                init_frame.variables["this"] = instance
                init_params = init_method.get("params", [])
                for i, p in enumerate(init_params):
                    init_frame.variables[p] = args[i] if i < len(args) else None
                self.frames.append(init_frame)
                f.ip += 1  # skip the increment in run loop
                return
            f.stack.append(instance)
            return

        # User-defined function in variables
        if func_name in f.variables:
            func_obj = f.variables[func_name]
            if isinstance(func_obj, dict) and "code" in func_obj:
                new_frame = CallFrame(func_obj["code"], func_obj["constants"], func_obj.get("labels", {}))
                for i, p in enumerate(func_obj.get("params", [])):
                    new_frame.variables[p] = args[i] if i < len(args) else None
                self.frames.append(new_frame)
                f.ip += 1  # skip increment
                return

        # Global callable
        if func_name in self.globals:
            self.globals[func_name](*args)
            f.stack.append(None)
            return

        f.stack.append(None)

    # ── Builtin fast paths ──

    def _builtin_print(self, f, args):
        print(*args)
        f.stack.append(None)

    def _builtin_len(self, f, args):
        f.stack.append(len(args[0]) if args and args[0] else 0)

    def _builtin_str(self, f, args):
        f.stack.append(str(args[0]) if args else "")

    def _builtin_int(self, f, args):
        f.stack.append(int(args[0]) if args else 0)

    def _builtin_float(self, f, args):
        f.stack.append(float(args[0]) if args else 0.0)

    def _builtin_range(self, f, args):
        start = int(args[0]) if args else 0
        end = int(args[1]) if len(args) > 1 else 0
        f.stack.append(list(range(start, end + 1)))

    def _builtin_sum(self, f, args):
        f.stack.append(sum(args[0]) if args and isinstance(args[0], list) else 0)

    def _op_call_method(self, f, instr, label_pos):
        method_name = instr[1]
        arg_count = instr[2]
        args = [f.stack.pop() for _ in range(arg_count)][::-1]
        instance = args[0] if args else {}
        method_args = args[1:] if len(args) > 1 else []
        cls_name = instance.get("__class__", "") if isinstance(instance, dict) else ""
        methods = self.classes.get(cls_name, {})
        func_obj = methods.get(method_name)

        if func_obj and "code" in func_obj:
            new_frame = CallFrame(func_obj["code"], func_obj["constants"], func_obj.get("labels", {}))
            new_frame.variables["this"] = instance
            for i, p in enumerate(func_obj.get("params", [])):
                new_frame.variables[p] = method_args[i] if i < len(method_args) else None
            self.frames.append(new_frame)
            f.ip += 1
        else:
            f.stack.append(None)

    def _op_return(self, f, instr, label_pos):
        result = f.stack[-1] if f.stack else None
        if len(self.frames) > 1:
            self.frames.pop()
            self._current().stack.append(result)
            f.ip = len(f.code)  # break inner loop
        else:
            return result

    def _op_make_list(self, f, instr, label_pos):
        count = instr[1]
        items = [f.stack.pop() for _ in range(count)][::-1]
        f.stack.append(items)

    def _op_make_dict(self, f, instr, label_pos):
        count = instr[1]
        d = {}
        for _ in range(count):
            v = f.stack.pop()
            k = f.stack.pop()
            d[k] = v
        f.stack.append(d)

    def _op_index(self, f, instr, label_pos):
        idx = f.stack.pop()
        obj = f.stack.pop()
        try:
            f.stack.append(obj[idx])
        except:
            f.stack.append(None)

    def _op_get_attr(self, f, instr, label_pos):
        attr = instr[1]
        obj = f.stack.pop() if f.stack else {}
        if isinstance(obj, dict):
            f.stack.append(obj.get(attr))
        else:
            f.stack.append(None)

    def _op_set_attr(self, f, instr, label_pos):
        attr = instr[1]
        val = f.stack.pop()
        obj = f.stack.pop()
        if isinstance(obj, dict):
            obj[attr] = val

    def _op_make_func(self, f, instr, label_pos):
        idx = instr[1]
        func_obj = f.constants[idx]
        f.stack.append(func_obj)

    def _op_label(self, f, instr, label_pos):
        pass

    # ── Helpers ──

    def _compute_labels(self, frame):
        pos = {}
        for i, instr in enumerate(frame.code):
            if instr[0] == LABEL:
                pos[instr[1]] = i
        return pos

    def _n(self, v):
        if v is None: return 0
        if isinstance(v, (int, float)): return v
        if isinstance(v, str):
            try: return float(v)
            except: return 0
        return 0