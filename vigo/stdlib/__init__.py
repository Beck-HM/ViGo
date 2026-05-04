"""ViGo Standard Library - Auto-discovery loader"""
import os
import importlib


def register_all(env):
    """Auto-discover and register all *lib.py modules in this directory."""
    stdlib_dir = os.path.dirname(os.path.abspath(__file__))
    for filename in sorted(os.listdir(stdlib_dir)):
        if filename.endswith('lib.py') and filename != '__init__.py':
            module_name = filename[:-3]  # remove .py
            try:
                mod = importlib.import_module(f'.{module_name}', package='vigo.stdlib')
                if hasattr(mod, 'register'):
                    mod.register(env)
            except Exception:
                pass  # Skip modules that fail to load