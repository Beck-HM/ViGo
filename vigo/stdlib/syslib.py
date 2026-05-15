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
        
    # ── Process management ──

    def _spawn(cmd, wait=False):
        import subprocess
        try:
            if wait:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return {'pid': result.pid, 'stdout': result.stdout.strip(),
                        'stderr': result.stderr.strip(), 'code': result.returncode}
            else:
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True)
                return {'pid': proc.pid, 'running': True}
        except Exception as e:
            raise ViGoError(f"Failed to spawn process: {e}")

    def _kill(pid, signal=9):
        import signal as _signal
        try:
            os.kill(int(pid), int(signal))
            return True
        except Exception as e:
            raise ViGoError(f"Failed to send signal: {e}")

    def _process_list():
        import subprocess
        try:
            if sys.platform == 'win32':
                result = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True)
                lines = result.stdout.strip().split('\n')
                procs = []
                for line in lines:
                    parts = line.strip('"').split('","')
                    if len(parts) >= 2:
                        procs.append({'name': parts[0], 'pid': int(parts[1])})
                return procs
            else:
                result = subprocess.run(['ps', '-eo', 'pid,comm'], capture_output=True, text=True)
                procs = []
                for line in result.stdout.strip().split('\n')[1:]:
                    parts = line.strip().split(None, 1)
                    if len(parts) == 2:
                        procs.append({'pid': int(parts[0]), 'name': parts[1]})
                return procs
        except Exception as e:
            raise ViGoError(f"Failed to list processes: {e}")

    def _pid():
        return os.getpid()

    def _sleep(seconds):
        import time
        time.sleep(float(seconds))
        return True

    # ── System info ──

    def _sys_info():
        return {
            'platform': sys.platform,
            'python_version': sys.version,
            'arch': 'x64' if sys.maxsize > 2**32 else 'x86',
            'cpu_count': os.cpu_count(),
            'pid': os.getpid(),
            'cwd': os.getcwd(),
        }

    def _disk_usage(path='.'):
        import shutil
        try:
            usage = shutil.disk_usage(path)
            return {'total': usage.total, 'used': usage.used, 'free': usage.free}
        except Exception as e:
            raise ViGoError(f"Failed to get disk usage: {e}")

    # ── Registration additions ──

    env.define('spawn',        BuiltinFunction(_spawn, 'spawn'))
    env.define('kill',         BuiltinFunction(_kill, 'kill'))
    env.define('process_list', BuiltinFunction(_process_list, 'process_list'))
    env.define('pid',          BuiltinFunction(_pid, 'pid'))
    env.define('sleep',        BuiltinFunction(_sleep, 'sleep'))
    env.define('sys_info',     BuiltinFunction(_sys_info, 'sys_info'))
    env.define('disk_usage',   BuiltinFunction(_disk_usage, 'disk_usage'))
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