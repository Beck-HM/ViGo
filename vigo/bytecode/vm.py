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

                if op == HALT:
                    if len(self.frames) == 1:
                        return f.stack[-1] if f.stack else None
                    else:
                        result = f.stack[-1] if f.stack else None
                        self.frames.pop()
                        self._current().stack.append(result)
                        break

                elif op == PUSH:
                    f.stack.append(f.constants[instr[1]])

                elif op == POP:
                    if f.stack: f.stack.pop()

                elif op == LOAD:
                    name = instr[1]
                    val = f.variables.get(name)
                    if val is None and len(self.frames) > 0:
                        val = self.frames[0].variables.get(name)
                    if val is None:
                        val = self.globals.get(name)
                    f.stack.append(val)

                elif op == STORE:
                    name = instr[1]
                    if f.stack:
                        f.variables[name] = f.stack.pop()

                elif op == STORE_METHOD:
                    class_name, method_name, const_idx = instr[1], instr[2], instr[3]
                    func_obj = f.constants[const_idx]
                    if class_name not in self.classes:
                        self.classes[class_name] = {}
                    self.classes[class_name][method_name] = func_obj

                elif op == ADD:
                    b = f.stack.pop() if f.stack else 0
                    a = f.stack.pop() if f.stack else 0
                    if isinstance(a, str) or isinstance(b, str):
                        f.stack.append(str(a) + str(b))
                    elif isinstance(a, list) and isinstance(b, list):
                        f.stack.append(a + b)
                    else:
                        f.stack.append(self._n(a) + self._n(b))

                elif op == SUB:
                    b = f.stack.pop() if f.stack else 0
                    a = f.stack.pop() if f.stack else 0
                    f.stack.append(self._n(a) - self._n(b))

                elif op == MUL:
                    b = f.stack.pop() if f.stack else 1
                    a = f.stack.pop() if f.stack else 1
                    if isinstance(a, str) and isinstance(b, int):
                        f.stack.append(a * b)
                    elif isinstance(a, list) and isinstance(b, int):
                        f.stack.append(a * b)
                    else:
                        f.stack.append(self._n(a) * self._n(b))

                elif op == DIV:
                    b = f.stack.pop() if f.stack else 1
                    a = f.stack.pop() if f.stack else 0
                    denom = self._n(b)
                    f.stack.append(self._n(a) / denom if denom != 0 else 0)

                elif op == MOD:
                    b = f.stack.pop() if f.stack else 1
                    a = f.stack.pop() if f.stack else 0
                    denom = self._n(b)
                    f.stack.append(self._n(a) % denom if denom != 0 else 0)

                elif op == NEG:
                    a = f.stack.pop() if f.stack else 0
                    f.stack.append(-self._n(a))

                elif op == NOT_OP:
                    a = f.stack.pop() if f.stack else None
                    f.stack.append(not a)

                elif op == AND:
                    b = f.stack.pop() if f.stack else False
                    a = f.stack.pop() if f.stack else False
                    f.stack.append(a and b)

                elif op == EQ:
                    b = f.stack.pop(); a = f.stack.pop()
                    f.stack.append(a == b)

                elif op == LT:
                    b = f.stack.pop(); a = f.stack.pop()
                    f.stack.append(self._n(a) < self._n(b))

                elif op == GT:
                    b = f.stack.pop(); a = f.stack.pop()
                    f.stack.append(self._n(a) > self._n(b))

                elif op == LE:
                    b = f.stack.pop(); a = f.stack.pop()
                    f.stack.append(self._n(a) <= self._n(b))

                elif op == GE:
                    b = f.stack.pop(); a = f.stack.pop()
                    f.stack.append(self._n(a) >= self._n(b))

                elif op == NEQ:
                    b = f.stack.pop(); a = f.stack.pop()
                    f.stack.append(a != b)

                elif op == JUMP:
                    label = instr[1]
                    if label in label_pos:
                        f.ip = label_pos[label]
                        continue

                elif op == JUMP_IF_FALSE:
                    label = instr[1]
                    cond = f.stack.pop() if f.stack else False
                    if not cond and label in label_pos:
                        f.ip = label_pos[label]
                        continue

                elif op == JUMP_IF_TRUE:
                    label = instr[1]
                    cond = f.stack.pop() if f.stack else False
                    if cond and label in label_pos:
                        f.ip = label_pos[label]
                        continue

                elif op == CALL:
                    func_name = instr[1]
                    arg_count = instr[2]
                    args = [f.stack.pop() for _ in range(arg_count)][::-1]

                    if func_name == "print":
                        print(*args)
                        f.stack.append(None)
                    elif func_name == "len":
                        f.stack.append(len(args[0]) if args and args[0] else 0)
                    elif func_name == "str":
                        f.stack.append(str(args[0]) if args else "")
                    elif func_name == "int":
                        f.stack.append(int(args[0]) if args else 0)
                    elif func_name == "float":
                        f.stack.append(float(args[0]) if args else 0.0)
                    elif func_name == "range":
                        start = int(args[0]) if args else 0
                        end = int(args[1]) if len(args) > 1 else 0
                        f.stack.append(list(range(start, end + 1)))
                    elif func_name == "sum":
                        f.stack.append(sum(args[0]) if args and isinstance(args[0], list) else 0)
                    elif func_name.startswith("new_"):
                        class_name = func_name[4:]
                        instance = {"__class__": class_name, "__methods__": self.classes.get(class_name, {})}
                        f.stack.append(instance)
                    elif func_name in f.variables:
                        func_obj = f.variables[func_name]
                        if isinstance(func_obj, dict) and "code" in func_obj:
                            new_frame = CallFrame(func_obj["code"], func_obj["constants"], func_obj.get("labels", {}))
                            for i, p in enumerate(func_obj.get("params", [])):
                                new_frame.variables[p] = args[i] if i < len(args) else None
                            self.frames.append(new_frame)
                            break
                        else:
                            f.stack.append(None)
                    elif func_name in self.globals:
                        self.globals[func_name](*args)
                        f.stack.append(None)
                    else:
                        f.stack.append(None)

                elif op == CALL_METHOD:
                    method_name = instr[1]
                    arg_count = instr[2]
                    args = [f.stack.pop() for _ in range(arg_count)][::-1]

                    instance = args[0] if args else {}
                    cls_name = instance.get("__class__", "")
                    methods = self.classes.get(cls_name, {})
                    func_obj = methods.get(method_name)

                    if func_obj and "code" in func_obj:
                        new_frame = CallFrame(func_obj["code"], func_obj["constants"], func_obj.get("labels", {}))
                        new_frame.variables["this"] = instance
                        for i, p in enumerate(func_obj.get("params", [])):
                            new_frame.variables[p] = args[i + 1] if i + 1 < len(args) else None
                        self.frames.append(new_frame)
                        break
                    else:
                        f.stack.append(None)

                elif op == RETURN:
                    result = f.stack[-1] if f.stack else None
                    if len(self.frames) > 1:
                        self.frames.pop()
                        self._current().stack.append(result)
                        break
                    else:
                        return result

                elif op == MAKE_LIST:
                    count = instr[1]
                    items = [f.stack.pop() for _ in range(count)][::-1]
                    f.stack.append(items)

                elif op == MAKE_DICT:
                    count = instr[1]
                    d = {}
                    for _ in range(count):
                        v = f.stack.pop()
                        k = f.stack.pop()
                        d[k] = v
                    f.stack.append(d)

                elif op == INDEX:
                    idx = f.stack.pop()
                    obj = f.stack.pop()
                    try:
                        f.stack.append(obj[idx])
                    except:
                        f.stack.append(None)

                elif op == GET_ATTR:
                    attr = instr[1]
                    obj = f.stack.pop() if f.stack else {}
                    if isinstance(obj, dict):
                        f.stack.append(obj.get(attr))
                    else:
                        f.stack.append(None)

                elif op == SET_ATTR:
                    attr = instr[1]
                    val = f.stack.pop()
                    obj = f.stack.pop()
                    if isinstance(obj, dict):
                        obj[attr] = val

                elif op == MAKE_FUNC:
                    idx = instr[1]
                    func_obj = f.constants[idx]
                    f.stack.append(func_obj)

                elif op == LABEL:
                    pass

                f.ip += 1

        return None

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