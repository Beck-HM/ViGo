"""ViGo runtime errors and exception classes."""


class ViGoError(Exception):
    """Base ViGo error with optional call stack trace."""
    def __init__(self, message, call_trace=None):
        self.message = message
        self.call_trace = call_trace or []

    def __str__(self):
        if self.call_trace:
            trace = "\n".join(f"  ⚡ {frame}" for frame in self.call_trace)
            return f"ViGo Error: {self.message}\nCall stack:\n{trace}"
        return f"ViGo Error: {self.message}"


class ReturnException(Exception):
    """Signals a function return with a value."""
    def __init__(self, value):
        self.value = value


class BreakException(Exception):
    """Signals a break statement."""


class ContinueException(Exception):
    """Signals a continue statement."""


class AwaitException(Exception):
    """Signals an await with a timeout value."""
    def __init__(self, seconds):
        self.seconds = seconds


class TailCallException(BaseException):
    """Tail-call optimization signal. Carries the function and arguments
    so the trampoline loop in _call can reuse the current frame."""
    def __init__(self, func, args, env, func_name, this_obj=None):
        self.func = func
        self.args = args
        self.env = env
        self.func_name = func_name
        self.this_obj = this_obj