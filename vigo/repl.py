"""ViGo REPL - Interactive read-eval-print loop with multiline support and history"""
import sys
import os
import atexit

from .runtime.interpreter import Interpreter
from .lexer.lexer import Lexer
from .parser.parser import Parser
from .runtime.errors import ViGoError


# Try to enable readline for history (Unix); fallback for Windows
try:
    import readline
    _HAS_READLINE = True
except ImportError:
    try:
        import pyreadline3 as readline
        _HAS_READLINE = True
    except ImportError:
        _HAS_READLINE = False


_HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".vigo_history")


class ViGoREPL:
    def __init__(self):
        self.interpreter = Interpreter(source_file="<repl>")
        self.last_result = None
        self.running = True
        self._setup_history()

    def _setup_history(self):
        if not _HAS_READLINE:
            return
        try:
            if os.path.exists(_HISTORY_FILE):
                readline.read_history_file(_HISTORY_FILE)
        except Exception:
            pass
        atexit.register(self._save_history)

    def _save_history(self):
        if not _HAS_READLINE:
            return
        try:
            readline.write_history_file(_HISTORY_FILE)
        except Exception:
            pass

    @property
    def prompt(self):
        return ">>> "

    @property
    def cont_prompt(self):
        return "... "

    def run(self):
        print(r"""
  __      ___ ___  ___
  \ \    / (_) __|/ _ \
   \ \/\/ /| | (_ | (_) |
    \_/\_/ |_|\___|\___/

  ViGo v3.7 REPL
  Type .exit or .quit to leave, .help for commands
""")
        while self.running:
            try:
                line = self._read_multiline()
                if line is None:
                    break
                self._execute(line)
            except KeyboardInterrupt:
                print("\n(interrupted)")
            except EOFError:
                print("\nGoodbye!")
                break

    def _read_multiline(self):
        """Read input, continuing across lines if ts blocks are unclosed."""
        lines = []
        depth = 0
        first_prompt = self.prompt

        while True:
            try:
                prompt = first_prompt if not lines else self.cont_prompt
                raw = input(prompt)
            except EOFError:
                return None

            line = raw.strip()

            if not lines and line.startswith("."):
                self._handle_command(line)
                return None

            lines.append(raw)

            full = "\n".join(lines)
            depth = self._count_ts_depth(full)

            if depth <= 0:
                return full

    def _count_ts_depth(self, source):
        """Count unclosed ts blocks by tokenizing and tracking ts/Fin."""
        try:
            lexer = Lexer(source)
            depth = 0
            while True:
                tok = lexer.get_next_token()
                from .lexer.tokens import TokenType
                if tok.type == TokenType.EOF:
                    break
                if tok.type == TokenType.TS:
                    depth += 1
                elif tok.type == TokenType.FIN:
                    depth -= 1
            return depth
        except Exception:
            return 0

    def _execute(self, source):
        """Parse and execute the source, storing result in self.last_result."""
        try:
            lexer = Lexer(source)
            parser = Parser(lexer)
            program = parser.parse_program()
            result = self.interpreter.interpret(program)
            if result is not None:
                self.last_result = result
                self.interpreter.global_env.variables["_"] = result
                print(result)
        except ViGoError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Error: {e}")

    def _handle_command(self, line):
        """Handle REPL meta-commands starting with ."""
        cmd = line[1:].strip().lower()
        if cmd in ("exit", "quit"):
            self.running = False
            print("Goodbye!")
        elif cmd == "help":
            print("""ViGo REPL Commands:
  .exit, .quit    Exit the REPL
  .help           Show this help
  .clear          Clear the screen
  _               Reference the last result""")
        elif cmd == "clear":
            os.system("cls" if os.name == "nt" else "clear")
        else:
            print(f"Unknown command: {line}  (type .help for commands)")