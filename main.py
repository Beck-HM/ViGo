#!/usr/bin/env python3
import sys, os
from vigo import Lexer, Parser, Interpreter, ViGoError, BytecodeCompiler, VirtualMachine
from vigo.runtime.errors import ReturnException, AwaitException

LOGO = r'''
╔══════════════════════════════════════╗
║   __      ___ ___  ___               ║
║   \ \    / (_) __|/ _ \              ║
║    \ \/\/ /| | (_ | (_) |            ║
║     \_/\_/ |_|\___|\___/             ║
║                                      ║
║   ViGo v3.7 · Bytecode Launch        ║
╚══════════════════════════════════════╝
'''


class ViGoREPL:
    def __init__(self, use_bytecode=False):
        self.interpreter = Interpreter()
        self.env = self.interpreter.global_env
        self.buffer = ''
        self.in_block = False
        self.use_bytecode = use_bytecode

    def run(self):
        print(LOGO)
        mode = "Bytecode Mode" if self.use_bytecode else "Interpreter Mode"
        print(f"Current: {mode}")
        print(':help Help | :quit Quit')
        print()
        while True:
            try:
                prompt = '⚡ ' if self.in_block else '🎮 '
                line = input(prompt).rstrip()
                if not line:
                    if self.in_block: continue
                    else: print(); continue
                if not self.in_block and line.startswith(':'):
                    self.handle_command(line); continue
                if not self.in_block:
                    self.buffer = line
                    if self.needs_continuation(line): self.in_block = True; continue
                    self.execute(self.buffer)
                else:
                    if line.strip() in ('Fin;', 'Fin'):
                        self.execute(self.buffer + '\n' + line)
                        self.buffer = ''; self.in_block = False
                    else: self.buffer += '\n' + line
            except KeyboardInterrupt:
                print('\n🏃 Bye'); self.buffer = ''; self.in_block = False
            except EOFError: print('\n👋 Goodbye!'); break

    def needs_continuation(self, line):
        s = line.rstrip()
        if s.endswith('ts'): return True
        if s.rstrip(';').rstrip().endswith(':'): return True
        if any(s.strip().startswith(k) for k in ['loop','if','eif','for','class','try','switch','enum','go','skip']):
            if not s.rstrip().endswith(';'): return True
        return False

    def execute(self, code):
        try:
            if not code.strip(): return
            if self.use_bytecode:
                lexer = Lexer(code)
                parser = Parser(lexer)
                ast = parser.parse_program()
                compiler = BytecodeCompiler()
                bc = compiler.compile(ast)
                vm = VirtualMachine()
                vm.load(bc)
                result = vm.run()
                if result is not None: print(f'✨ {self.format_value(result)}')
            else:
                ast = Parser(Lexer(code)).parse_program()
                for stmt in ast.statements:
                    try:
                        result = self.interpreter.eval(stmt, self.env)
                        if result is not None: print(f'✨ {self.format_value(result)}')
                    except ReturnException as r: print(f'✨ {self.format_value(r.value)}')
                    except AwaitException as a: print(f'⏳ Waiting {a.seconds}s')
        except ViGoError as e: print(f'💥 {e}')
        except Exception as e: print(f'💥 {e}')

    def format_value(self, v):
        if v is None: return 'null'
        if isinstance(v, bool): return '✓ ok' if v else '✗ no'
        if isinstance(v, str): return f'"{v}"'
        if isinstance(v, float): return str(int(v)) if v == int(v) else str(v)
        if isinstance(v, list): return '[' + ', '.join(self.format_value(x) for x in v) + ']'
        if isinstance(v, set): return 'Set{' + ', '.join(self.format_value(x) for x in v) + '}'
        if isinstance(v, dict):
            items = ', '.join(f'{k}: {self.format_value(v)}' for k, v in v.items())
            return '{' + items + '}'
        return str(v)

    def handle_command(self, cmd):
        c = cmd[1:].strip().lower()
        if c in ('q', 'quit', 'exit'): print('👋 Goodbye!'); sys.exit(0)
        elif c in ('h', 'help'): print('ViGo v3.5 · Bytecode Mode · :help :quit :vars :clear :about :run')
        elif c == 'vars':
            for n, v in self.env.variables.items(): print(f'  {n}: {self.format_value(v)}')
        elif c == 'clear': self.interpreter.reset(); self.env = self.interpreter.global_env; print('✨')
        elif c.startswith('run '):
            fn = c[4:].strip().strip('"')
            try:
                with open(fn, 'r', encoding='utf-8') as f: self.execute(f.read())
            except FileNotFoundError: print(f'💥 File not found: {fn}')
        elif c == 'about': print('ViGo v3.5 · Bytecode + Class Inheritance + Pipe')
        else: print(f'🤔 Unknown command: {c}')


def _read_file_safe(filepath):
    with open(filepath, 'rb') as f:
        raw = f.read()
    if raw[:3] == b'\xef\xbb\xbf': raw = raw[3:]
    try: return raw.decode('utf-8')
    except: pass
    try: return raw.decode('gbk')
    except: pass
    return raw.decode('latin-1')


def run_file(filepath, use_bytecode=False):
    source = _read_file_safe(filepath)
    if use_bytecode:
        lexer = Lexer(source)
        parser = Parser(lexer)
        ast = parser.parse_program()
        compiler = BytecodeCompiler()
        bc = compiler.compile(ast)
        vm = VirtualMachine()
        vm.load(bc)
        return vm.run()
    else:
        interp = Interpreter(source_file=filepath)
        ast = Parser(Lexer(source)).parse_program()
        return interp.interpret(ast)


def main():
    from vigo.cli import main as cli_main
    cli_main()


if __name__ == '__main__':
    main()