from .errors import ViGoError


class Environment:
    def __init__(self, parent=None):
        self.variables = {}
        self.parent = parent
        self.symbol_table = None  # Set when entering a function scope

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
        # Fast path: symbol table guided O(1) lookup
        if self.symbol_table is not None:
            kind = self.symbol_table.classify(name)
            if kind == 'local':
                if name in self.variables:
                    return self.variables[name]
                raise ViGoError(f"Variable '{name}' is not defined")
            elif kind == 'closure':
                env = self.parent
                while env is not None:
                    if name in env.variables:
                        return env.variables[name]
                    env = env.parent
                raise ViGoError(f"Variable '{name}' is not defined")
            else:  # global
                root = self
                while root.parent is not None:
                    root = root.parent
                if name in root.variables:
                    return root.variables[name]
                raise ViGoError(f"Variable '{name}' is not defined")

        # Slow path: recursive parent chain walk (no symbol table)
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