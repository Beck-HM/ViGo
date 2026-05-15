"""ViGo CLI - Command line interface with package management"""
import sys
import os
from .runtime.interpreter import Interpreter
from .lexer.lexer import Lexer
from .parser.parser import Parser
from .runtime.errors import ViGoError, ReturnException, AwaitException
from .bytecode.compiler import BytecodeCompiler
from .bytecode.vm import VirtualMachine


LOGO = r'''
╔══════════════════════════════════════╗
║   __      ___ ___  ___               ║
║   \ \    / (_) __|/ _ \              ║
║    \ \/\/ /| | (_ | (_) |            ║
║     \_/\_/ |_|\___|\___/             ║
║                                      ║
║   ViGo v3.7 · Bytecode Launch        ║
╚══════════════════════════════════════╝
'''


def _get_packages_dir():
    """Return the cross-platform packages directory."""
    if os.name == 'nt':  # Windows
        base = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        return os.path.join(base, 'ViGo', 'packages')
    else:  # Linux / macOS
        return os.path.join(os.path.expanduser('~'), '.vigo', 'packages')


def _read_file_safe(filepath):
    """Read a file with automatic encoding detection."""
    with open(filepath, 'rb') as f:
        raw = f.read()
    if raw[:3] == b'\xef\xbb\xbf':
        raw = raw[3:]
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        pass
    try:
        return raw.decode('gbk')
    except UnicodeDecodeError:
        pass
    return raw.decode('latin-1')


def run_file(filepath, use_bytecode=False):
    """Execute a ViGo source file."""
    source = _read_file_safe(filepath)
    if use_bytecode:
        lexer = Lexer(source)
        parser = Parser(lexer)
        ast = parser.parse_program()
        compiler = BytecodeCompiler()
        bc = compiler.compile(ast)
        vm = VirtualMachine()
        vm.load(bc)
        return vm.run()
    else:
        interp = Interpreter(source_file=filepath)
        ast = Parser(Lexer(source)).parse_program()
        return interp.interpret(ast)


def cmd_run(args):
    """Run a ViGo script."""
    use_bytecode = '--bytecode' in args
    filepath = None
    for a in args:
        if not a.startswith('--'):
            filepath = a
            break
    if not filepath:
        print("Usage: vigo run <file.vigo> [--bytecode]")
        return
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        return
    print(LOGO)
    try:
        result = run_file(filepath, use_bytecode)
        if result is not None:
            print(f"Result: {result}")
    except ViGoError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def cmd_build(args):
    """Transpile a ViGo script to Python."""
    filepath = None
    for a in args:
        if not a.startswith('--'):
            filepath = a
            break
    if not filepath:
        print("Usage: vigo build <file.vigo>")
        return
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        return
    source = _read_file_safe(filepath)
    from .transpiler.transpiler import transpile
    py_code = transpile(source)
    out_path = filepath.rsplit('.', 1)[0] + '.py'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(py_code)
    print(f"Transpiled: {out_path}")


def cmd_install(args):
    """Install a package."""
    if not args:
        print("Usage: vigo install <package-name>")
        print("       vigo install <file.vigo-pkg>")
        return
    target = args[0]
    if target.endswith('.vigo-pkg'):
        _install_from_file(target)
    else:
        _install_from_registry(target)


def _install_from_registry(name):
    """Download and install a package from the registry."""
    import urllib.request
    import json
    import tempfile
    import zipfile
    import shutil

    registry_url = "https://raw.githubusercontent.com/Beck-HM/ViGo-Registry/main/registry.json"
    packages_dir = _get_packages_dir()

    print(f"Looking up package: {name}")
    try:
        resp = urllib.request.urlopen(registry_url, timeout=10)
        registry = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: Cannot access registry: {e}")
        return

    pkg_info = registry.get("packages", {}).get(name)
    if not pkg_info:
        print(f"Error: Package '{name}' not found in registry")
        print("Available packages:")
        for p in registry.get("packages", {}):
            print(f"  - {p}")
        return

    download_url = f"https://github.com/{pkg_info['repo']}/releases/latest/download/{name}.vigo-pkg"
    print(f"Downloading {name} v{pkg_info['latest']}...")

    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.vigo-pkg')
        urllib.request.urlretrieve(download_url, tmp.name)
    except Exception as e:
        print(f"Error: Download failed: {e}")
        print(f"Make sure the package has a Release with {name}.vigo-pkg attached")
        return

    pkg_path = os.path.join(packages_dir, name)
    os.makedirs(pkg_path, exist_ok=True)

    try:
        with zipfile.ZipFile(tmp.name, 'r') as zf:
            zf.extractall(pkg_path)
        os.unlink(tmp.name)
    except Exception as e:
        print(f"Error: Failed to extract package: {e}")
        return

    pkg_json_path = os.path.join(pkg_path, "package.json")
    if os.path.exists(pkg_json_path):
        with open(pkg_json_path, 'r', encoding='utf-8') as f:
            pkg_data = json.load(f)
        deps = pkg_data.get("dependencies", {})
        if deps:
            print(f"Package {name} v{pkg_info['latest']} installed.")
            print("Missing dependencies (install manually):")
            for dep_name, dep_ver in deps.items():
                dep_dir = os.path.join(packages_dir, dep_name)
                if not os.path.exists(dep_dir):
                    print(f"  - {dep_name} {dep_ver}  (run: vigo install {dep_name})")
        else:
            print(f"Package {name} v{pkg_info['latest']} installed successfully.")
    else:
        print(f"Package {name} v{pkg_info['latest']} installed successfully.")


