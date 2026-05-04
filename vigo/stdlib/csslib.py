"""ViGo CSS Standard Library - CSS parsing and manipulation"""
import re
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


def register(env):
    """Register CSS functions into the ViGo environment."""

    def _css_extract_rules(css):
        """Extract all CSS rule blocks with their selectors.
        Returns list of [selector, properties_text] pairs."""
        rules = []
        # Remove comments
        text = re.sub(r'/\*.*?\*/', '', str(css), flags=re.DOTALL)
        for m in re.finditer(r'([^{]+)\{([^}]+)\}', text):
            selector = m.group(1).strip()
            properties = m.group(2).strip()
            rules.append([selector, properties])
        return rules

    def _css_get_property(css, selector, property_name):
        """Get a specific property value from a CSS rule by selector.
        Returns the value string or null if not found."""
        text = re.sub(r'/\*.*?\*/', '', str(css), flags=re.DOTALL)
        pattern = rf'{re.escape(str(selector))}\s*\{{[^}}]*{re.escape(str(property_name))}\s*:\s*([^;]+);'
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    def _css_extract_colors(css):
        """Extract all color values from CSS. Returns list of unique color strings."""
        colors = set()
        text = str(css)
        # Hex colors
        for m in re.finditer(r'#[0-9a-fA-F]{3,8}', text):
            colors.add(m.group(0))
        # rgb/rgba
        for m in re.finditer(r'rgba?\s*\([^)]+\)', text, re.IGNORECASE):
            colors.add(m.group(0))
        # hsl/hsla
        for m in re.finditer(r'hsla?\s*\([^)]+\)', text, re.IGNORECASE):
            colors.add(m.group(0))
        # Named colors
        named = {'red','blue','green','yellow','black','white','orange','purple','pink',
                 'gray','grey','brown','navy','teal','aqua','lime','maroon','olive','silver'}
        for color in named:
            if re.search(rf'\b{color}\b', text, re.IGNORECASE):
                colors.add(color)
        return sorted(list(colors))

    def _css_extract_classes(css):
        """Extract all class selectors (.classname) from CSS. Returns list of class names."""
        classes = set()
        for m in re.finditer(r'\.([a-zA-Z_][\w-]*)', str(css)):
            classes.add(m.group(1))
        return sorted(list(classes))

    def _css_extract_ids(css):
        """Extract all ID selectors (#id) from CSS. Returns list of IDs."""
        ids = set()
        for m in re.finditer(r'#([a-zA-Z_][\w-]*)', str(css)):
            ids.add(m.group(1))
        return sorted(list(ids))

    def _css_extract_fonts(css):
        """Extract font-family values from CSS. Returns list of font names."""
        fonts = set()
        for m in re.finditer(r'font-family\s*:\s*([^;]+);', str(css), re.IGNORECASE):
            families = m.group(1)
            for font in re.finditer(r"['\"]?([^,'\"]+)['\"]?", families):
                f = font.group(1).strip()
                if f and f.lower() not in ('sans-serif','serif','monospace','cursive','fantasy','inherit','initial'):
                    fonts.add(f)
        return sorted(list(fonts))

    def _css_minify(css):
        """Minify CSS by removing whitespace, comments, and unnecessary characters."""
        text = str(css)
        # Remove comments
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        # Remove whitespace around special characters
        text = re.sub(r'\s*([{}:;,])\s*', r'\1', text)
        # Remove last semicolon before closing brace
        text = re.sub(r';\}', '}', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        # Collapse multiple spaces
        text = re.sub(r'\s{2,}', ' ', text)
        return text

    def _css_pretty(css):
        """Format CSS with proper indentation and line breaks."""
        text = re.sub(r'/\*.*?\*/', '', str(css), flags=re.DOTALL)
        text = text.strip()
        # Add newlines after braces
        text = re.sub(r'\{', ' {\n    ', text)
        text = re.sub(r'\}', '\n}\n', text)
        text = re.sub(r';(?!\n)', ';\n    ', text)
        # Clean up extra spaces
        text = re.sub(r'\n\s*\n', '\n', text)
        text = re.sub(r'^\s+', '', text)
        text = re.sub(r'\s+$', '', text)
        return text

    def _css_parse_inline(style_string):
        """Parse an inline CSS style string into a dictionary.
        Returns dict with property: value pairs."""
        result = {}
        for part in str(style_string).split(';'):
            part = part.strip()
            if ':' in part:
                prop, value = part.split(':', 1)
                result[prop.strip()] = value.strip()
        return result

    def _css_to_inline(properties_dict):
        """Convert a properties dict to an inline CSS style string."""
        if not isinstance(properties_dict, dict):
            return ""
        parts = []
        for k, v in properties_dict.items():
            parts.append(f"{k}: {v}")
        return "; ".join(parts)

    env.define('css_rules',      BuiltinFunction(_css_extract_rules,   'css_rules'))
    env.define('css_get',        BuiltinFunction(_css_get_property,    'css_get'))
    env.define('css_colors',     BuiltinFunction(_css_extract_colors,  'css_colors'))
    env.define('css_classes',    BuiltinFunction(_css_extract_classes, 'css_classes'))
    env.define('css_ids',        BuiltinFunction(_css_extract_ids,     'css_ids'))
    env.define('css_fonts',      BuiltinFunction(_css_extract_fonts,   'css_fonts'))
    env.define('css_minify',     BuiltinFunction(_css_minify,          'css_minify'))
    env.define('css_pretty',     BuiltinFunction(_css_pretty,          'css_pretty'))
    env.define('css_parse_inline',BuiltinFunction(_css_parse_inline,   'css_parse_inline'))
    env.define('css_to_inline',  BuiltinFunction(_css_to_inline,       'css_to_inline'))