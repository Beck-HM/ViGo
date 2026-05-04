"""ViGo → Python Transpiler"""
from ..parser.ast_nodes import *


class PythonTranspiler:
    BUILTIN_RENAME = {
        'time': 'time.time',
        'now': 'datetime.datetime.now().isoformat',
        'date': 'datetime.date.today().isoformat',
        'uuid': 'uuid.uuid4().hex',
        'random': 'random.randint',
        'sqrt': 'math.sqrt',
        'abs': 'abs',
        'min': 'min',
        'max': 'max',
        'floor': 'math.floor',
        'ceil': 'math.ceil',
        'round': 'round',
        'pow': 'pow',
        'sin': 'math.sin',
        'cos': 'math.cos',
        'tan': 'math.tan',
        'log': 'math.log',
        'len': 'len',
        'str': 'str',
        'int': 'int',
        'float': 'float',
        'bool': 'bool',
        'type': 'type',
        'print': 'print',
        'push': '.append',
        'pop': '.pop',
        'upper': '.upper',
        'lower': '.lower',
        'trim': '.strip',
        'split': '.split',
        'join': '.join',
        'replace': '.replace',
        'sort': 'sorted',
        'keys': '.keys',
        'values': '.values',
        'reverse': '.reverse',
        'md5': '_md5',
        'sha256': '_sha256',
        'sha512': '_sha512',
        'base64_encode': 'base64.b64encode',
        'base64_decode': 'base64.b64decode',
        'to_json': 'json.dumps',
        'parse_json': 'json.loads',
        'read_file': 'open',
        'file_exists': 'os.path.exists',
        'ai_ask': '_ai_ask_wrapper',
        'ai_chat': '_ai_chat_wrapper',
        'ai_ollama': '_ai_ollama_wrapper',
        'ai_chain': '_ai_chain_wrapper',
        'ai_set_key': '_ai_set_key_wrapper',
        'ai_set_base_url': '_ai_set_base_url_wrapper',
        'ai_agent': '_ai_agent_wrapper',
        'ai_agent_add_tool': '_ai_agent_add_tool_wrapper',
        'ai_agent_run': '_ai_agent_run_wrapper',
    }

    def __init__(self):
        self.indent = 0

    def _emit(self, line):
        return "    " * self.indent + line

    def transpile(self, program):
        lines = []
        for stmt in program.statements:
            lines.append(self._transpile_statement(stmt))
        return "\n".join(lines)

    def _transpile_statement(self, node):
        if isinstance(node, VarDecl):
            return self._emit(f"{node.name} = {self._transpile_expr(node.value)}")
        elif isinstance(node, AssignStmt):
            target = self._transpile_expr(node.target)
            return self._emit(f"{target} {node.op} {self._transpile_expr(node.value)}")
        elif isinstance(node, FuncDef):
            return self._transpile_function(node)
        elif isinstance(node, ReturnStmt):
            return self._emit(f"return {self._transpile_expr(node.value)}")
        elif isinstance(node, IfStmt):
            return self._transpile_if(node)
        elif isinstance(node, LoopStmt):
            return self._transpile_loop(node)
        elif isinstance(node, ForInStmt):
            return self._transpile_for_in(node)
        elif isinstance(node, ClassDef):
            return self._transpile_class(node)
        elif isinstance(node, SwitchStmt):
            return self._transpile_switch(node)
        elif isinstance(node, TryStmt):
            return self._transpile_try(node)
        elif isinstance(node, ThrowStmt):
            return self._emit(f"raise Exception({self._transpile_expr(node.value)})")
        elif isinstance(node, BreakStmt):
            return self._emit("break")
        elif isinstance(node, ContinueStmt):
            return self._emit("continue")
        elif isinstance(node, SureStmt):
            cond = self._transpile_expr(node.condition)
            return self._emit(f"assert {cond}")
        elif isinstance(node, FuncCall):
            return self._emit(self._transpile_expr(node))
        elif isinstance(node, SkipStmt):
            cond = self._transpile_expr(node.condition)
            code = []
            code.append(self._emit(f"if not ({cond}):"))
            self.indent += 1
            for s in node.body:
                code.append(self._transpile_statement(s))
            self.indent -= 1
            return "\n".join(code)
        elif isinstance(node, DoWhileStmt):
            code = []
            code.append(self._emit("while True:"))
            self.indent += 1
            for s in node.body:
                code.append(self._transpile_statement(s))
            code.append(self._emit(f"if not ({self._transpile_expr(node.condition)}): break"))
            self.indent -= 1
            return "\n".join(code)
        else:
            return self._emit(f"# unsupported: {type(node).__name__}")

    def _transpile_expr(self, node):
        if node is None:
            return "None"
        if isinstance(node, Literal):
            if node.value is None:
                return "None"
            if node.value is True:
                return "True"
            if node.value is False:
                return "False"
            if isinstance(node.value, str):
                return repr(node.value)
            return str(node.value)
        elif isinstance(node, Variable):
            return str(node.name)
        elif isinstance(node, BinaryOp):
            left = self._transpile_expr(node.left)
            right = self._transpile_expr(node.right)
            return f"({left} {node.op} {right})"
        elif isinstance(node, UnaryOp):
            op = node.op
            if op == '!': op = 'not '
            elif op == 'not': op = 'not '
            return f"({op}{self._transpile_expr(node.operand)})"
        elif isinstance(node, FuncCall):
            return self._transpile_call(node)
        elif isinstance(node, DotAccess):
            obj = self._transpile_expr(node.object)
            return f"{obj}.{node.attr}"
        elif isinstance(node, IndexAccess):
            obj = self._transpile_expr(node.object)
            idx = self._transpile_expr(node.index)
            return f"{obj}[{idx}]"
        elif isinstance(node, ListLiteral):
            items = ", ".join(self._transpile_expr(e) for e in node.elements)
            return f"[{items}]"
        elif isinstance(node, DictLiteral):
            items = ", ".join(f"{repr(k)}: {self._transpile_expr(v)}" for k, v in node.pairs.items())
            return f"{{{items}}}"
        elif isinstance(node, SetLiteral):
            items = ", ".join(self._transpile_expr(e) for e in node.elements)
            return f"{{{items}}}"
        elif isinstance(node, TernaryExpr):
            cond = self._transpile_expr(node.condition)
            t = self._transpile_expr(node.then_expr)
            e = self._transpile_expr(node.else_expr)
            return f"({t} if {cond} else {e})"
        elif isinstance(node, PipeExpr):
            return self._transpile_pipe(node)
        elif isinstance(node, RangeExpr):
            start = self._transpile_expr(node.start)
            end = self._transpile_expr(node.end)
            return f"range({start}, {int(end)}+1)"
        elif isinstance(node, NullCoalesce):
            left = self._transpile_expr(node.left)
            right = self._transpile_expr(node.right)
            return f"({left} if {left} is not None else {right})"
        elif isinstance(node, OptionalChain):
            obj = self._transpile_expr(node.object)
            chain = self._transpile_expr(node.chain)
            return f"({obj}.{chain} if {obj} is not None else None)"
        elif isinstance(node, ListCompExpr):
            expr = self._transpile_expr(node.expr)
            var = node.var
            it = self._transpile_expr(node.iterable)
            if node.condition:
                cond = self._transpile_expr(node.condition)
                return f"[{expr} for {var} in {it} if {cond}]"
            return f"[{expr} for {var} in {it}]"
        elif isinstance(node, InterpolatedString):
            parts = []
            for p in node.parts:
                if isinstance(p, tuple):
                    parts.append("{" + self._transpile_expr(p[0]) + "}")
                else:
                    parts.append(str(p.value) if hasattr(p, 'value') else str(p))
            return "f\"" + "".join(parts) + "\""
        elif isinstance(node, LogicalOp):
            left = self._transpile_expr(node.left)
            right = self._transpile_expr(node.right)
            return f"({left} {node.op} {right})"
        elif isinstance(node, ChainedCompare):
            parts = []
            for i, op in enumerate(node.ops):
                if i == 0:
                    parts.append(self._transpile_expr(node.operands[i]))
                parts.append(op)
                parts.append(self._transpile_expr(node.operands[i + 1]))
            return "(" + " ".join(parts) + ")"
        elif isinstance(node, InExpr):
            left = self._transpile_expr(node.left)
            right = self._transpile_expr(node.right)
            if node.negated:
                return f"({left} not in {right})"
            return f"({left} in {right})"
        elif isinstance(node, ExpandExpr):
            return f"*{self._transpile_expr(node.expr)}"
        elif isinstance(node, NewExpr):
            args = ", ".join(self._transpile_expr(a) for a in node.args)
            return f"{node.class_name}({args})"
        elif isinstance(node, ThisExpr):
            return "self"
        elif isinstance(node, LambdaExpr):
            return self._transpile_lambda(node)
        elif isinstance(node, AwaitExpr):
            return f"await {self._transpile_expr(node.value)}"
        else:
            return f"None  # unsupported expr: {type(node).__name__}"

    def _transpile_call(self, node):
        if isinstance(node.name, Variable):
            name = node.name.name
            if name == 'sum' and len(node.args) == 1:
                return f"sum(list({self._transpile_expr(node.args[0])}))"
            if name in self.BUILTIN_RENAME:
                name = self.BUILTIN_RENAME[name]
        elif isinstance(node.name, DotAccess):
            obj = self._transpile_expr(node.name.object)
            name = f"{obj}.{node.name.attr}"
        else:
            name = self._transpile_expr(node.name)
        args = ", ".join(self._transpile_expr(a) for a in node.args)
        return f"{name}({args})"

    def _transpile_pipe(self, node):
        if isinstance(node.right, PipeExpr):
            inner = self._transpile_pipe(PipeExpr(node.left, node.right.left))
            outer = self._transpile_expr(node.right.right)
            return f"{outer}({inner})"
        elif isinstance(node.right, Variable) and node.right.name == 'sum':
            left = self._transpile_expr(node.left)
            return f"sum(list({left}))"
        else:
            left = self._transpile_expr(node.left)
            if isinstance(node.right, FuncCall):
                call = node.right
                fn_name_raw = call.name.name if isinstance(call.name, Variable) else self._transpile_expr(call.name)
                fn_args = [self._transpile_expr(a) for a in call.args]
                args = fn_args + [left]
                if fn_name_raw == 'sum':
                    return f"sum(list({', '.join(args)}))"
                return f"{fn_name_raw}({', '.join(args)})"
            else:
                right = self._transpile_expr(node.right)
                return f"{right}({left})"

    def _transpile_if(self, node):
        code = []
        code.append(self._emit(f"if {self._transpile_expr(node.condition)}:"))
        self.indent += 1
        for s in node.then_body:
            code.append(self._transpile_statement(s))
        self.indent -= 1
        for cond, body in node.else_body:
            if cond is None:
                code.append(self._emit("else:"))
            else:
                code.append(self._emit(f"elif {self._transpile_expr(cond)}:"))
            self.indent += 1
            for s in body:
                code.append(self._transpile_statement(s))
            self.indent -= 1
        return "\n".join(code)

    def _transpile_loop(self, node):
        code = []
        code.append(self._emit(f"while {self._transpile_expr(node.condition)}:"))
        self.indent += 1
        for s in node.body:
            code.append(self._transpile_statement(s))
        self.indent -= 1
        return "\n".join(code)

    def _transpile_for_in(self, node):
        code = []
        var = node.var_name
        it = self._transpile_expr(node.iterable)
        code.append(self._emit(f"for {var} in {it}:"))
        self.indent += 1
        for s in node.body:
            code.append(self._transpile_statement(s))
        self.indent -= 1
        return "\n".join(code)

    def _transpile_function(self, node):
        params = list(node.params)
        if node.rest_param:
            params.append(f"*{node.rest_param}")
        for p, d in node.defaults.items():
            idx = params.index(p)
            params[idx] = f"{p}={self._transpile_expr(d)}"
        code = []
        code.append(self._emit(f"def {node.name}({', '.join(params)}):"))
        self.indent += 1
        for s in node.body:
            code.append(self._transpile_statement(s))
        self.indent -= 1
        return "\n".join(code)

    def _transpile_method(self, node):
        params = ["self"] + list(node.params)
        if node.rest_param:
            params.append(f"*{node.rest_param}")
        code = []
        code.append(self._emit(f"def {node.name}({', '.join(params)}):"))
        self.indent += 1
        for s in node.body:
            code.append(self._transpile_statement(s))
        self.indent -= 1
        return "\n".join(code)

    def _transpile_static_method(self, node):
        params = list(node.func_def.params)
        code = []
        code.append(self._emit("@staticmethod"))
        code.append(self._emit(f"def {node.func_def.name}({', '.join(params)}):"))
        self.indent += 1
        for s in node.func_def.body:
            code.append(self._transpile_statement(s))
        self.indent -= 1
        return "\n".join(code)

    def _transpile_lambda(self, node):
        params = ", ".join(node.params)
        body = self._transpile_expr(node.body[0]) if node.body else "None"
        return f"(lambda {params}: {body})"

    def _transpile_class(self, node):
        parent = node.parent if node.parent else "object"
        code = []
        code.append(self._emit(f"class {node.name}({parent}):"))
        self.indent += 1
        for s in node.body:
            if isinstance(s, FuncDef):
                code.append(self._transpile_method(s))
            elif isinstance(s, StaticMethodDef):
                code.append(self._transpile_static_method(s))
            else:
                code.append(self._transpile_statement(s))
        self.indent -= 1
        return "\n".join(code)

    def _transpile_switch(self, node):
        code = []
        expr = self._transpile_expr(node.expr)
        first = True
        for case_val, body in node.cases:
            if isinstance(case_val, tuple) and case_val[0] == 'range':
                cond = f"{case_val[1]} <= {expr} <= {case_val[2]}"
            else:
                cond = f"{expr} == {repr(case_val)}"
            if first:
                code.append(self._emit(f"if {cond}:"))
                first = False
            else:
                code.append(self._emit(f"elif {cond}:"))
            self.indent += 1
            for s in body:
                code.append(self._transpile_statement(s))
            self.indent -= 1
        if node.default_body:
            code.append(self._emit("else:"))
            self.indent += 1
            for s in node.default_body:
                code.append(self._transpile_statement(s))
            self.indent -= 1
        return "\n".join(code)

    def _transpile_try(self, node):
        code = []
        code.append(self._emit("try:"))
        self.indent += 1
        for s in node.try_body:
            code.append(self._transpile_statement(s))
        self.indent -= 1
        if node.catch_body:
            var = node.catch_var if node.catch_var else "e"
            code.append(self._emit(f"except Exception as {var}:"))
            self.indent += 1
            for s in node.catch_body:
                code.append(self._transpile_statement(s))
            self.indent -= 1
        return "\n".join(code)


