"""ViGo Standard Library - Auto-discovery loader"""
import os
import importlib


def register_all(env):
    """Auto-discover and register all *lib.py modules in this directory and subdirectories."""
    stdlib_dir = os.path.dirname(os.path.abspath(__file__))
    for root, dirs, files in os.walk(stdlib_dir):
        # Skip __pycache__ and other hidden dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and not d.startswith('__')]
        for filename in sorted(files):
            if filename.endswith('lib.py') and filename != '__init__.py':
                # Build module path relative to stdlib
                rel_path = os.path.relpath(os.path.join(root, filename), stdlib_dir)
                module_name = rel_path[:-3].replace(os.sep, '.')  # remove .py, convert / to .
                try:
                    mod = importlib.import_module(f'.{module_name}', package='vigo.stdlib')
                    if hasattr(mod, 'register'):
                        mod.register(env)
                except Exception:
                    pass  # Skip modules that fail to load