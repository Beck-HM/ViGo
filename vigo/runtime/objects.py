class BuiltinFunction:
    def __init__(self, func, name='<Builtin>'):
        self.func = func
        self.name = name

    def __repr__(self):
        return f"⚙️ {self.name}"


class ViGoFunction:
    def __init__(self, name, params, defaults, rest_param, body, closure, src=None):
        self.name = name
        self.params = params
        self.defaults = defaults
        self.rest_param = rest_param
        self.body = body
        self.closure = closure
        self.source_file = src
        self.is_static = False

    def __repr__(self):
        return f"🎯 {self.name}"


class LambdaFunction(ViGoFunction):
    def __init__(self, params, body, closure):
        super().__init__('<lambda>', params, {}, None, body, closure)


class ViGoClass:
    def __init__(self, name, parent, body, closure, src=None):
        self.name = name
        self.parent = parent
        self.body = body
        self.closure = closure
        self.source_file = src

    def __repr__(self):
        return f"🏛️ {self.name}"


class ViGoInstance:
    def __init__(self, cls, env):
        self.cls = cls
        self.env = env

    def __repr__(self):
        return f"<{self.cls.name} Instance>"


class ViGoEnum:
    def __init__(self, name, members):
        self.name = name
        self.members = members

    def __repr__(self):
        return f"📋 {self.name}"