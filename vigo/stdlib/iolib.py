import os
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


def register(env):
    def _read_file(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise ViGoError(f"Failed to read file: {e}")

    def _write_file(path, content, mode='w'):
        try:
            with open(path, mode, encoding='utf-8') as f:
                f.write(str(content))
                return True
        except Exception as e:
            raise ViGoError(f"Failed to write file: {e}")

    env.define('print',       BuiltinFunction(lambda *a: print(*a), 'print'))
    env.define('input',       BuiltinFunction(lambda p='': input(p), 'input'))
    env.define('read_file',   BuiltinFunction(_read_file, 'read_file'))
    env.define('write_file',  BuiltinFunction(_write_file, 'write_file'))
    env.define('append_file', BuiltinFunction(lambda p, c: _write_file(p, c, 'a'), 'append_file'))
    env.define('read_lines',  BuiltinFunction(lambda p: open(p, 'r', encoding='utf-8').readlines(), 'read_lines'))
    env.define('file_exists', BuiltinFunction(lambda p: os.path.exists(p), 'file_exists'))

    # Path operations
    env.define('path_join',   BuiltinFunction(lambda *parts: os.path.join(*parts), 'path_join'))
    env.define('path_dir',    BuiltinFunction(lambda p: os.path.dirname(p), 'path_dir'))
    env.define('path_base',   BuiltinFunction(lambda p: os.path.basename(p), 'path_base'))
    env.define('path_ext',    BuiltinFunction(lambda p: os.path.splitext(p)[1], 'path_ext'))
    env.define('path_stem',   BuiltinFunction(lambda p: os.path.splitext(p)[0], 'path_stem'))
    env.define('path_abs',    BuiltinFunction(lambda p: os.path.abspath(p), 'path_abs'))
    env.define('path_exists', BuiltinFunction(lambda p: os.path.exists(p), 'path_exists'))
    env.define('path_isdir',  BuiltinFunction(lambda p: os.path.isdir(p), 'path_isdir'))
    env.define('path_isfile', BuiltinFunction(lambda p: os.path.isfile(p), 'path_isfile'))