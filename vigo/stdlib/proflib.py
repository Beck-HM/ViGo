"""ViGo Standard Library: Performance Profiling (proflib)
Function-level and block-level profiling for AI script optimization.
Pure Python stdlib — zero external dependencies.
"""
import time
import sys
import tracemalloc
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


class ProfileResult:
    def __init__(self, cpu_time, wall_time, memory_peak, calls):
        self.cpu_time = cpu_time
        self.wall_time = wall_time
        self.memory_peak = memory_peak
        self.calls = calls
    
    def to_dict(self):
        return {
            "cpu_time": self.cpu_time,
            "wall_time": self.wall_time,
            "memory_peak": self.memory_peak,
            "calls": self.calls,
        }


class Profiler:
    def __init__(self):
        self._start_time = None
        self._start_cpu = None
        self._memory_snapshots = []
        self._running = False
    
    def start(self):
        self._start_time = time.time()
        self._start_cpu = time.process_time()
        self._memory_snapshots = []
        tracemalloc.start()
        self._running = True
        return True
    
    def stop(self):
        if not self._running:
            return {"wall_time": 0, "cpu_time": 0, "memory_peak": 0, "calls": 0}
        wall_time = time.time() - self._start_time
        cpu_time = time.process_time() - self._start_cpu
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self._running = False
        return {
            "wall_time": round(wall_time, 6),
            "cpu_time": round(cpu_time, 6),
            "memory_peak": peak,
            "calls": 1,
        }
    
    def report(self):
        """Return a detailed report dict."""
        if self._running:
            current, peak = tracemalloc.get_traced_memory()
            wall_elapsed = time.time() - self._start_time
            cpu_elapsed = time.process_time() - self._start_cpu
            return {
                "running": True,
                "wall_elapsed": round(wall_elapsed, 6),
                "cpu_elapsed": round(cpu_elapsed, 6),
                "memory_current": current,
                "memory_peak": peak,
            }
        return {"running": False}


def profile(func, *args, **kwargs):
    """Profile a single function call. Returns ProfileResult."""
    profiler = Profiler()
    profiler.start()
    try:
        func(*args, **kwargs)
    except Exception:
        pass
    return profiler.stop()


def benchmark(func, *args, **kwargs):
    """Time a function call. Returns wall time in seconds."""
    start = time.perf_counter()
    func(*args, **kwargs)
    return time.perf_counter() - start


def register(env):
    env.define("Profiler", BuiltinFunction(lambda: Profiler(), "Profiler"))
    env.define("profile", BuiltinFunction(lambda func: profile(func), "profile"))
    env.define("benchmark", BuiltinFunction(lambda func: benchmark(func), "benchmark"))