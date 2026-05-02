"""ViGo Workflow Library - DAG Executor"""
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


class WorkflowEngine:
    def __init__(self):
        self.steps = {}
        self.dependencies = {}
        self.results = {}

    def add_step(self, name, func, depends_on=None):
        self.steps[name] = func
        if depends_on:
            deps = [d.strip() for d in depends_on.split(",")]
            self.dependencies[name] = deps
        else:
            self.dependencies[name] = []
        return name

    def run(self):
        completed = set()
        self.results = {}
        while len(completed) < len(self.steps):
            progress = False
            for name, func in self.steps.items():
                if name in completed: continue
                deps = self.dependencies.get(name, [])
                if all(d in completed for d in deps):
                    try:
                        # Try calling directly, then try .func if BuiltinFunction
                        if hasattr(func, 'func'):
                            result = func.func()
                        elif callable(func):
                            result = func()
                        else:
                            result = str(func)
                        self.results[name] = str(result)
                        completed.add(name)
                        progress = True
                    except Exception as e:
                        self.results[name] = f"Error: {e}"
                        completed.add(name)
                        progress = True
            if not progress:
                break
        return self.results

    def get_result(self, name):
        return self.results.get(name, "Not executed")

    def get_all_results(self):
        return self.results

    def reset(self):
        self.steps = {}
        self.dependencies = {}
        self.results = {}
        return True


_wf = WorkflowEngine()


def register(env):
    env.define('wf_add_step', BuiltinFunction(
        lambda name, func, deps=None: _wf.add_step(name, func, deps),
        'wf_add_step'))
    env.define('wf_run', BuiltinFunction(
        lambda: _wf.run() and _wf.get_all_results(),
        'wf_run'))
    env.define('wf_result', BuiltinFunction(
        lambda name: _wf.get_result(name),
        'wf_result'))
    env.define('wf_reset', BuiltinFunction(
        lambda: _wf.reset(),
        'wf_reset'))