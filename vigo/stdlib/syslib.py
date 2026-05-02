"""SystemOperation: Directory, EnvironmentVariable, Command lineParameter"""
import os
import sys
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


def register(env):
    def _list_dir(path='.'):
        try:
            return os.listdir(path)
        except Exception as e:
            raise ViGoError(f"Failed to list directory: {e}")

    def _mkdir(path):
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            raise ViGoError(f"Failed to create directory: {e}")

    def _rmdir(path):
        try:
            os.rmdir(path)
            return True
        except Exception as e:
            raise ViGoError(f"Failed to delete directory: {e}")

    def _remove_file(path):
        try:
            os.remove(path)
            return True
        except Exception as e:
            raise ViGoError(f"Failed to delete file: {e}")

    def _get_cwd():
        return os.getcwd()

    def _chdir(path):
        try:
            os.chdir(path)
            return True
        except Exception as e:
            raise ViGoError(f"Failed to change directory: {e}")

    def _get_env(name, default=None):
        return os.environ.get(name, default)

    def _set_env(name, value):
        os.environ[name] = str(value)
        return True

    def _all_env():
        return dict(os.environ)

    def _args():
        return sys.argv

    def _exec_cmd(cmd):
        import subprocess
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return {
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'code': result.returncode
            }
        except Exception as e:
            raise ViGoError(f"Failed to execute command: {e}")

    env.define('list_dir',    BuiltinFunction(_list_dir, 'list_dir'))
    env.define('mkdir',       BuiltinFunction(_mkdir, 'mkdir'))
    env.define('rmdir',       BuiltinFunction(_rmdir, 'rmdir'))
    env.define('remove_file', BuiltinFunction(_remove_file, 'remove_file'))
    env.define('get_cwd',     BuiltinFunction(_get_cwd, 'get_cwd'))
    env.define('chdir',       BuiltinFunction(_chdir, 'chdir'))
    env.define('env',         BuiltinFunction(_get_env, 'env'))
    env.define('set_env',     BuiltinFunction(_set_env, 'set_env'))
    env.define('all_env',     BuiltinFunction(_all_env, 'all_env'))
    env.define('args',        BuiltinFunction(_args, 'args'))
    env.define('exec',        BuiltinFunction(_exec_cmd, 'exec'))