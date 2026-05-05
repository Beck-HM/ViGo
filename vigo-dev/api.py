"""
ViGo Dev API - Backend bridge between frontend JS and ViGo engine.
Exposes methods callable from JavaScript via pywebview.api.*
"""
import os
import sys
import json
import subprocess
import time
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(APP_DIR))

from vigo.runtime.interpreter import Interpreter
from vigo.lexer.lexer import Lexer
from vigo.parser.parser import Parser


class Api:
    """API exposed to JavaScript via PyWebView JS Bridge."""

    def __init__(self):
        self.vigo_root = os.path.dirname(APP_DIR)
        self.projects_dir = os.path.join(APP_DIR, "Projects")
        self.models_dir = os.path.join(APP_DIR, "models")
        self.config_path = os.path.join(APP_DIR, ".vigo_config.json")
        self.current_file = None
        self.current_project = None
        self.project_root = None
        self.current_model = "gemma-4b"
        self.current_provider = "ollama"
        self.interp = Interpreter(source_file="<vigo-dev>")
        self._model_registry = {"local": [], "cloud": []}
        os.makedirs(self.projects_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
        self._load_config()

    # ═══════════════════════════════════════
    #  Config
    # ═══════════════════════════════════════

    def _load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                last_project = config.get("last_project")
                if last_project:
                    project_path = os.path.join(self.projects_dir, last_project)
                    if os.path.exists(project_path):
                        self.current_project = last_project
                        self.project_root = project_path
                self.current_model = config.get("last_model", "gemma-4b")
                self.current_provider = config.get("last_provider", "ollama")
        except Exception:
            pass

    def _save_config(self):
        try:
            config = {
                "last_project": self.current_project,
                "last_model": self.current_model,
                "last_provider": self.current_provider,
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass

    # ═══════════════════════════════════════
    #  Project Management
    # ═══════════════════════════════════════

    def list_projects(self):
        projects = []
        if os.path.exists(self.projects_dir):
            for name in sorted(os.listdir(self.projects_dir)):
                full = os.path.join(self.projects_dir, name)
                if os.path.isdir(full) and not name.startswith("."):
                    projects.append({"name": name, "path": full})
        
        last_file = None
        if self.current_project:
            last_file = self._load_project_config()
        
        return json.dumps({
            "projects": projects,
            "current": self.current_project,
            "last_file": last_file or "",
        })

    def create_project(self, name):
        safe_name = name.strip().replace(" ", "-")
        if not safe_name:
            return json.dumps({"status": "error", "message": "Project name cannot be empty."})
        project_path = os.path.join(self.projects_dir, safe_name)
        if os.path.exists(project_path):
            return json.dumps({"status": "error", "message": f"Project '{safe_name}' already exists."})
        try:
            os.makedirs(project_path, exist_ok=True)
            skeleton = f'// {safe_name} - ViGo Project\n\nprint("Hello from {safe_name}!")\n'
            with open(os.path.join(project_path, "main.vigo"), "w", encoding="utf-8") as f:
                f.write(skeleton)
            self.current_project = safe_name
            self.project_root = project_path
            self.current_file = "main.vigo"
            self._save_config()
            self._save_project_config()
            return json.dumps({"status": "ok", "name": safe_name, "last_file": "main.vigo"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def open_project(self, name):
        project_path = os.path.join(self.projects_dir, name)
        if not os.path.exists(project_path):
            return json.dumps({"status": "error", "message": f"Project '{name}' not found."})
        self.current_project = name
        self.project_root = project_path
        self.current_file = None
        self._save_config()
        last_file = self._load_project_config()
        return json.dumps({"status": "ok", "name": name, "last_file": last_file or ""})

    def close_project(self):
        """Close the current project."""
        self.current_project = None
        self.project_root = None
        self.current_file = None
        self._save_config()
        return json.dumps({"status": "ok"})

    def import_project(self, name, source_path):
        safe_name = name.strip().replace(" ", "-")
        if not safe_name:
            return json.dumps({"status": "error", "message": "Project name cannot be empty."})
        if not os.path.exists(source_path):
            return json.dumps({"status": "error", "message": f"Source path not found: {source_path}"})
        project_path = os.path.join(self.projects_dir, safe_name)
        if os.path.exists(project_path):
            self.current_project = safe_name
            self.project_root = project_path
            self._save_config()
            last_file = self._load_project_config()
            return json.dumps({"status": "ok", "name": safe_name, "exists": True, "last_file": last_file or ""})
        try:
            if sys.platform == "win32":
                subprocess.run(["mklink", "/D", project_path, source_path], shell=True, check=True)
            else:
                os.symlink(source_path, project_path)
            self.current_project = safe_name
            self.project_root = project_path
            self._save_config()
            last_file = self._load_project_config()
            return json.dumps({"status": "ok", "name": safe_name, "last_file": last_file or ""})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def create_file(self, dir_path, name):
        if not self.project_root:
            return json.dumps({"status": "error", "message": "No project open."})
        if "." not in name:
            name += ".vigo"
        full_path = os.path.join(self.project_root, dir_path or "", name)
        if os.path.exists(full_path):
            return json.dumps({"status": "error", "message": f"'{name}' already exists."})
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write("")
            return json.dumps({"status": "ok", "name": name, "path": os.path.relpath(full_path, self.project_root)})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def create_folder(self, dir_path, name):
        """Create a new folder in the given directory."""
        if not self.project_root:
            return json.dumps({"status": "error", "message": "No project open."})
        full_path = os.path.join(self.project_root, dir_path or "", name)
        if os.path.exists(full_path):
            return json.dumps({"status": "error", "message": f"'{name}' already exists."})
        try:
            os.makedirs(full_path)
            return json.dumps({"status": "ok", "name": name})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def delete_item(self, path):
        """Delete a file or folder."""
        if not self.project_root:
            return json.dumps({"status": "error", "message": "No project open."})
        full_path = os.path.join(self.project_root, path)
        if not os.path.exists(full_path):
            return json.dumps({"status": "error", "message": "Not found."})
        try:
            if os.path.isdir(full_path):
                import shutil
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)
            if self.current_file and self.current_file.startswith(path):
                self.current_file = None
            return json.dumps({"status": "ok"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def rename_item(self, path, new_name):
        if not self.project_root:
            return json.dumps({"status": "error", "message": "No project open."})
        full_path = os.path.join(self.project_root, path)
        if not os.path.exists(full_path):
            return json.dumps({"status": "error", "message": "Not found."})
        # Preserve original extension unless user explicitly provided one
        name, old_ext = os.path.splitext(os.path.basename(path))
        new_name_clean, new_ext = os.path.splitext(new_name)
        if not new_ext:
            new_name = new_name_clean + old_ext
        parent_dir = os.path.dirname(full_path)
        new_path = os.path.join(parent_dir, new_name)
        if os.path.exists(new_path):
            return json.dumps({"status": "error", "message": f"'{new_name}' already exists."})
        try:
            os.rename(full_path, new_path)
            if self.current_file and self.current_file.startswith(path):
                self.current_file = os.path.relpath(new_path, self.project_root)
            return json.dumps({"status": "ok", "new_name": new_name, "new_path": os.path.relpath(new_path, self.project_root)})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    # ═══════════════════════════════════════
    #  File Operations
    # ═══════════════════════════════════════

    def get_dir_children(self, dir_path):
        """Lazy-load children of a directory."""
        if not self.project_root:
            return json.dumps([])
        full_path = os.path.join(self.project_root, dir_path or "")
        if not os.path.exists(full_path):
            return json.dumps([])
        items = self._scan_dir_flat(full_path)
        return json.dumps(items)

    def _scan_dir_flat(self, path):
        """Scan a single directory level without recursion."""
        result = []
        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            return []

        skip_dirs = {"__pycache__", ".git", "dist", "build", "node_modules", ".vigo_memory", ".vigo_chromadb"}

        for item in entries:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                if item in skip_dirs or item.startswith("."):
                    continue
                result.append({
                    "name": item,
                    "path": os.path.relpath(full_path, self.project_root),
                    "type": "dir",
                    "children": []  # empty placeholder, loaded on expand
                })
            else:
                ext = os.path.splitext(item)[1]
                if item.startswith(".") or ext in (".exe", ".dll", ".pyd", ".pyc", ".ico", ".db", ".zip", ".png", ".jpg"):
                    pass
                elif item.endswith(".vigo_backup"):
                    pass
                else:
                    result.append({
                        "name": item,
                        "path": os.path.relpath(full_path, self.project_root),
                        "type": "file",
                        "ext": ext,
                    })
        return result

    def get_file_tree(self):
        if not self.project_root:
            return json.dumps([])
        return self.get_dir_children("")  # root level only

    def _scan_dir(self, path, max_depth, current_depth=0):
        if current_depth > max_depth:
            return None
        result = []
        try:
            items = sorted(os.listdir(path))
        except PermissionError:
            return []

        skip_dirs = {"__pycache__", ".git", "dist", "build", "node_modules",
                     ".vigo_memory", ".vigo_chromadb"}

        for item in items:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                if item in skip_dirs or item.startswith("."):
                    continue
                children = self._scan_dir(full_path, max_depth, current_depth + 1)
                result.append({
                    "name": item, "path": os.path.relpath(full_path, self.project_root),
                    "type": "dir", "children": children or []
                })
            else:
                ext = os.path.splitext(item)[1]
                # Skip obvious binary and hidden files
                if item.startswith(".") or ext in (".exe", ".dll", ".pyd", ".pyc", ".ico", ".db", ".zip", ".png", ".jpg"):
                    pass
                else:
                    result.append({
                        "name": item, "path": os.path.relpath(full_path, self.project_root),
                        "type": "file", "ext": ext,
                    })
        return result

    def read_file(self, filepath):
        if not self.project_root:
            return "// No project open."
        full_path = os.path.join(self.project_root, filepath)
        if not os.path.exists(full_path):
            return f"// File not found: {filepath}"
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.current_file = filepath
            self._save_project_config()  # remember last opened file
            return content
        except Exception as e:
            return f"// Error: {e}"

    def _project_config_path(self):
        """Return path to project-level config file."""
        if not self.project_root:
            return None
        return os.path.join(self.project_root, ".vigo_project.json")

    def _save_project_config(self):
        """Save project-level config (last opened file)."""
        path = self._project_config_path()
        if not path:
            return
        config = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                pass
        config["last_file"] = self.current_file
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass

    def _load_project_config(self):
        """Load project-level config and return last opened file."""
        path = self._project_config_path()
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config.get("last_file")
        except Exception:
            return None

    def save_file(self, filepath, content):
        if not self.project_root:
            return json.dumps({"status": "error", "message": "No project open."})
        full_path = os.path.join(self.project_root, filepath)
        if os.path.exists(full_path):
            backup_path = full_path + ".vigo_backup"
            try:
                with open(full_path, "r", encoding="utf-8") as src:
                    with open(backup_path, "w", encoding="utf-8") as dst:
                        dst.write(src.read())
            except Exception:
                pass
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return json.dumps({"status": "ok", "path": filepath})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def get_current_file(self):
        return self.current_file or ""

    # ═══════════════════════════════════════
    #  Model Management
    # ═══════════════════════════════════════

    def _load_models(self):
        models = {"local": [], "cloud": []}
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if parts:
                    name = parts[0].replace(":latest", "")
                    models["local"].append({
                        "id": name, "name": name, "provider": "ollama", "source": "local",
                    })
        except Exception:
            pass

        if os.path.exists(self.models_dir):
            for filename in sorted(os.listdir(self.models_dir)):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(self.models_dir, filename), "r", encoding="utf-8") as f:
                            config = json.load(f)
                            if isinstance(config, dict):
                                config["source"] = "cloud"
                                config["id"] = config.get("id", filename[:-5])
                                models["cloud"].append(config)
                    except Exception:
                        pass
        return models

    def list_models(self):
        """Return all available models. Loads from Ollama on first call."""
        if not self._model_registry["local"] and not self._model_registry["cloud"]:
            self._model_registry = self._load_models()
        all_models = self._model_registry["local"] + self._model_registry["cloud"]
        return json.dumps(all_models)

    def set_model(self, model_id, provider):
        self.current_model = model_id
        self.current_provider = provider
        self._save_config()
        return json.dumps({"status": "ok", "model": model_id, "provider": provider})

    # ═══════════════════════════════════════
    #  AI Operations
    # ═══════════════════════════════════════

    def ask_ai(self, message):
        try:
            model = self.current_model
            provider = self.current_provider
            start_time = time.time()

            if provider == "ollama":
                import threading
                result_container = {}

                def call_ollama(prompt_text):
                    try:
                        data = json.dumps({
                            "model": model,
                            "prompt": str(prompt_text),
                            "stream": True,
                        }).encode('utf-8')
                        req = urllib.request.Request(
                            "http://localhost:11434/api/generate",
                            data=data,
                            headers={"Content-Type": "application/json"}
                        )
                        chunks = []
                        with urllib.request.urlopen(req, timeout=120) as resp:
                            buffer = ""
                            while True:
                                byte = resp.read(1)
                                if not byte: break
                                buffer += byte.decode('utf-8', errors='ignore')
                                while "\n" in buffer:
                                    line, buffer = buffer.split("\n", 1)
                                    line = line.strip()
                                    if line:
                                        try:
                                            obj = json.loads(line)
                                            chunk = obj.get("response", "")
                                            if chunk: chunks.append(chunk)
                                            if obj.get("done", False): break
                                        except json.JSONDecodeError: pass
                        result_container['text'] = "".join(chunks)
                        result_container['chunks'] = chunks
                    except Exception as e:
                        result_container['error'] = str(e)

                prompt = f"""You are a helpful AI coding assistant. You have access to one tool:

read_file(path) - returns the content of the file at the given path in the current project.

To use it, reply with ONLY this line and nothing else:
READ: <file path>

If you don't need to read a file, just answer normally.
Current open file: {self.current_file or 'none'}
Put any code in ```language ...``` blocks.

User: {message}"""

                t = threading.Thread(target=call_ollama, args=(prompt,))
                t.start()
                t.join(timeout=120)

                if 'error' in result_container:
                    return json.dumps({"status": "error", "response": f"Error: {result_container['error']}"})

                text = result_container.get('text', '')
                chunks = result_container.get('chunks', [])

                # Check if AI requests a file read
                if text.strip().startswith("READ:") and "\n" not in text.strip():
                    file_path = text.strip()[5:].strip()
                    file_content = self._read_project_file(file_path)
                    # Second call with file content
                    followup = f"""File content of {file_path}:

{file_content}

Now provide your final answer to the original question: {message}

Put any code in ```language ...``` blocks."""
                    result_container2 = {}
                    def call_ollama2():
                        try:
                            data = json.dumps({"model": model, "prompt": followup, "stream": True}).encode('utf-8')
                            req = urllib.request.Request("http://localhost:11434/api/generate", data=data, headers={"Content-Type": "application/json"})
                            chunks2 = []
                            with urllib.request.urlopen(req, timeout=120) as resp:
                                buffer = ""
                                while True:
                                    byte = resp.read(1)
                                    if not byte: break
                                    buffer += byte.decode('utf-8', errors='ignore')
                                    while "\n" in buffer:
                                        line, buffer = buffer.split("\n", 1)
                                        line = line.strip()
                                        if line:
                                            try:
                                                obj = json.loads(line)
                                                chunk = obj.get("response", "")
                                                if chunk: chunks2.append(chunk)
                                                if obj.get("done", False): break
                                            except json.JSONDecodeError: pass
                            result_container2['text'] = "".join(chunks2)
                            result_container2['chunks'] = chunks2
                        except Exception as e:
                            result_container2['error'] = str(e)
                    t2 = threading.Thread(target=call_ollama2)
                    t2.start()
                    t2.join(timeout=120)
                    text = result_container2.get('text', text)
                    chunks = result_container2.get('chunks', chunks)
            else:
                text = ""
                chunks = []

            if text:
                import re
                if "done thinking." in text:
                    text = text.split("done thinking.")[-1].strip()
                text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
                if len(text) > 3000:
                    text = text[:3000]

            elapsed = round(time.time() - start_time, 1)

            if text:
                if not chunks:
                    chunks = [text[i:i+3] for i in range(0, len(text), 3)]
                return json.dumps({
                    "status": "ok",
                    "response": text.strip(),
                    "elapsed": elapsed,
                    "chunks": chunks,
                })
            return json.dumps({"status": "error", "response": "No response.", "elapsed": elapsed})
        except Exception as e:
            return json.dumps({"status": "error", "response": f"Error: {e}", "elapsed": 0})

    def _read_project_file(self, path):
        if not self.project_root:
            return "Error: No project open."
        full_path = os.path.join(self.project_root, path.strip())
        if not os.path.exists(full_path):
            return f"Error: File not found: {path}"
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()[:3000]
        except Exception as e:
            return f"Error reading file: {e}"

    def _read_project_file(self, path):
        """Read a file from the current project for AI tool use."""
        if not self.project_root:
            return "Error: No project open."
        full_path = os.path.join(self.project_root, path.strip())
        if not os.path.exists(full_path):
            return f"Error: File not found: {path}"
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()[:3000]
        except Exception as e:
            return f"Error reading file: {e}"

    def _write_project_file(self, path, content):
        if not self.project_root:
            return "Error: No project open."
        full_path = os.path.join(self.project_root, path.strip())
        if not os.path.exists(full_path):
            return f"Error: File not found: {path}"
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return "OK"
        except Exception as e:
            return f"Error: {e}"

    def _create_project_file(self, path, content):
        if not self.project_root:
            return "Error: No project open."
        full_path = os.path.join(self.project_root, path.strip())
        if os.path.exists(full_path):
            return f"Error: File already exists: {path}"
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return "OK"
        except Exception as e:
            return f"Error: {e}"

    # ═══════════════════════════════════════
    #  Memory Operations
    # ═══════════════════════════════════════

    def mem_save(self, key, content):
        try:
            vigo_code = f'mem_save("{self._escape(key)}", "{self._escape(content)}")'
            self._run_vigo(vigo_code)
            return json.dumps({"status": "ok"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def mem_search(self, query, limit=5):
        try:
            vigo_code = f'memories = mem_recall("{self._escape(query)}", {limit})'
            self._run_vigo(vigo_code)
            memories = self.interp.global_env.variables.get("memories", [])
            results = []
            for m in memories:
                results.append({
                    "key": m.get("key", ""),
                    "value": str(m.get("value", ""))[:200],
                    "similarity": m.get("similarity", 0),
                })
            return json.dumps(results)
        except Exception:
            return json.dumps([])

    def mem_snapshot(self):
        try:
            self._run_vigo("snap = mem_snapshot()")
            snap = self.interp.global_env.variables.get("snap", {})
            return json.dumps(snap)
        except Exception:
            return json.dumps({"total": 0, "chromadb": False})

    # ═══════════════════════════════════════
    #  Testing
    # ═══════════════════════════════════════

    def run_test(self):
        try:
            result = subprocess.run(
                ["python", "main.py", "tests/test_regression_v36.vigo"],
                cwd=self.vigo_root,
                capture_output=True, text=True, timeout=120,
            )
            return json.dumps({
                "status": "ok" if result.returncode == 0 else "fail",
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-500:],
            })
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def run_vigo_file(self, path):
        """Execute a .vigo file and return its output."""
        if not self.project_root:
            return json.dumps({"status": "error", "output": "No project open."})
        full_path = os.path.join(self.project_root, path)
        if not os.path.exists(full_path):
            return json.dumps({"status": "error", "output": f"File not found: {path}"})
        try:
            result = subprocess.run(
                ["python", "main.py", full_path],
                cwd=self.vigo_root,
                capture_output=True, text=True, timeout=30,
            )
            output = result.stdout
            if result.stderr:
                output += "\n" + result.stderr
            return json.dumps({"status": "ok" if result.returncode == 0 else "error", "output": output.strip() or "(no output)"})
        except subprocess.TimeoutExpired:
            return json.dumps({"status": "error", "output": "Execution timed out (30s)."})
        except Exception as e:
            return json.dumps({"status": "error", "output": str(e)})

    # ═══════════════════════════════════════
    #  Utility
    # ═══════════════════════════════════════

    def _run_vigo(self, code):
        lexer = Lexer(code)
        parser = Parser(lexer)
        ast = parser.parse_program()
        return self.interp.interpret(ast)

    def _escape(self, text):
        return str(text).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")