"""ViGo Standard Library: Concurrency (concurrentlib)
Provides Lock, Workload (Semaphore), TaskPool (Thread/Process Pool), Asyn (Future), and Queue.
Pure Python stdlib — zero external dependencies.
"""
import threading
import multiprocessing
import queue as _queue
import time
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


class Lock:
    """Mutual exclusion lock. Use gain()/free() instead of acquire/release."""
    def __init__(self):
        self._lock = threading.Lock()
    
    def gain(self, timeout=None):
        """Acquire the lock. Returns True if successful."""
        return self._lock.acquire(timeout=timeout if timeout else -1)
    
    def free(self):
        """Release the lock."""
        self._lock.release()
    
    def __enter__(self):
        self.gain()
        return self
    
    def __exit__(self, *args):
        self.free()


class Workload:
    """Semaphore for controlling concurrency count."""
    def __init__(self, max_count=1):
        self._sem = threading.Semaphore(max_count)
    
    def gain(self, timeout=None):
        """Acquire the semaphore."""
        return self._sem.acquire(timeout=timeout if timeout else -1)
    
    def free(self):
        """Release the semaphore."""
        self._sem.release()


class Asyn:
    """Future-like placeholder for async task results."""
    def __init__(self):
        self._event = threading.Event()
        self._result = None
        self._error = None
        self._done = False
    
    def set_result(self, value):
        self._result = value
        self._done = True
        self._event.set()
    
    def set_error(self, error):
        self._error = str(error)
        self._done = True
        self._event.set()
    
    def get(self, timeout=None):
        """Wait for and return the result."""
        if not self._done:
            if timeout:
                self._event.wait(timeout)
            else:
                self._event.wait()
        if self._error:
            raise ViGoError(self._error)
        return self._result
    
    def ready(self):
        return self._done
    
    def result(self):
        return self._result if self._done else None


class TaskPool:
    """Thread/Process pool for parallel task execution."""
    def __init__(self, max_workers=4, mode="thread"):
        self.mode = mode
        self.max_workers = max_workers
        self._tasks = []
        self._results = []
        if mode == "process":
            self._pool = multiprocessing.Pool(processes=max_workers)
        else:
            self._pool = None
            self._threads = []
    
    def submit(self, func, *args, **kwargs):
        """Submit a task and return an Asyn future."""
        future = Asyn()
        
        def wrapper():
            try:
                result = func(*args, **kwargs)
                future.set_result(result)
            except Exception as e:
                future.set_error(e)
        
        if self.mode == "process":
            raise ViGoError("Process pool submit not yet supported — use map instead")
        else:
            t = threading.Thread(target=wrapper, daemon=True)
            t.start()
            self._threads.append(t)
        
        return future
    
    def map(self, func, iterable):
        items = list(iterable)
        
        # Only ViGo custom functions (not pure Python builtins) need interpreter context
        from ..runtime.objects import ViGoFunction, LambdaFunction
        needs_interpreter = isinstance(func, (ViGoFunction, LambdaFunction))
        
        if needs_interpreter:
            results = []
            for item in items:
                try:
                    results.append(func(item))
                except Exception as e:
                    results.append(f"Error: {e}")
            return results
        
        # Pure Python callables and builtins can run in threads
        if self.mode == "process":
            with multiprocessing.Pool(processes=self.max_workers) as pool:
                return pool.map(func, items)
        else:
            results = [None] * len(items)
            threads = []
            lock = threading.Lock()
            
            def worker(idx, item):
                try:
                    # Unwrap BuiltinFunction if needed
                    f = func.func if hasattr(func, 'func') else func
                    r = f(item)
                except Exception as e:
                    r = f"Error: {e}"
                with lock:
                    results[idx] = r
            
            for i, item in enumerate(items):
                t = threading.Thread(target=worker, args=(i, item))
                t.start()
                threads.append(t)
            
            for t in threads:
                t.join()
            
            return results
    
    def shutdown(self, wait=True):
        """Shutdown the pool."""
        if self.mode == "process" and self._pool:
            self._pool.terminate()
            self._pool = None
        elif self._threads and wait:
            for t in self._threads:
                t.join(timeout=5)
            self._threads = []
    
    def __del__(self):
        self.shutdown(wait=False)


class Queue:
    """Thread-safe task queue."""
    def __init__(self, maxsize=0):
        self._queue = _queue.Queue(maxsize=maxsize if maxsize > 0 else 0)
    
    def put(self, item, timeout=None):
        """Add an item to the queue."""
        self._queue.put(item, timeout=timeout)
    
    def get(self, timeout=None):
        """Remove and return an item from the queue."""
        return self._queue.get(timeout=timeout)
    
    def empty(self):
        return self._queue.empty()
    
    def size(self):
        return self._queue.qsize()


def parallel(func, iterable, max_workers=4, mode="thread"):
    """Convenience: apply func to iterable in parallel, return results."""
    pool = TaskPool(max_workers, mode)
    try:
        return pool.map(func, iterable)
    finally:
        pool.shutdown()


def sleep(seconds):
    """Sleep for the given number of seconds."""
    time.sleep(float(seconds))
    return True


def register(env):
    env.define("Lock", BuiltinFunction(lambda: Lock(), "Lock"))
    env.define("Workload", BuiltinFunction(lambda max_count=1: Workload(max_count), "Workload"))
    env.define("Asyn", BuiltinFunction(lambda: Asyn(), "Asyn"))
    env.define("TaskPool", BuiltinFunction(lambda max_workers=4, mode="thread": TaskPool(max_workers, mode), "TaskPool"))
    env.define("Queue", BuiltinFunction(lambda maxsize=0: Queue(maxsize), "Queue"))
    env.define("parallel", BuiltinFunction(lambda func, iterable, max_workers=4, mode="thread": parallel(func, iterable, max_workers, mode), "parallel"))
    env.define("sleep", BuiltinFunction(lambda sec: sleep(sec), "sleep"))