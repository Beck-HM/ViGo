"""ViGo Standard Library: Network Protocols (netlib)
Provides HTTP, TCP, UDP, and basic networking utilities.
Uses Python stdlib — no third-party dependencies.
"""
import urllib.request
import urllib.error
import socket
_USER_AGENT = 'ViGo/3.7'
import json as _json
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


def register(env):
    # ── HTTP ──

    def _http_get(url, headers=None, timeout=10):
        """Send an HTTP GET request. Returns response body as string."""
        try:
            req_headers = {'User-Agent': _USER_AGENT}
            if headers and isinstance(headers, dict):
                req_headers.update(headers)
            req = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(req, timeout=int(timeout)) as r:
                return r.read().decode('utf-8')
        except Exception as e:
            raise ViGoError(f"HTTP GET failed: {e}")

    def _http_post(url, data="", headers=None, content_type="application/json", timeout=10):
        """Send an HTTP POST request. Returns response body as string."""
        try:
            req_headers = {'User-Agent': _USER_AGENT, 'Content-Type': content_type}
            if headers and isinstance(headers, dict):
                req_headers.update(headers)
            body = data if isinstance(data, bytes) else str(data).encode('utf-8')
            req = urllib.request.Request(url, data=body, headers=req_headers)
            with urllib.request.urlopen(req, timeout=int(timeout)) as r:
                return r.read().decode('utf-8')
        except Exception as e:
            raise ViGoError(f"HTTP POST failed: {e}")

    def _http_put(url, data="", headers=None, timeout=10):
        """Send an HTTP PUT request. Returns response body as string."""
        try:
            req_headers = {'User-Agent': _USER_AGENT, 'Content-Type': 'application/json'}
            if headers and isinstance(headers, dict):
                req_headers.update(headers)
            body = data if isinstance(data, bytes) else str(data).encode('utf-8')
            req = urllib.request.Request(url, data=body, headers=req_headers, method='PUT')
            with urllib.request.urlopen(req, timeout=int(timeout)) as r:
                return r.read().decode('utf-8')
        except Exception as e:
            raise ViGoError(f"HTTP PUT failed: {e}")

    def _http_delete(url, headers=None, timeout=10):
        """Send an HTTP DELETE request. Returns response body as string."""
        try:
            req_headers = {'User-Agent': _USER_AGENT}
            if headers and isinstance(headers, dict):
                req_headers.update(headers)
            req = urllib.request.Request(url, headers=req_headers, method='DELETE')
            with urllib.request.urlopen(req, timeout=int(timeout)) as r:
                return r.read().decode('utf-8')
        except Exception as e:
            raise ViGoError(f"HTTP DELETE failed: {e}")

    def _http_get_json(url, headers=None, timeout=10):
        """Send an HTTP GET and parse JSON response."""
        text = _http_get(url, headers, timeout)
        return _json.loads(text)

    def _http_post_json(url, data, headers=None, timeout=10):
        """Send an HTTP POST with JSON body and parse JSON response."""
        body = _json.dumps(data) if isinstance(data, (dict, list)) else str(data)
        text = _http_post(url, body, headers, 'application/json', timeout)
        return _json.loads(text)

    def _http_download(url, filepath, timeout=60):
        """Download a file from a URL and save it to disk."""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': _USER_AGENT})
            with urllib.request.urlopen(req, timeout=int(timeout)) as r:
                with open(filepath, 'wb') as f:
                    f.write(r.read())
            return True
        except Exception as e:
            raise ViGoError(f"Download failed: {e}")

    # ── TCP Socket ──

    def _tcp_send(host, port, message, timeout=5):
        """Send a message over TCP and return the response."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(int(timeout))
            sock.connect((host, int(port)))
            sock.sendall(message.encode('utf-8'))
            response = sock.recv(4096)
            sock.close()
            return response.decode('utf-8')
        except Exception as e:
            raise ViGoError(f"TCP send failed: {e}")

    def _tcp_client(host, port, timeout=5):
        """Create a simple TCP client that returns a dict with send/recv/close methods.
        Not a full socket wrapper — returns raw bytes for flexibility."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(int(timeout))
            sock.connect((host, int(port)))
            return {
                "send": lambda msg: sock.sendall(msg.encode() if isinstance(msg, str) else msg),
                "recv": lambda size=4096: sock.recv(int(size)),
                "close": lambda: sock.close(),
                "__socket__": sock,
            }
        except Exception as e:
            raise ViGoError(f"TCP connect failed: {e}")

    # ── UDP Socket ──

    def _udp_send(host, port, message, timeout=5):
        """Send a UDP message and wait for a response."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(int(timeout))
            sock.sendto(message.encode('utf-8'), (host, int(port)))
            data, addr = sock.recvfrom(4096)
            sock.close()
            return data.decode('utf-8')
        except Exception as e:
            raise ViGoError(f"UDP send failed: {e}")

    def _udp_send_only(host, port, message):
        """Send a UDP message without waiting for a response."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(message.encode('utf-8'), (host, int(port)))
            sock.close()
            return True
        except Exception as e:
            raise ViGoError(f"UDP send failed: {e}")

    # ── DNS ──

    def _dns_lookup(hostname):
        """Resolve a hostname to an IP address."""
        try:
            return socket.gethostbyname(hostname)
        except Exception as e:
            raise ViGoError(f"DNS lookup failed: {e}")

    def _dns_reverse(ip):
        """Reverse DNS lookup — get hostname from IP."""
        try:
            return socket.gethostbyaddr(ip)[0]
        except Exception as e:
            raise ViGoError(f"Reverse DNS failed: {e}")

    # ── Network utilities ──

    def _url_encode(text):
        """URL-encode a string."""
        import urllib.parse
        return urllib.parse.quote(str(text))

    def _url_decode(text):
        """URL-decode a string."""
        import urllib.parse
        return urllib.parse.unquote(str(text))

    def _parse_url(url):
        """Parse a URL into components (scheme, host, path, query, fragment)."""
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        return {
            "scheme": parsed.scheme,
            "host": parsed.hostname or "",
            "port": parsed.port or 0,
            "path": parsed.path or "",
            "query": parsed.query or "",
            "fragment": parsed.fragment or "",
        }

    def _build_url(scheme, host, path="/", query="", port=0):
        """Build a URL from components."""
        port_str = f":{port}" if port else ""
        query_str = f"?{query}" if query else ""
        return f"{scheme}://{host}{port_str}{path}{query_str}"

    def _ping(host, count=4, timeout=2):
        """Simple TCP ping — tries to connect to port 80 or 443. Returns latency in ms."""
        import time
        results = []
        for _ in range(int(count)):
            try:
                start = time.time()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(int(timeout))
                sock.connect((host, 80))
                elapsed = (time.time() - start) * 1000
                sock.close()
                results.append(elapsed)
            except Exception:
                results.append(-1)
        return results

    def _local_ip():
        """Get the local machine's IP address."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            sock.close()
            return ip
        except Exception:
            return "127.0.0.1"

    # ── Registration ──

    env.define('http_get',       BuiltinFunction(_http_get, 'http_get'))
    env.define('http_post',      BuiltinFunction(_http_post, 'http_post'))
    env.define('http_put',       BuiltinFunction(_http_put, 'http_put'))
    env.define('http_delete',    BuiltinFunction(_http_delete, 'http_delete'))
    env.define('http_get_json',  BuiltinFunction(_http_get_json, 'http_get_json'))
    env.define('http_post_json', BuiltinFunction(_http_post_json, 'http_post_json'))
    env.define('http_download',  BuiltinFunction(_http_download, 'http_download'))
    env.define('tcp_send',       BuiltinFunction(_tcp_send, 'tcp_send'))
    env.define('tcp_client',     BuiltinFunction(_tcp_client, 'tcp_client'))
    env.define('udp_send',       BuiltinFunction(_udp_send, 'udp_send'))
    env.define('udp_send_only',  BuiltinFunction(_udp_send_only, 'udp_send_only'))
    env.define('dns_lookup',     BuiltinFunction(_dns_lookup, 'dns_lookup'))
    env.define('dns_reverse',    BuiltinFunction(_dns_reverse, 'dns_reverse'))
    env.define('url_encode',     BuiltinFunction(_url_encode, 'url_encode'))
    env.define('url_decode',     BuiltinFunction(_url_decode, 'url_decode'))
    env.define('parse_url',      BuiltinFunction(_parse_url, 'parse_url'))
    env.define('build_url',      BuiltinFunction(_build_url, 'build_url'))
    env.define('ping',           BuiltinFunction(_ping, 'ping'))
    env.define('local_ip',       BuiltinFunction(_local_ip, 'local_ip'))