"""ViGo Sandbox - Isolated code execution environment."""
import json
import subprocess
import os
import sys
import time
from ...runtime.objects import BuiltinFunction
from ...runtime.errors import ViGoError


class SandboxConfig:
    def __init__(self, allowed_dirs=None, allowed_hosts=None, max_cpu=10,
                 max_memory=512, timeout=30, max_steps=10000):
        self.allowed_dirs = allowed_dirs or [os.getcwd()]
        self.allowed_hosts = allowed_hosts or []
        self.max_cpu = max_cpu
        self.max_memory = max_memory
        self.timeout = timeout
        self.max_steps = max_steps
    
    def to_dict(self):
        return {
            "allowed_dirs": self.allowed_dirs,
            "allowed_hosts": self.allowed_hosts,
            "max_cpu": self.max_cpu,
            "max_memory": self.max_memory,
            "timeout": self.timeout,
            "max_steps": self.max_steps,
        }


class SandboxResult:
    def __init__(self, data):
        self.status = data.get("status", "error")
        self.stdout = data.get("stdout", "")
        self.stderr = data.get("stderr", "")
        self.exception = data.get("exception")
        self.exception_type = data.get("exception_type")
        self.cpu_time = data.get("cpu_time", 0)
        self.peak_memory = data.get("peak_memory", 0)
        self.duration_ms = data.get("duration_ms", 0)
    
    def to_dict(self):
        return {
            "status": self.status,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exception": self.exception,
            "exception_type": self.exception_type,
            "cpu_time": self.cpu_time,
            "peak_memory": self.peak_memory,
            "duration_ms": self.duration_ms,
        }


def sandbox_run(code, config=None):
    """Execute code in an isolated sandbox."""
    if config is None:
        config = SandboxConfig()
    elif isinstance(config, dict):
        config = SandboxConfig(**config)
    
    config_dict = config.to_dict()
    config_json = json.dumps(config_dict)
    
    child_code = f"""
import sys, json
sys.path.insert(0, {repr(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))})
config_json = {repr(config_json)}
code = {repr(code)}

from vigo.stdlib.sandbox.protocol import run_in_child
run_in_child(config_json, code)
"""
    
    try:
        proc = subprocess.Popen(
            [sys.executable, "-c", child_code],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        try:
            stdout, stderr = proc.communicate(timeout=config.timeout + 5)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            return SandboxResult({
                "status": "timeout",
                "exception": "Execution timed out (parent watchdog)",
                "duration_ms": config.timeout * 1000,
            })
        
        # Try reading result from temp file first
        if "__VIGO_SANDBOX_RESULT__" in stdout:
            lines = stdout.split("\n")
            for i, line in enumerate(lines):
                if line.strip() == "__VIGO_SANDBOX_RESULT__" and i + 1 < len(lines):
                    result_file = lines[i + 1].strip()
                    if os.path.exists(result_file):
                        try:
                            with open(result_file, 'r') as f:
                                result_data = json.load(f)
                            os.unlink(result_file)
                            return SandboxResult(result_data)
                        except Exception:
                            pass
        
        # Fallback: inline JSON (old format)
        if "__VIGO_SANDBOX_RESULT__" in stdout:
            start = stdout.index("__VIGO_SANDBOX_RESULT__") + len("__VIGO_SANDBOX_RESULT__")
            end = stdout.index("__VIGO_SANDBOX_END__") if "__VIGO_SANDBOX_END__" in stdout else len(stdout)
            result_json = stdout[start:end].strip()
            try:
                result_data = json.loads(result_json)
                return SandboxResult(result_data)
            except json.JSONDecodeError:
                pass
        
        return SandboxResult({
            "status": "error",
            "stdout": stdout,
            "stderr": stderr,
            "exception": "Failed to parse sandbox result",
        })
    
    except Exception as e:
        return SandboxResult({
            "status": "error",
            "exception": str(e),
            "exception_type": type(e).__name__,
        })


def register(env):
    env.define("sandbox_run", BuiltinFunction(
        lambda code, config=None: sandbox_run(code, config).to_dict(),
        "sandbox_run"))