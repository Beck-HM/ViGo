import urllib.request
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


def register(env):
    def _get(url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'ViGo/3.1'})
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.read().decode('utf-8')
        except Exception as e:
            raise ViGoError(f"HTTP GET failed: {e}")

    def _post(url, data=''):
        try:
            req = urllib.request.Request(url, data=data.encode(), headers={'User-Agent': 'ViGo/3.1'})
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.read().decode('utf-8')
        except Exception as e:
            raise ViGoError(f"HTTP POST failed: {e}")

    env.define('http_get',  BuiltinFunction(_get, 'http_get'))
    env.define('http_post', BuiltinFunction(_post, 'http_post'))