def transpile(source_code):
    from ..lexer.lexer import Lexer
    from ..parser.parser import Parser

    lexer = Lexer(source_code)
    parser = Parser(lexer)
    ast = parser.parse_program()
    trans = PythonTranspiler()
    py_code = trans.transpile(ast)

    imports = "import math, random, time, datetime, uuid, hashlib, base64, json, os\n"
    helpers = """
def _md5(s): return hashlib.md5(s.encode()).hexdigest()
def _sha256(s): return hashlib.sha256(s.encode()).hexdigest()
def _sha512(s): return hashlib.sha512(s.encode()).hexdigest()
"""
    ai_helpers = """
import urllib.request, urllib.error, json as _json
_ai_api_key = None
_ai_base_url = None

def _ai_set_key_wrapper(key):
    global _ai_api_key
    _ai_api_key = key
    return True

def _ai_set_base_url_wrapper(url):
    global _ai_base_url
    _ai_base_url = url
    return True

def _ai_ollama_wrapper(prompt, model="llama3", host="http://localhost:11434"):
    url = host + "/api/generate"
    data = _json.dumps({"model": model, "prompt": str(prompt), "stream": False}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        return _json.loads(resp.read().decode()).get("response", "")

def _ai_chain_wrapper(steps, default_model="gemma-4b"):
    result = ""
    for step in steps:
        prompt_template = step[0]
        model = step[1] if len(step) > 1 else default_model
        prompt = prompt_template.replace("__OUTPUT__", result)
        result = _ai_ollama_wrapper(prompt, model)
    return result

def _ai_ask_wrapper(prompt, model=None, temp=None, max_tokens=None):
    return _ai_ollama_wrapper(prompt, model or "gemma-4b")

def _ai_chat_wrapper(messages, model=None, temp=None, max_tokens=None):
    prompt = "\\n".join(str(m[1]) for m in messages if isinstance(m, list) and len(m) >= 2)
    return _ai_ollama_wrapper(prompt, model or "gemma-4b")

class _AIAgent:
    def __init__(self, model="gemma-4b", max_steps=5, verbose=False):
        self.model = model
        self.max_steps = max_steps
        self.verbose = verbose
        self.tools = {}
        self.memory = []
        self.long_term_memory = []
        self.retry_count = 2

    def add_tool(self, name, func, desc):
        self.tools[name] = {"func": func, "desc": desc}

    def run(self, task):
        self.memory = []
        system_prompt = "You are a helpful AI assistant with access to tools.\\nAvailable tools:\\n"
        for name, info in self.tools.items():
            system_prompt += f"- {name}: {info['desc']}\\n"
        system_prompt += "\\nThink step by step. To use a tool, write:\\nTOOL: tool_name\\nINPUT: your input\\n\\nWhen you have the final answer, write:\\nFINAL: your final answer\\n"
        current_prompt = f"{system_prompt}\\n\\nTask: {task}"
        for step in range(self.max_steps):
            response = _ai_ollama_wrapper(current_prompt, self.model)
            self.memory.append({"step": step + 1, "response": response})
            if "TOOL:" in response:
                tool_name = response.split("TOOL:")[1].split("\\n")[0].strip()
                if "INPUT:" in response:
                    tool_input = response.split("INPUT:")[1].split("\\n")[0].strip()
                else:
                    tool_input = ""
                if tool_name in self.tools:
                    try:
                        tool_result = self.tools[tool_name]["func"](tool_input)
                    except:
                        tool_result = "Error executing tool"
                    current_prompt = f"{current_prompt}\\n\\nAssistant: {response}\\n\\nTool result: {tool_result}\\n\\nContinue."
                    continue
            if "FINAL:" in response:
                return response.split("FINAL:")[1].strip()
            current_prompt = f"{current_prompt}\\n\\nAssistant: {response}\\n\\nContinue or provide FINAL answer."
        return "Agent max steps reached."

def _ai_agent_wrapper(model="gemma-4b", max_steps=5, verbose=False):
    return _AIAgent(model, max_steps, verbose)

def _ai_agent_add_tool_wrapper(agent, name, func, desc):
    agent.add_tool(name, func, desc)
    return agent

def _ai_agent_run_wrapper(agent, task):
    return agent.run(task)
"""
    return imports + helpers + ai_helpers + py_code


