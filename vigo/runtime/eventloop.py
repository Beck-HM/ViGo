"""ViGo Async Event Loop — spawn/await concurrency."""
import threading


class Task:
    """A spawned concurrent task."""
    def __init__(self, name, target, args):
        self.name = name
        self.result = None
        self.error = None
        self.done = False
        self._thread = threading.Thread(target=self._run, args=(target, args))
        self._thread.daemon = True

    def _run(self, target, args):
        try:
            self.result = target(*args)
        except Exception as e:
            self.error = str(e)
        finally:
            self.done = True

    def start(self):
        self._thread.start()

    def wait(self, timeout=None):
        self._thread.join(timeout)
        return self.result


class EventLoop:
    """Simple event loop for managing concurrent tasks."""
    def __init__(self):
        self.tasks = {}

    def spawn(self, name, func, args):
        """Launch a function call in a new thread."""
        task = Task(name, func, args)
        self.tasks[name] = task
        task.start()
        return task

    def await_all(self, names):
        """Wait for named tasks and return their results."""
        results = {}
        for name in names:
            task = self.tasks.get(name)
            if task:
                task.wait()
                if task.error:
                    results[name] = {"status": "error", "error": task.error}
                else:
                    results[name] = {"status": "ok", "result": task.result}
            else:
                results[name] = {"status": "error", "error": f"Task '{name}' not found"}
        return results

    def clear(self):
        self.tasks = {}


_event_loop = EventLoop()


def get_event_loop():
    return _event_loop