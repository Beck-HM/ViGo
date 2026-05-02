import hashlib
import base64
import uuid
from ..runtime.objects import BuiltinFunction


def register(env):
    env.define('md5',           BuiltinFunction(lambda s: hashlib.md5(s.encode()).hexdigest(), 'md5'))
    env.define('sha256',        BuiltinFunction(lambda s: hashlib.sha256(s.encode()).hexdigest(), 'sha256'))
    env.define('sha512',        BuiltinFunction(lambda s: hashlib.sha512(s.encode()).hexdigest(), 'sha512'))
    env.define('base64_encode', BuiltinFunction(lambda s: base64.b64encode(s.encode()).decode(), 'base64_encode'))
    env.define('base64_decode', BuiltinFunction(lambda s: base64.b64decode(s.encode()).decode(), 'base64_decode'))
    env.define('uuid',          BuiltinFunction(lambda: uuid.uuid4().hex, 'uuid'))
    env.define('short_uuid',    BuiltinFunction(lambda: uuid.uuid4().hex[:8], 'short_uuid'))