def transpile_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except UnicodeDecodeError:
        with open(filepath, "r", encoding="gbk") as f:
            source = f.read()
    return transpile(source)

def transpile_ir(source_code):
    """Transpile via IR: AST → IR → optimized IR → Python source."""
    from ..lexer.lexer import Lexer
    from ..parser.parser import Parser
    from ..ir import IRBuilder, IROptimizer

    lexer = Lexer(source_code)
    parser = Parser(lexer)
    ast = parser.parse_program()
    builder = IRBuilder()
    ir = builder.build(ast)
    optimizer = IROptimizer()
    ir = optimizer.optimize(ir)

    return _ir_to_python(ir)


def _ir_to_python(instructions):
    """Convert optimized IR back to Python source code."""
    lines = []
    temps = {}

    for inst in instructions:
        if inst.opcode == IR_LOAD_CONST:
            val = inst.operands[0] if inst.operands else None
            if inst.result and inst.result.startswith('t'):
                temps[inst.result] = repr(val) if isinstance(val, str) else str(val)
            else:
                lines.append(f"{inst.result} = {repr(val)}")

        elif inst.opcode in (IR_ADD, IR_SUB, IR_MUL, IR_DIV):
            left = temps.get(inst.operands[0], inst.operands[0])
            right = temps.get(inst.operands[1], inst.operands[1])
            op_map = {IR_ADD: '+', IR_SUB: '-', IR_MUL: '*', IR_DIV: '/'}
            op = op_map.get(inst.opcode, '+')
            expr = f"{left} {op} {right}"
            if inst.result and inst.result.startswith('t'):
                temps[inst.result] = f"({expr})"
            else:
                lines.append(f"{inst.result} = {expr}")

        elif inst.opcode == IR_STORE:
            var = inst.operands[0]
            val = temps.get(inst.operands[1], inst.operands[1])
            lines.append(f"{var} = {val}")

    return "\n".join(lines)