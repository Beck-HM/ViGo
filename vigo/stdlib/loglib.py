"""LogSystem"""
import datetime
from ..runtime.objects import BuiltinFunction


class ViGoLogger:
    LEVELS = {'debug': 0, 'info': 1, 'warn': 2, 'error': 3}

    def __init__(self, name='ViGo', level='info', filepath=None):
        self.name = name
        self.level = level
        self.level_num = self.LEVELS.get(level, 1)
        self.filepath = filepath

    def _log(self, level, msg):
        if self.LEVELS.get(level, 0) < self.level_num:
            return
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{timestamp}] [{level.upper()}] [{self.name}] {msg}"
        print(line)
        if self.filepath:
            try:
                with open(self.filepath, 'a', encoding='utf-8') as f:
                    f.write(line + '\n')
            except:
                pass

    def debug(self, msg): self._log('debug', msg)
    def info(self, msg): self._log('info', msg)
    def warn(self, msg): self._log('warn', msg)
    def error(self, msg): self._log('error', msg)

    def set_level(self, level):
        if level in self.LEVELS:
            self.level = level
            self.level_num = self.LEVELS[level]
        return True

    def __repr__(self):
        return f"📝 <Logger {self.name}>"


def register(env):
    def _create_logger(name='ViGo', level='info', filepath=None):
        return ViGoLogger(name, level, filepath)

    def _log_debug(logger, msg):
        if isinstance(logger, ViGoLogger): logger.debug(str(msg)); return True
        return False

    def _log_info(logger, msg):
        if isinstance(logger, ViGoLogger): logger.info(str(msg)); return True
        return False

    def _log_warn(logger, msg):
        if isinstance(logger, ViGoLogger): logger.warn(str(msg)); return True
        return False

    def _log_error(logger, msg):
        if isinstance(logger, ViGoLogger): logger.error(str(msg)); return True
        return False

    def _log_set_level(logger, level):
        if isinstance(logger, ViGoLogger): return logger.set_level(level)
        return False

    env.define('logger',        BuiltinFunction(_create_logger, 'logger'))
    env.define('log_debug',     BuiltinFunction(_log_debug, 'log_debug'))
    env.define('log_info',      BuiltinFunction(_log_info, 'log_info'))
    env.define('log_warn',      BuiltinFunction(_log_warn, 'log_warn'))
    env.define('log_error',     BuiltinFunction(_log_error, 'log_error'))
    env.define('log_set_level', BuiltinFunction(_log_set_level, 'log_set_level'))