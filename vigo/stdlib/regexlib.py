"""ViGo Regex Standard Library - Regular expression support"""
import re
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


def register(env):
    """Register regex functions into the ViGo environment."""

    def _regex_match(pattern, text):
        """Check if pattern matches anywhere in text. Returns ok/no."""
        try:
            return bool(re.search(pattern, str(text)))
        except re.error as e:
            raise ViGoError(f"Regex error: {e}")

    def _regex_search(pattern, text):
        """Return the first match as a string, or null if no match."""
        try:
            m = re.search(pattern, str(text))
            return m.group(0) if m else None
        except re.error as e:
            raise ViGoError(f"Regex error: {e}")

    def _regex_find_all(pattern, text):
        """Return a list of all non-overlapping matches as strings."""
        try:
            return re.findall(pattern, str(text))
        except re.error as e:
            raise ViGoError(f"Regex error: {e}")

    def _regex_replace(pattern, replacement, text, count=0):
        """Replace occurrences of pattern with replacement.
        count=0 means replace all. Returns the modified string."""
        try:
            return re.sub(pattern, str(replacement), str(text), count=int(count))
        except re.error as e:
            raise ViGoError(f"Regex error: {e}")

    def _regex_split(pattern, text, maxsplit=0):
        """Split text by regex pattern.
        maxsplit=0 means split all. Returns a list of strings."""
        try:
            return re.split(pattern, str(text), maxsplit=int(maxsplit))
        except re.error as e:
            raise ViGoError(f"Regex error: {e}")

    def _regex_escape(text):
        """Escape special regex characters in text. Returns the escaped string."""
        return re.escape(str(text))

    def _regex_extract_groups(pattern, text):
        """Return a list of all group matches (first match only).
        Group 0 = full match, group 1+ = captured groups."""
        try:
            m = re.search(pattern, str(text))
            if m:
                return list(m.groups())
            return []
        except re.error as e:
            raise ViGoError(f"Regex error: {e}")

    def _regex_test(pattern):
        """Check if a regex pattern is valid. Returns ok/no."""
        try:
            re.compile(pattern)
            return True
        except re.error:
            return False

    def _regex_count(pattern, text):
        """Count non-overlapping occurrences of pattern in text."""
        try:
            return len(re.findall(pattern, str(text)))
        except re.error as e:
            raise ViGoError(f"Regex error: {e}")

    env.define('regex_match',   BuiltinFunction(_regex_match,   'regex_match'))
    env.define('regex_search',  BuiltinFunction(_regex_search,  'regex_search'))
    env.define('regex_find_all',BuiltinFunction(_regex_find_all,'regex_find_all'))
    env.define('regex_replace', BuiltinFunction(_regex_replace,'regex_replace'))
    env.define('regex_split',   BuiltinFunction(_regex_split,   'regex_split'))
    env.define('regex_escape',  BuiltinFunction(_regex_escape,  'regex_escape'))
    env.define('regex_groups',  BuiltinFunction(_regex_extract_groups, 'regex_groups'))
    env.define('regex_test',    BuiltinFunction(_regex_test,    'regex_test'))
    env.define('regex_count',   BuiltinFunction(_regex_count,   'regex_count'))