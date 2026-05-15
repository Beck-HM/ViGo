"""ViGo Sandbox - Parent-child process communication protocol."""
import json
import time
import os
import sys
import traceback
import tempfile

try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False

from .restricted_builtins import build_restricted_globals


def run_in_child(config_json, code):
    """Execute code in a child process. Called via subprocess.
    Writes result to a temp file to avoid stdout capture issues.
    """
    config = json.loads(config_json)
    
    start_time = time.time()
    cpu_start = time.process_time()
    
    result = {
        "status": "success",
        "stdout": "",
        "stderr": "",
        "exception": None,
        "exception_type": None,
        "cpu_time": 0,
        "peak_memory": 0,
        "duration_ms": 0,
    }
    
    result_file = os.path.join(tempfile.gettempdir(), f"vigo_sandbox_result_{os.getpid()}.json")
    
    try:
        if HAS_RESOURCE:
            max_cpu = config.get("max_cpu", 0)
            max_memory = config.get("max_memory", 0)
            if max_cpu > 0:
                resource.setrlimit(resource.RLIMIT_CPU, (max_cpu, max_cpu))
            if max_memory > 0:
                mem_bytes = max_memory * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        
        timeout = config.get("timeout", 0)
        if timeout > 0:
            import threading
            def timeout_handler():
                time.sleep(timeout)
                os._exit(1)
            watchdog = threading.Thread(target=timeout_handler, daemon=True)
            watchdog.start()
        
        restricted_globals = build_restricted_globals(
            allowed_dirs=config.get("allowed_dirs"),
            allowed_hosts=config.get("allowed_hosts"),
            max_steps=config.get("max_steps"),
        )
        
        import io
        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = captured_stdout
        sys.stderr = captured_stderr
        
        try:
            if config.get("max_steps", 0) > 0:
                code = f"_check_step()\n{code}"
            exec(code, restricted_globals)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        
        result["stdout"] = captured_stdout.getvalue()
        result["stderr"] = captured_stderr.getvalue()
        
    except Exception as e:
        result["status"] = "error"
        result["exception"] = str(e)
        result["exception_type"] = type(e).__name__
        result["stderr"] = traceback.format_exc()
    except MemoryError:
        result["status"] = "error"
        result["exception"] = "Memory limit exceeded"
        result["exception_type"] = "MemoryError"
    except SystemExit:
        result["status"] = "timeout"
        result["exception"] = "Execution timed out"
    
    result["cpu_time"] = time.process_time() - cpu_start
    result["duration_ms"] = (time.time() - start_time) * 1000
    
    if HAS_RESOURCE:
        try:
            result["peak_memory"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        except Exception:
            pass
    
    try:
        with open(result_file, 'w') as f:
            json.dump(result, f)
    except Exception:
        pass
    
    print("__VIGO_SANDBOX_RESULT__")
    print(result_file)
    print("__VIGO_SANDBOX_END__")