def _install_from_file(filepath):
    """Install a package from a local .vigo-pkg file."""
    import json
    import zipfile

    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        return

    packages_dir = _get_packages_dir()

    name = None
    with zipfile.ZipFile(filepath, 'r') as zf:
        if "package.json" in zf.namelist():
            data = json.loads(zf.read("package.json").decode('utf-8'))
            name = data.get("name")

    if not name:
        name = os.path.basename(filepath).replace('.vigo-pkg', '')
        print(f"Warning: No package.json found, using name: {name}")

    pkg_path = os.path.join(packages_dir, name)
    os.makedirs(pkg_path, exist_ok=True)

    with zipfile.ZipFile(filepath, 'r') as zf:
        zf.extractall(pkg_path)

    print(f"Package {name} installed from local file.")


def cmd_uninstall(args):
    """Uninstall a package."""
    if not args:
        print("Usage: vigo uninstall <package-name>")
        return
    name = args[0]
    packages_dir = _get_packages_dir()
    pkg_path = os.path.join(packages_dir, name)
    if not os.path.exists(pkg_path):
        print(f"Error: Package '{name}' is not installed")
        return
    import shutil
    shutil.rmtree(pkg_path)
    print(f"Package {name} uninstalled.")


def cmd_list(args):
    """List installed packages."""
    packages_dir = _get_packages_dir()
    if not os.path.exists(packages_dir):
        print("No packages installed.")
        return
    pkgs = os.listdir(packages_dir)
    if not pkgs:
        print("No packages installed.")
        return
    print("Installed packages:")
    for p in sorted(pkgs):
        pkg_json = os.path.join(packages_dir, p, "package.json")
        if os.path.exists(pkg_json):
            import json
            with open(pkg_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"  {p} v{data.get('version', '?')}")
        else:
            print(f"  {p}")


def cmd_publish(args):
    """Publish current directory as a package."""
    import json
    import zipfile

    if not os.path.exists("package.json"):
        print("Error: No package.json found in current directory.")
        print("Create a package.json with: name, version, description")
        return

    with open("package.json", 'r', encoding='utf-8') as f:
        pkg_data = json.load(f)

    name = pkg_data.get("name")
    version = pkg_data.get("version")
    if not name or not version:
        print("Error: package.json must have 'name' and 'version'")
        return

    pkg_file = f"{name}.vigo-pkg"
    with zipfile.ZipFile(pkg_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk("."):
            for file in files:
                if file == pkg_file or '__pycache__' in root:
                    continue
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, ".")
                zf.write(filepath, arcname)


def main():
    if len(sys.argv) < 2:
        try:
            from .repl import ViGoREPL
            repl = ViGoREPL()
            repl.run()
        except ImportError:
            print("REPL module not found. Please ensure vigo/repl.py exists.")
        return

    command = sys.argv[1].lower()
    args = sys.argv[2:]

    commands = {
        "run": cmd_run,
        "build": cmd_build,
        "install": cmd_install,
        "uninstall": cmd_uninstall,
        "list": cmd_list,
        "publish": cmd_publish,
    }

    if command in commands:
        commands[command](args)
    else:
        filepath = command
        if not os.path.exists(filepath):
            print(f"Error: Unknown command or file not found: {command}")
            print("Commands: run, build, install, uninstall, list, publish")
            return
        print(LOGO)
        try:
            result = run_file(filepath)
            if result is not None:
                print(f"Result: {result}")
        except ViGoError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == '__main__':
    main()