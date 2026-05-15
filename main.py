#!/usr/bin/env python3
"""ViGo main entry point."""
import sys
import os
from vigo import Lexer, Parser, Interpreter, ViGoError, BytecodeCompiler, VirtualMachine


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


def _read_file_safe(filepath):
    """Read a file with automatic encoding detection (UTF-8 BOM, UTF-8, GBK fallback)."""
    with open(filepath, 'rb') as f:
        raw = f.read()
    if raw[:3] == b'\xef\xbb\xbf':
        raw = raw[3:]
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        pass
    try:
        return raw.decode('gbk')
    except UnicodeDecodeError:
        pass
    return raw.decode('latin-1')


def run_file(filepath, use_bytecode=False):
    """Execute a ViGo source file. Returns the result value."""
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
    """Entry point: delegates to the CLI module."""
    from vigo.cli import main as cli_main
    cli_main()


if __name__ == '__main__':
    main()