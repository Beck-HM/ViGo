"""Color tools: RGB / HSL / HEX Conversion"""
from ..runtime.objects import BuiltinFunction


def _rgb(r, g, b):
    """Create RGB Color dictionary"""
    return {'r': max(0, min(255, int(r))),
            'g': max(0, min(255, int(g))),
            'b': max(0, min(255, int(b)))}

def _rgb_to_hex(r, g=None, b=None):
    """RGB Convert to hex color string, supports rgb(r,g,b) or rgb({r,g,b})"""
    if g is None and b is None and isinstance(r, dict):
        r, g, b = r['r'], r['g'], r['b']
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

def _hex_to_rgb(hex_str):
    """Hex color to RGB Dictionary"""
    h = hex_str.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    if len(h) == 6:
        return {'r': int(h[0:2], 16), 'g': int(h[2:4], 16), 'b': int(h[4:6], 16)}
    return {'r': 0, 'g': 0, 'b': 0}

def _rgb_to_hsl(r, g=None, b=None):
    """RGB To HSL, supports rgb(r,g,b) or rgb({r,g,b})"""
    if g is None and b is None and isinstance(r, dict):
        r, g, b = r['r'], r['g'], r['b']
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    mx = max(r, g, b)
    mn = min(r, g, b)
    d = mx - mn
    l = (mx + mn) / 2
    if d == 0:
        h = s = 0
    else:
        s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
        if mx == r:
            h = ((g - b) / d) % 6
        elif mx == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        h *= 60
    return {'h': round(h), 's': round(s * 100), 'l': round(l * 100)}

def _hsl_to_rgb(h, s, l):
    """HSL To RGB Dictionary"""
    s, l = s / 100.0, l / 100.0
    if s == 0:
        r = g = b = l
    else:
        def hue_to_rgb(p, q, t):
            if t < 0: t += 1
            if t > 1: t -= 1
            if t < 1/6: return p + (q - p) * 6 * t
            if t < 1/2: return q
            if t < 2/3: return p + (q - p) * (2/3 - t) * 6
            return p
        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q
        h = (h % 360) / 360.0
        r = hue_to_rgb(p, q, h + 1/3)
        g = hue_to_rgb(p, q, h)
        b = hue_to_rgb(p, q, h - 1/3)
    return {'r': round(r * 255), 'g': round(g * 255), 'b': round(b * 255)}

def _lerp_color(c1, c2, t):
    """Color linear interpolation"""
    t = max(0, min(1, t))
    return {'r': round(c1['r'] + (c2['r'] - c1['r']) * t),
            'g': round(c1['g'] + (c2['g'] - c1['g']) * t),
            'b': round(c1['b'] + (c2['b'] - c1['b']) * t)}


def register(env):
    env.define('rgb',          BuiltinFunction(_rgb, 'rgb'))
    env.define('rgb_to_hex',   BuiltinFunction(_rgb_to_hex, 'rgb_to_hex'))
    env.define('hex_to_rgb',   BuiltinFunction(_hex_to_rgb, 'hex_to_rgb'))
    env.define('rgb_to_hsl',   BuiltinFunction(_rgb_to_hsl, 'rgb_to_hsl'))
    env.define('hsl_to_rgb',   BuiltinFunction(_hsl_to_rgb, 'hsl_to_rgb'))
    env.define('lerp_color',   BuiltinFunction(_lerp_color, 'lerp_color'))