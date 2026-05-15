"""ViGo Standard Library: Stream Processing (streamlib)
Lazy, chainable stream processing for large files and real-time data.
Pure Python stdlib — zero external dependencies.
"""
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


class Stream:
    """Lazy iterable stream with chainable operations."""
    
    def __init__(self, source):
        """Create a stream from an iterable source or file path."""
        if isinstance(source, str):
            # File path
            self._source = source
            self._is_file = True
        elif hasattr(source, '__iter__') and not isinstance(source, (str, dict)):
            self._source = source
            self._is_file = False
        else:
            raise ViGoError("Stream source must be a file path or iterable")
    
    def _iter_lines(self):
        """Yield lines from source."""
        if self._is_file:
            with open(self._source, 'r', encoding='utf-8') as f:
                for line in f:
                    yield line.rstrip('\n\r')
        else:
            for item in self._source:
                yield item
    
    def filter(self, predicate):
        """Filter items by predicate. Returns new Stream."""
        def gen():
            for item in self._iter_lines():
                if predicate(item):
                    yield item
        return Stream(gen())
    
    def map(self, transform):
        """Transform each item. Returns new Stream."""
        def gen():
            for item in self._iter_lines():
                yield transform(item)
        return Stream(gen())
    
    def head(self, n):
        """Take first n items."""
        def gen():
            for i, item in enumerate(self._iter_lines()):
                if i >= n:
                    break
                yield item
        return Stream(gen())
    
    def tail(self, n):
        """Take last n items (requires buffering)."""
        buf = []
        for item in self._iter_lines():
            buf.append(item)
            if len(buf) > n:
                buf.pop(0)
        return Stream(buf)
    
    def drop(self, n):
        """Skip first n items."""
        def gen():
            for i, item in enumerate(self._iter_lines()):
                if i >= n:
                    yield item
        return Stream(gen())
    
    def chunk(self, size):
        """Group items into chunks of given size."""
        def gen():
            batch = []
            for item in self._iter_lines():
                batch.append(item)
                if len(batch) >= size:
                    yield batch
                    batch = []
            if batch:
                yield batch
        return Stream(gen())
    
    def flatten(self):
        """Flatten nested iterables."""
        def gen():
            for item in self._iter_lines():
                if hasattr(item, '__iter__') and not isinstance(item, str):
                    for sub in item:
                        yield sub
                else:
                    yield item
        return Stream(gen())
    
    def dedupe(self):
        """Remove consecutive duplicates."""
        def gen():
            prev = object()
            for item in self._iter_lines():
                if item != prev:
                    yield item
                    prev = item
        return Stream(gen())
    
    def sort(self, key=None, reverse=False):
        """Sort items (requires full load into memory)."""
        items = list(self._iter_lines())
        items.sort(key=key, reverse=reverse)
        return Stream(items)
    
    def count(self):
        """Count items in stream."""
        n = 0
        for _ in self._iter_lines():
            n += 1
        return n
    
    def sum(self):
        """Sum numeric items."""
        total = 0
        for item in self._iter_lines():
            try:
                total += float(item)
            except (ValueError, TypeError):
                pass
        return total
    
    def collect(self):
        """Collect all items into a list."""
        return list(self._iter_lines())
    
    def write_file(self, filepath):
        """Write stream to file, one item per line."""
        with open(filepath, 'w', encoding='utf-8') as f:
            for item in self._iter_lines():
                f.write(str(item) + '\n')
        return filepath
    
    def __iter__(self):
        return self._iter_lines()


def stream(source):
    """Create a Stream from a file path or list."""
    return Stream(source)


def register(env):
    env.define("Stream", BuiltinFunction(lambda source: Stream(source), "Stream"))
    env.define("stream", BuiltinFunction(lambda source: Stream(source), "stream"))