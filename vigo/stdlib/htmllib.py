"""ViGo HTML Standard Library - HTML parsing and manipulation"""
import re
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


def register(env):
    """Register HTML functions into the ViGo environment."""

    def _html_strip_tags(html):
        """Remove all HTML tags, returning plain text."""
        return re.sub(r'<[^>]+>', '', str(html))

    def _html_extract_text(html):
        """Extract visible text from HTML, preserving paragraph breaks."""
        text = str(html)
        # Replace block elements with newlines
        text = re.sub(r'<(br|hr)\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</?(p|div|h[1-6]|li|tr|td|th|section|article|header|footer|nav|main)[^>]*>', '\n', text, flags=re.IGNORECASE)
        # Remove scripts and styles
        text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', text, flags=re.IGNORECASE | re.DOTALL)
        # Remove remaining tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode common entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
        # Collapse whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()

    def _html_extract_links(html):
        """Extract all <a href="...">text</a> links. Returns list of [text, href] pairs."""
        links = []
        for m in re.finditer(r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', str(html), re.IGNORECASE | re.DOTALL):
            text = re.sub(r'<[^>]+>', '', m.group(2)).strip()
            links.append([text, m.group(1)])
        return links

    def _html_extract_images(html):
        """Extract all <img src="..."> sources. Returns list of [alt, src] pairs."""
        images = []
        for m in re.finditer(r'<img\s[^>]*src=["\']([^"\']+)["\'][^>]*(?:alt=["\']([^"\']*)["\'])?[^>]*>', str(html), re.IGNORECASE):
            images.append([m.group(2) or '', m.group(1)])
        return images

    def _html_extract_table(html, index=0):
        """Extract a table from HTML as list of rows. index=0 means first table.
        Returns list of rows, each row is a list of cells."""
        tables = re.findall(r'<table[^>]*>(.*?)</table>', str(html), re.IGNORECASE | re.DOTALL)
        idx = int(index)
        if idx >= len(tables):
            return []
        table = tables[idx]
        rows = []
        for tr in re.finditer(r'<tr[^>]*>(.*?)</tr>', table, re.IGNORECASE | re.DOTALL):
            cells = []
            for cell in re.finditer(r'<(td|th)[^>]*>(.*?)</\1>', tr.group(1), re.IGNORECASE | re.DOTALL):
                cells.append(_html_strip_tags(cell.group(2)).strip())
            if cells:
                rows.append(cells)
        return rows

    def _html_count_tags(html, tag):
        """Count occurrences of a specific HTML tag."""
        pattern = f'<{re.escape(str(tag))}[\\s>]'
        return len(re.findall(pattern, str(html), re.IGNORECASE))

    def _html_get_meta(html, name):
        """Get content of <meta name="..."> tag. Returns content string or null."""
        pattern = f'<meta\\s[^>]*name=["\']{re.escape(str(name))}["\'][^>]*content=["\']([^"\']+)["\']'
        m = re.search(pattern, str(html), re.IGNORECASE)
        return m.group(1) if m else None

    def _html_get_title(html):
        """Extract the <title> from HTML. Returns string or null."""
        m = re.search(r'<title[^>]*>(.*?)</title>', str(html), re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else None

    def _html_to_text(html):
        """Full HTML to readable text conversion. Alias for _html_extract_text with entity decoding."""
        return _html_extract_text(html)

    def _html_attr_list(html, tag, attr):
        """Extract all values of a specific attribute from a specific tag.
        Returns list of attribute values."""
        pattern = f'<{re.escape(str(tag))}\\s[^>]*{re.escape(str(attr))}=["\']([^"\']+)["\']'
        return re.findall(pattern, str(html), re.IGNORECASE)

    env.define('html_strip',     BuiltinFunction(_html_strip_tags,    'html_strip'))
    env.define('html_text',      BuiltinFunction(_html_extract_text,  'html_text'))
    env.define('html_links',     BuiltinFunction(_html_extract_links, 'html_links'))
    env.define('html_images',    BuiltinFunction(_html_extract_images,'html_images'))
    env.define('html_table',     BuiltinFunction(_html_extract_table, 'html_table'))
    env.define('html_count_tag', BuiltinFunction(_html_count_tags,    'html_count_tag'))
    env.define('html_meta',      BuiltinFunction(_html_get_meta,      'html_meta'))
    env.define('html_title',     BuiltinFunction(_html_get_title,     'html_title'))
    env.define('html_to_text',   BuiltinFunction(_html_to_text,       'html_to_text'))
    env.define('html_attrs',     BuiltinFunction(_html_attr_list,     'html_attrs'))