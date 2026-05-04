"""ViGo Markdown Standard Library - Markdown to HTML conversion"""
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


def register(env):
    """Register markdown functions into the ViGo environment."""

    def _md_to_html(text):
        """Convert Markdown text to HTML. Returns the HTML string."""
        try:
            text = str(text)
            html = _simple_markdown_to_html(text)
            return html
        except Exception as e:
            raise ViGoError(f"Markdown error: {e}")

    def _md_extract_links(text):
        """Extract all [text](url) links from Markdown. Returns list of [text, url] pairs."""
        import re
        links = []
        for m in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', str(text)):
            links.append([m.group(1), m.group(2)])
        return links

    def _md_extract_headers(text):
        """Extract all headers (# to ######) from Markdown. Returns list of [level, text] pairs."""
        import re
        headers = []
        for m in re.finditer(r'^(#{1,6})\s+(.+)$', str(text), re.MULTILINE):
            headers.append([len(m.group(1)), m.group(2).strip()])
        return headers

    def _md_extract_code_blocks(text):
        """Extract all fenced code blocks from Markdown. Returns list of [language, code] pairs."""
        import re
        blocks = []
        for m in re.finditer(r'```(\w*)\n(.*?)```', str(text), re.DOTALL):
            blocks.append([m.group(1) or '', m.group(2).strip()])
        return blocks

    def _md_to_plain(text):
        """Strip all Markdown formatting, returning plain text."""
        import re
        text = str(text)
        # Remove images
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)
        # Remove links, keep text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # Remove headers markers
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # Remove bold/italic
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'___(.+?)___', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        # Remove inline code
        text = re.sub(r'`([^`]+)`', r'\1', text)
        # Remove code blocks
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        # Remove horizontal rules
        text = re.sub(r'^[*-]{3,}\s*$', '', text, flags=re.MULTILINE)
        # Remove blockquote markers
        text = re.sub(r'^>\s?', '', text, flags=re.MULTILINE)
        # Remove list markers
        text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)
        # Collapse whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _md_count_words(text):
        """Count words in Markdown text (after stripping formatting)."""
        plain = _md_to_plain(text)
        words = plain.split()
        return len(words)

    def _md_table_to_list(text):
        """Extract tables from Markdown and return as list of rows (each row is a list of cells)."""
        import re
        tables = []
        lines = str(text).split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('|') and line.endswith('|'):
                rows = []
                # Header row
                cells = [c.strip() for c in line.split('|')[1:-1]]
                rows.append(cells)
                i += 1
                # Separator row
                if i < len(lines) and re.match(r'^[\|\s\-:]+\|$', lines[i].strip()):
                    i += 1
                # Data rows
                while i < len(lines):
                    row_line = lines[i].strip()
                    if row_line.startswith('|') and row_line.endswith('|'):
                        data_cells = [c.strip() for c in row_line.split('|')[1:-1]]
                        rows.append(data_cells)
                        i += 1
                    else:
                        break
                tables.append(rows)
            else:
                i += 1
        return tables

    env.define('md_to_html',        BuiltinFunction(_md_to_html,        'md_to_html'))
    env.define('md_extract_links',   BuiltinFunction(_md_extract_links,   'md_extract_links'))
    env.define('md_extract_headers', BuiltinFunction(_md_extract_headers, 'md_extract_headers'))
    env.define('md_extract_code',    BuiltinFunction(_md_extract_code_blocks, 'md_extract_code'))
    env.define('md_to_plain',       BuiltinFunction(_md_to_plain,       'md_to_plain'))
    env.define('md_count_words',    BuiltinFunction(_md_count_words,    'md_count_words'))
    env.define('md_table_to_list',  BuiltinFunction(_md_table_to_list,  'md_table_to_list'))
    env.define('md_escape_html',    BuiltinFunction(lambda t: str(t).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;'), 'md_escape_html'))


def _simple_markdown_to_html(text):
    """Simple Markdown to HTML converter (no external dependencies)."""
    import re

    # Escape HTML first
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # Code blocks (must be before other processing)
    code_blocks = {}
    def _save_code(m):
        key = f'%%CODEBLOCK{len(code_blocks)}%%'
        lang = m.group(1) or ''
        code = m.group(2)
        escaped = code.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        code_blocks[key] = f'<pre><code class="language-{lang}">{escaped}</code></pre>'
        return key
    text = re.sub(r'```(\w*)\n(.*?)```', _save_code, text, flags=re.DOTALL)

    # Inline code
    inline_codes = {}
    def _save_inline(m):
        key = f'%%INLINECODE{len(inline_codes)}%%'
        inline_codes[key] = f'<code>{m.group(1)}</code>'
        return key
    text = re.sub(r'`([^`]+)`', _save_inline, text)

    # Headers
    text = re.sub(r'^###### (.+)$', r'<h6>\1</h6>', text, flags=re.MULTILINE)
    text = re.sub(r'^##### (.+)$', r'<h5>\1</h5>', text, flags=re.MULTILINE)
    text = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)

    # Bold and italic
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

    # Images
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', text)

    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

    # Horizontal rules
    text = re.sub(r'^[*-]{3,}\s*$', '<hr>', text, flags=re.MULTILINE)

    # Blockquotes
    text = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', text, flags=re.MULTILINE)

    # Unordered lists
    text = re.sub(r'^[\s]*[-*+] (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', text)

    # Paragraphs: wrap non-tag lines
    paragraphs = []
    current = []
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped == '':
            if current:
                paragraphs.append(' '.join(current))
                current = []
        elif stripped.startswith('<'):
            if current:
                paragraphs.append(' '.join(current))
                current = []
            paragraphs.append(stripped)
        else:
            current.append(stripped)
    if current:
        paragraphs.append(' '.join(current))

    result = []
    for p in paragraphs:
        if p.startswith('<'):
            result.append(p)
        else:
            result.append(f'<p>{p}</p>')

    text = '\n'.join(result)

    # Restore code blocks
    for key, html in code_blocks.items():
        text = text.replace(key, html)
    for key, html in inline_codes.items():
        text = text.replace(key, html)

    return text