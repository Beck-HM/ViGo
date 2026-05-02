from .errors import ViGoError


class Environment:
    def __init__(self, parent=None):
        self.variables = {}
        self.parent = parent

    def define(self, name, value):
        self.variables[name] = value

    def assign(self, name, value):
        if name in self.variables:
            self.variables[name] = value
        elif self.parent:
            self.parent.assign(name, value)
        else:
            self.variables[name] = value

    def lookup(self, name):
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.lookup(name)
        raise ViGoError(f"Variable '{name}' is not defined")

    def has(self, name):
        if name in self.variables:
            return True
        if self.parent:
            return self.parent.has(name)
        return False

    def __repr__(self):
        return f"Environment({self.variables})"