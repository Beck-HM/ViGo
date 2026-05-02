"""ViGo Enhanced Module System"""
import os
import sys
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


class ModuleLoader:
    def __init__(self):
        self.search_paths = [
            ".",
            "./lib",
            "./modules",
            os.path.join(os.path.dirname(__file__), "..", "stdlib"),
        ]
        self.loaded_modules = {}
        self.loaded_files = set()

    def add_search_path(self, path):
        if path not in self.search_paths:
            self.search_paths.append(path)
        return True

    def get_search_paths(self):
        return self.search_paths

    def load(self, module_name, env, alias=None):
        from ..runtime.interpreter import Interpreter
        from ..lexer.lexer import Lexer
        from ..parser.parser import Parser
        from ..runtime.environment import Environment
        # ... rest of the method ...

        # Search for the file
        filepath = None
        for sp in self.search_paths:
            candidates = [
                os.path.join(sp, f"{module_name}.vigo"),
                os.path.join(sp, module_name),
                os.path.join(sp, f"{module_name}.vig"),
            ]
            for c in candidates:
                if os.path.exists(c):
                    filepath = c
                    break
            if filepath:
                break

        if not filepath:
            raise ViGoError(f"Module not found: {module_name}. Search paths: {self.search_paths}")

        # Cycle detection
        abs_path = os.path.abspath(filepath)
        if abs_path in self.loaded_files:
            return {}
        self.loaded_files.add(abs_path)

        # Load and execute
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
        except UnicodeDecodeError:
            with open(filepath, "r", encoding="gbk") as f:
                source = f.read()

        sub_interp = Interpreter(source_file=filepath)
        sub_interp.global_env = Environment(env)  # Share parent env for access to builtins
        # Register module loader into sub-interpreter
        sub_interp.global_env.define('module_add_path', BuiltinFunction(
            lambda p: _loader.add_search_path(p), 'module_add_path'))
        sub_interp.global_env.define('module_import', BuiltinFunction(
            lambda n, a=None: _loader.load(n, sub_interp.global_env, a), 'module_import'))

        ast = Parser(Lexer(source)).parse_program()
        result = sub_interp.interpret(ast)

        # Export module's public symbols
        module_exports = {}
        for k, v in sub_interp.global_env.variables.items():
            if not k.startswith('_'):
                module_exports[k] = v

        if alias:
            env.define(alias, module_exports)
        else:
            for k, v in module_exports.items():
                env.define(k, v)

        self.loaded_modules[module_name] = module_exports
        return module_exports

    def list_loaded(self):
        return list(self.loaded_modules.keys())

    def reload(self, module_name, env):
        if module_name in self.loaded_modules:
            del self.loaded_modules[module_name]
        return self.load(module_name, env)


_loader = ModuleLoader()


def register(env):
    env.define('module_add_path', BuiltinFunction(
        lambda p: _loader.add_search_path(p), 'module_add_path'))
    env.define('module_paths', BuiltinFunction(
        lambda: _loader.get_search_paths(), 'module_paths'))
    env.define('module_import', BuiltinFunction(
        lambda n, a=None: _loader.load(n, env, a), 'module_import'))
    env.define('module_list', BuiltinFunction(
        lambda: _loader.list_loaded(), 'module_list'))
    env.define('module_reload', BuiltinFunction(
        lambda n: _loader.reload(n, env), 'module_reload'))