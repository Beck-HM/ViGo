class ViGoError(Exception):
    def __init__(self, msg, trace=None):
        super().__init__(msg)
        self.trace = trace or []

    def __str__(self):
        if not self.trace:
            return f"ViGo Error: {super().__str__()}"
        return f"ViGo Error: {super().__str__()}\nCall stack:\n" + \
               '\n'.join(f"  ⚡ {t}" for t in reversed(self.trace))


class ReturnException(Exception):
    def __init__(self, value): self.value = value

class BreakException(Exception): pass
class ContinueException(Exception): pass

class AwaitException(Exception):
    def __init__(self, sec): self.seconds = sec