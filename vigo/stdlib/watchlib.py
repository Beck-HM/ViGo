"""ViGo Standard Library: File System Watcher (watchlib)
Monitor file changes and trigger callbacks.
Uses polling by default, watchdog if available.
"""
import os
import time
import threading
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


class Watcher:
    def __init__(self, path, pattern=None, ignore=None):
        self.path = os.path.abspath(path)
        self.pattern = pattern
        self.ignore = ignore or []
        self._callbacks = {"change": [], "create": [], "delete": []}
        self._running = False
        self._thread = None
        self._snapshot = {}
        self._take_snapshot()
    
    def _take_snapshot(self):
        """Record current state of watched directory."""
        snapshot = {}
        for root, dirs, files in os.walk(self.path):
            for name in files:
                if self._should_watch(name):
                    fpath = os.path.join(root, name)
                    try:
                        snapshot[fpath] = os.path.getmtime(fpath)
                    except OSError:
                        pass
        self._snapshot = snapshot
    
    def _should_watch(self, name):
        """Check if file matches pattern and not ignored."""
        if self.pattern:
            import fnmatch
            if not fnmatch.fnmatch(name, self.pattern):
                return False
        for ig in self.ignore:
            if ig in name:
                return False
        return True
    
    def _poll(self):
        """Poll for changes."""
        while self._running:
            new_snapshot = {}
            for root, dirs, files in os.walk(self.path):
                for name in files:
                    if self._should_watch(name):
                        fpath = os.path.join(root, name)
                        try:
                            new_snapshot[fpath] = os.path.getmtime(fpath)
                        except OSError:
                            pass
            
            # Detect changes
            for fpath in new_snapshot:
                if fpath not in self._snapshot:
                    self._fire("create", fpath)
                elif new_snapshot[fpath] != self._snapshot[fpath]:
                    self._fire("change", fpath)
            
            for fpath in self._snapshot:
                if fpath not in new_snapshot:
                    self._fire("delete", fpath)
            
            self._snapshot = new_snapshot
            time.sleep(1)
    
    def _fire(self, event_type, path):
        """Fire callbacks for an event."""
        for cb in self._callbacks.get(event_type, []):
            try:
                cb(path)
            except Exception:
                pass
    
    def on_change(self, callback):
        self._callbacks["change"].append(callback)
        return self
    
    def on_create(self, callback):
        self._callbacks["create"].append(callback)
        return self
    
    def on_delete(self, callback):
        self._callbacks["delete"].append(callback)
        return self
    
    def start(self):
        if self._running:
            return True
        self._running = True
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()
        return True
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        return True


def watch(path, pattern=None, ignore=None):
    """Create a file system watcher."""
    return Watcher(path, pattern=pattern, ignore=ignore)


def register(env):
    env.define("Watcher", BuiltinFunction(lambda path, pattern=None, ignore=None: Watcher(path, pattern, ignore), "Watcher"))
    env.define("watch", BuiltinFunction(lambda path, pattern=None, ignore=None: watch(path, pattern, ignore), "watch"))