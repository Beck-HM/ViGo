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
import shutil
from datetime import datetime

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
    sys.path.insert(0, os.path.dirname(APP_DIR))
else:
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
        self.chat_sessions = {}  # chatId -> { history: [...], type: "master"|"worker", parentId: str|None }
        os.makedirs(self.projects_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
        self.settings = {
            "ollama_host": "http://localhost:11434",
            "timeout": 120,
            "font_size": 13,
            "theme": "vs-dark",
            "tab_size": 4,
            "word_wrap": True,
            "memory_mode": "auto",
            "auto_save_interval": 60,
            "f3_shortcut": "F3",
        }
        self._load_config()

    def _get_session(self, chatId):
        if chatId not in self.chat_sessions:
            self.chat_sessions[chatId] = {"history": [], "type": "master", "parentId": None, "model": self.current_model}
        return self.chat_sessions[chatId]

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
                self.settings["ollama_host"] = config.get("ollama_host", self.settings["ollama_host"])
                self.settings["timeout"] = config.get("timeout", self.settings["timeout"])
                self.settings["font_size"] = config.get("font_size", self.settings["font_size"])
                self.settings["theme"] = config.get("theme", self.settings["theme"])
                self.settings["tab_size"] = config.get("tab_size", self.settings["tab_size"])
                self.settings["word_wrap"] = config.get("word_wrap", self.settings["word_wrap"])
                self.settings["memory_mode"] = config.get("memory_mode", "auto")
                self.settings["auto_save_interval"] = config.get("auto_save_interval", self.settings["auto_save_interval"])
                self.settings["f3_shortcut"] = config.get("f3_shortcut", self.settings["f3_shortcut"])
        except Exception:
            pass

    def _save_config(self):
        try:
            config = {
                "last_project": self.current_project,
                "last_model": self.current_model,
                "last_provider": self.current_provider,
                "ollama_host": self.settings.get("ollama_host", "http://localhost:11434"),
                "timeout": self.settings.get("timeout", 120),
                "font_size": self.settings.get("font_size", 13),
                "theme": self.settings.get("theme", "vs-dark"),
                "tab_size": self.settings.get("tab_size", 4),
                "word_wrap": self.settings.get("word_wrap", True),
                "memory_mode": self.settings.get("memory_mode", "auto"),
                "auto_save_interval": self.settings.get("auto_save_interval", 60),
                "f3_shortcut": self.settings.get("f3_shortcut", "F3"),
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
        return json.dumps({"projects": projects, "current": self.current_project, "last_file": last_file or ""})

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
        return json.dumps({"status": "ok", "name": name, "last_file": last_file or "", "project_root": project_path})

    def close_project(self):
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
        if not self.project_root:
            return json.dumps({"status": "error", "message": "No project open."})
        full_path = os.path.join(self.project_root, path)
        if not os.path.exists(full_path):
            return json.dumps({"status": "error", "message": "Not found."})
        try:
            if os.path.isdir(full_path):
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
        if not self.project_root:
            return json.dumps([])
        full_path = os.path.join(self.project_root, dir_path or "")
        if not os.path.exists(full_path):
            return json.dumps([])
        return json.dumps(self._scan_dir_flat(full_path))

    def _scan_dir_flat(self, path):
        result = []
        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            return []
        skip_dirs = {"__pycache__", ".git", "dist", "build", "node_modules", ".vigo_memory", ".vigo_chromadb", ".vigo_backups"}
        for item in entries:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                if item in skip_dirs or item.startswith("."):
                    continue
                result.append({"name": item, "path": os.path.relpath(full_path, self.project_root), "type": "dir", "children": []})
            else:
                ext = os.path.splitext(item)[1]
                if item.startswith(".") or ext in (".exe", ".dll", ".pyd", ".pyc", ".ico", ".db", ".zip", ".png", ".jpg"):
                    pass
                elif item.endswith(".vigo_backup"):
                    pass
                else:
                    result.append({"name": item, "path": os.path.relpath(full_path, self.project_root), "type": "file", "ext": ext})
        return result

    def get_file_tree(self):
        if not self.project_root:
            return json.dumps([])
        return self.get_dir_children("")

    def read_file(self, filepath):
        if not self.project_root and not os.path.isabs(filepath):
            return "// No project open."
        # Support absolute paths (drag & drop)
        if os.path.isabs(filepath):
            full_path = filepath
        else:
            full_path = os.path.join(self.project_root or "", filepath)
        if not os.path.exists(full_path):
            return f"// File not found: {filepath}"
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            if not os.path.isabs(filepath):
                self.current_file = filepath
                self._save_project_config()
            return content
        except Exception as e:
            return f"// Error: {e}"

    def _project_config_path(self):
        if not self.project_root:
            return None
        return os.path.join(self.project_root, ".vigo_project.json")

    def _save_project_config(self):
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
        path = self._project_config_path()
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config.get("last_file")
        except Exception:
            return None

    def save_project_state(self, state_json):
        """Save project state (open chats, editor tabs)."""
        if not self.project_root:
            return json.dumps({"status": "error", "message": "No project open."})
        try:
            state = json.loads(state_json)
            path = self._project_config_path()
            if not path:
                return json.dumps({"status": "error", "message": "No project config path."})
            config = {}
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            config["open_chats"] = state.get("open_chats", [])
            config["open_editor_tabs"] = state.get("open_editor_tabs", [])
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            return json.dumps({"status": "ok"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def _get_templates_dir(self):
        if not self.project_root:
            return None
        templates_dir = os.path.join(self.project_root, ".vigo_templates")
        os.makedirs(templates_dir, exist_ok=True)
        return templates_dir

    def save_template(self, name, template_json):
        """Save a task template."""
        templates_dir = self._get_templates_dir()
        if not templates_dir:
            return json.dumps({"status": "error", "message": "No project open."})
        try:
            template = json.loads(template_json)
            template["name"] = name
            safe_name = name.replace(" ", "-").replace("/", "-").replace("\\", "-")
            filepath = os.path.join(templates_dir, f"{safe_name}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(template, f, indent=2, ensure_ascii=False)
            return json.dumps({"status": "ok", "name": safe_name})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def list_templates(self):
        """List all saved task templates."""
        templates_dir = self._get_templates_dir()
        if not templates_dir or not os.path.exists(templates_dir):
            return json.dumps([])
        templates = []
        try:
            for fname in sorted(os.listdir(templates_dir)):
                if fname.endswith(".json"):
                    filepath = os.path.join(templates_dir, fname)
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    templates.append({
                        "name": data.get("name", fname[:-5]),
                        "label": data.get("label", data.get("name", fname[:-5])),
                        "mode": data.get("mode", "alone")
                    })
        except Exception:
            pass
        return json.dumps(templates)

    def load_template(self, name):
        """Load a task template by name."""
        templates_dir = self._get_templates_dir()
        if not templates_dir:
            return json.dumps({"status": "error", "message": "No project open."})
        safe_name = name.replace(" ", "-").replace("/", "-").replace("\\", "-")
        filepath = os.path.join(templates_dir, f"{safe_name}.json")
        if not os.path.exists(filepath):
            return json.dumps({"status": "error", "message": "Template not found."})
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.dumps(json.load(f))
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def delete_template(self, name):
        """Delete a task template by name."""
        templates_dir = self._get_templates_dir()
        if not templates_dir:
            return json.dumps({"status": "error", "message": "No project open."})
        safe_name = name.replace(" ", "-").replace("/", "-").replace("\\", "-")
        filepath = os.path.join(templates_dir, f"{safe_name}.json")
        if not os.path.exists(filepath):
            return json.dumps({"status": "error", "message": "Template not found."})
        try:
            os.remove(filepath)
            return json.dumps({"status": "ok"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def create_project_manager(self, name, system_prompt, default_provider="gemma-4b",
                                max_masters=3, max_workers_per_master=2, model_preferences_json="{}"):
        """Create a new project manager."""
        try:
            from vigo.stdlib.agent_manager import create_project_manager as do_create
            prefs = json.loads(model_preferences_json) if model_preferences_json else {}
            pm = do_create(name, system_prompt, default_provider, max_masters, max_workers_per_master, prefs)
            return json.dumps({"status": "ok", "pm": pm})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def update_project_manager(self, pm_id, name=None, system_prompt=None, default_provider=None,
                                max_masters=None, max_workers_per_master=None, model_preferences_json=None):
        """Update a project manager."""
        try:
            from vigo.stdlib.agent_manager import update_project_manager as do_update
            kwargs = {}
            if name is not None: kwargs["name"] = name
            if system_prompt is not None: kwargs["system_prompt"] = system_prompt
            if default_provider is not None: kwargs["default_provider"] = default_provider
            if max_masters is not None: kwargs["max_masters"] = max_masters
            if max_workers_per_master is not None: kwargs["max_workers_per_master"] = max_workers_per_master
            if model_preferences_json is not None:
                kwargs["model_preferences"] = json.loads(model_preferences_json)
            pm = do_update(pm_id, **kwargs)
            if pm:
                return json.dumps({"status": "ok", "pm": pm})
            return json.dumps({"status": "error", "message": "Project manager not found."})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def delete_project_manager(self, pm_id):
        """Delete a project manager."""
        try:
            from vigo.stdlib.agent_manager import delete_project_manager as do_delete
            do_delete(pm_id)
            return json.dumps({"status": "ok"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def list_project_managers(self):
        """List all project managers and preset templates."""
        try:
            from vigo.stdlib.agent_manager import list_project_managers as do_list, PRESET_TEMPLATES
            managers = do_list()
            return json.dumps({"managers": managers, "templates": PRESET_TEMPLATES})
        except Exception as e:
            return json.dumps({"managers": [], "templates": []})

    def launch_agent(self, pm_id, project_name, goal, plan_json="", project_path=""):
        """Launch an auto agent pipeline."""
        try:
            if project_path and os.path.isdir(project_path):
                self.project_root = project_path
                self.current_project = os.path.basename(project_path)
                self._save_config()
            from vigo.stdlib.agent_manager import get_project_manager, build_agent_pipeline
            pm = get_project_manager(pm_id)
            if not pm:
                return json.dumps({"status": "error", "message": "Project manager not found."})
            pipeline = build_agent_pipeline(pm, goal, plan_json if plan_json else None)
            return json.dumps({"status": "ok", "pipeline": pipeline, "pm_name": pm.get("name", ""), "project_root": self.project_root or ""})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def load_project_state(self):
        if not self.project_root:
            return json.dumps({"open_chats": [], "open_editor_tabs": [], "last_file": ""})
        path = self._project_config_path()
        if not path or not os.path.exists(path):
            return json.dumps({"open_chats": [], "open_editor_tabs": [], "last_file": ""})
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
            # Restore chat histories
            histories = config.get("chat_histories", {})
            for chat_id, history in histories.items():
                if chat_id not in self.chat_sessions:
                    self.chat_sessions[chat_id] = {"history": history, "type": "master", "parentId": None, "model": self.current_model}
                else:
                    self.chat_sessions[chat_id]["history"] = history
            return json.dumps({
                "open_chats": config.get("open_chats", []),
                "open_editor_tabs": config.get("open_editor_tabs", []),
                "last_file": config.get("last_file", "")
            })
        except Exception:
            return json.dumps({"open_chats": [], "open_editor_tabs": [], "last_file": ""})

    def save_file(self, filepath, content):
        if not self.project_root:
            return json.dumps({"status": "error", "message": "No project open."})
        full_path = os.path.join(self.project_root, filepath)
        if os.path.exists(full_path):
            self._create_backup(full_path)
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return json.dumps({"status": "ok", "path": filepath})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def get_current_file(self):
        return self.current_file or ""

    def open_folder_dialog(self):
        """Open a native folder picker dialog."""
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            folder = filedialog.askdirectory(title="Select Folder")
            root.destroy()
            return folder or ""
        except Exception:
            return ""

    def set_chat_model(self, chatId, model_id, provider):
        session = self._get_session(chatId)
        if session["type"] != "master":
            return json.dumps({"status": "error", "message": "Only master chats can change model."})
        session["model"] = model_id
        for cid, cs in self.chat_sessions.items():
            if cs["type"] == "worker" and cs.get("parentId") == chatId:
                cs["model"] = model_id
        return json.dumps({"status": "ok", "model": model_id})

    def clear_chat_history(self, chatId):
        session = self._get_session(chatId)
        session["history"] = []
        return json.dumps({"status": "ok"})

    def get_chat_history(self, chatId):
        """Return the conversation history for a chat."""
        session = self._get_session(chatId)
        return json.dumps(session.get("history", [])[-10:])

    def get_settings(self):
        return json.dumps(self.settings)

    def save_settings(self, settings_json):
        try:
            new_settings = json.loads(settings_json)
            self.settings.update(new_settings)
            self._save_config()
            return json.dumps({"status": "ok"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def save_conversation(self, conv_id, conv_type, messages_json, task_description=""):
        """Archive a conversation to project memory."""
        if not self.project_root:
            return json.dumps({"status": "error", "message": "No project open."})
        try:
            from vigo.stdlib.conversation_memory import save_conversation as do_save
            messages = json.loads(messages_json)
            result = do_save(
                self.project_root, conv_id, conv_type, messages,
                self.current_model, task_description
            )
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def list_conversations(self):
        """List archived conversations in current project."""
        if not self.project_root:
            return json.dumps([])
        try:
            from vigo.stdlib.conversation_memory import list_conversations as do_list
            return json.dumps(do_list(self.project_root))
        except Exception:
            return json.dumps([])

    def shutdown_save(self):
        """Save all open conversations and project state before shutdown."""
        saved = []
        for chat_id, session in self.chat_sessions.items():
            try:
                messages = []
                for entry in session.get("history", []):
                    messages.append({"role": "user", "content": entry.get("user", "")})
                    messages.append({"role": "ai", "content": entry.get("ai", "")})
                if messages:
                    from vigo.stdlib.conversation_memory import save_conversation as do_save
                    do_save(
                        self.project_root or "", chat_id,
                        session.get("type", "master"), messages,
                        self.current_model, ""
                    )
                    saved.append(chat_id)
            except Exception:
                pass
        # Also save history snapshots to project config for restore
        self._save_chat_histories()
        self._save_config()
        return json.dumps({"status": "ok", "saved": len(saved)})

    def _save_chat_histories(self):
        """Save chat histories to project config for session restore."""
        if not self.project_root:
            return
        path = self._project_config_path()
        if not path:
            return
        try:
            config = {}
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            histories = {}
            for chat_id, session in self.chat_sessions.items():
                histories[chat_id] = session.get("history", [])[-20:]  # Last 20 turns
            config["chat_histories"] = histories
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass

    def restore_chat_histories(self):
        """Restore chat histories from project config."""
        if not self.project_root:
            return {}
        path = self._project_config_path()
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config.get("chat_histories", {})
        except Exception:
            return {}

    def search_memories(self, query):
        """Search archived conversations for a query, returning clean snippets."""
        if not self.project_root:
            return json.dumps({"results": []})
        results = []
        conv_root = os.path.join(self.project_root, ".vigo_memory", "conversations")
        if os.path.exists(conv_root):
            for conv_id in os.listdir(conv_root):
                conv_dir = os.path.join(conv_root, conv_id)
                if not os.path.isdir(conv_dir):
                    continue
                md_files = sorted([f for f in os.listdir(conv_dir) if f.endswith('.md')], reverse=True)
                for md_file in md_files[:3]:
                    md_path = os.path.join(conv_dir, md_file)
                    try:
                        with open(md_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        marker = "## Full Conversation"
                        idx = content.find(marker)
                        if idx >= 0:
                            content = content[idx + len(marker):]
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if query.lower() in line.lower() and line.strip() and not line.strip().startswith('#'):
                                start = max(0, i - 2)
                                end = min(len(lines), i + 3)
                                snippet = ' '.join([l.strip() for l in lines[start:end] if l.strip() and not l.strip().startswith('#')])
                                if snippet and len(snippet) > 10:
                                    results.append({"conv_id": conv_id, "snippet": snippet[:200]})
                                    break
                        if len(results) >= 5:
                            break
                    except Exception:
                        pass
                if len(results) >= 5:
                    break
        return json.dumps({"results": results})

    # ═══════════════════════════════════════
    #  Backup System
    # ═══════════════════════════════════════

    def _get_backup_dir(self):
        if not self.project_root:
            return None
        backup_dir = os.path.join(self.project_root, ".vigo_backups")
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    def _create_backup(self, file_path):
        backup_dir = self._get_backup_dir()
        if not backup_dir:
            return None
        rel_path = os.path.relpath(file_path, self.project_root)
        safe_name = rel_path.replace("\\", "_").replace("/", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{safe_name}.bak_{timestamp}"
        backup_path = os.path.join(backup_dir, backup_name)
        try:
            shutil.copy2(file_path, backup_path)
            return backup_name
        except Exception:
            return None

    def list_backups(self, path):
        if not self.project_root:
            return json.dumps([])
        backup_dir = self._get_backup_dir()
        if not backup_dir or not os.path.exists(backup_dir):
            return json.dumps([])
        rel_path = os.path.relpath(os.path.join(self.project_root, path), self.project_root)
        safe_name = rel_path.replace("\\", "_").replace("/", "_")
        prefix = f"{safe_name}.bak_"
        backups = []
        try:
            for fname in sorted(os.listdir(backup_dir), reverse=True):
                if fname.startswith(prefix):
                    full = os.path.join(backup_dir, fname)
                    stat = os.stat(full)
                    backups.append({"filename": fname, "size": stat.st_size, "time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")})
        except Exception:
            pass
        return json.dumps(backups)

    def read_backup(self, backup_name, target_path):
        """Read the content of a backup file."""
        backup_dir = self._get_backup_dir()
        if not backup_dir:
            return "Error: No project open."
        backup_full = os.path.join(backup_dir, backup_name)
        if not os.path.exists(backup_full):
            return "Error: Backup not found."
        try:
            with open(backup_full, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error: {e}"

    def restore_backup(self, backup_name, target_path):
        if not self.project_root:
            return json.dumps({"status": "error", "message": "No project open."})
        backup_dir = self._get_backup_dir()
        backup_full = os.path.join(backup_dir, backup_name)
        if not os.path.exists(backup_full):
            return json.dumps({"status": "error", "message": f"Backup not found: {backup_name}"})
        target_full = os.path.join(self.project_root, target_path)
        try:
            self._create_backup(target_full)
            shutil.copy2(backup_full, target_full)
            return json.dumps({"status": "ok", "path": target_path})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    # ═══════════════════════════════════════
    #  Model Management
    # ═══════════════════════════════════════

    def _load_models(self):
        models = {"local": [], "cloud": []}
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
            for line in result.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if parts:
                    name = parts[0].replace(":latest", "")
                    models["local"].append({"id": name, "name": name, "provider": "ollama", "source": "local"})
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
        if not self._model_registry["local"] and not self._model_registry["cloud"]:
            self._model_registry = self._load_models()
        return json.dumps(self._model_registry["local"] + self._model_registry["cloud"])

    def list_available_models(self):
        """List installed models and popular models available for download."""
        installed = {}
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
            for line in result.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if parts:
                    name = parts[0].replace(":latest", "")
                    size = parts[-2] if len(parts) >= 3 else "?"
                    installed[name] = size
        except:
            pass

        popular = [
            {"name": "qwen2.5:7b", "size": "4.7 GB", "desc": "Alibaba Qwen 2.5, strong multilingual"},
            {"name": "codellama:7b", "size": "3.8 GB", "desc": "Meta Code Llama, code generation"},
            {"name": "mistral:7b", "size": "4.1 GB", "desc": "Mistral 7B, general purpose"},
            {"name": "phi3:mini", "size": "2.3 GB", "desc": "Microsoft Phi-3 Mini, compact & fast"},
            {"name": "llava:7b", "size": "4.5 GB", "desc": "LLaVA multimodal, image understanding"},
            {"name": "deepseek-coder:6.7b", "size": "3.8 GB", "desc": "DeepSeek Coder, code specialist"},
            {"name": "nomic-embed-text", "size": "0.3 GB", "desc": "Nomic embedding model, for memory"},
            {"name": "gemma2:9b", "size": "5.4 GB", "desc": "Google Gemma 2, general purpose"},
        ]

        available = []
        for m in popular:
            if m["name"] not in installed:
                available.append(m)

        return json.dumps({"installed": installed, "available": available})

    def download_model(self, model_name):
        """Start downloading a model via ollama pull in background thread."""
        import threading
        models_dir = os.path.join(APP_DIR, "models", "Local")
        os.makedirs(models_dir, exist_ok=True)
        progress_file = os.path.join(models_dir, f".download_progress_{model_name.replace(':', '_')}.txt")

        def do_download():
            try:
                with open(progress_file, "w") as f:
                    f.write("0")
                result = subprocess.run(
                    ["ollama", "pull", model_name],
                    capture_output=True, text=True, timeout=1800,
                    env=os.environ.copy()
                )
                if result.returncode == 0:
                    with open(progress_file, "w") as f:
                        f.write("100")
                else:
                    with open(progress_file, "w") as f:
                        f.write("-1")
            except Exception as e:
                with open(progress_file, "w") as f:
                    f.write(f"-1\nError: {e}")

        t = threading.Thread(target=do_download, daemon=True)
        t.start()
        return json.dumps({"status": "ok", "message": f"Downloading {model_name}..."})

    def get_download_progress(self, model_name):
        """Get download progress percentage for a model."""
        models_dir = os.path.join(APP_DIR, "models", "Local")
        progress_file = os.path.join(models_dir, f".download_progress_{model_name.replace(':', '_')}.txt")
        if os.path.exists(progress_file):
            try:
                with open(progress_file, "r") as f:
                    val = f.read().strip()
                    return json.dumps({"progress": int(val)})
            except:
                pass
        return json.dumps({"progress": 0})

    def cancel_download(self, model_name):
        """Cancel an ongoing model download."""
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"], capture_output=True, timeout=10)
            else:
                subprocess.run(["pkill", "-f", f"ollama pull {model_name}"], capture_output=True, timeout=10)
            return json.dumps({"status": "ok"})
        except:
            return json.dumps({"status": "error", "message": "Failed to cancel"})

    def delete_model(self, model_name):
        """Delete a local model via ollama rm."""
        try:
            result = subprocess.run(
                ["ollama", "rm", model_name],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return json.dumps({"status": "ok", "message": f"Deleted {model_name}"})
            return json.dumps({"status": "error", "message": result.stderr.strip() or result.stdout.strip()})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def set_model(self, model_id, provider):
        self.current_model = model_id
        self.current_provider = provider
        self._save_config()
        return json.dumps({"status": "ok", "model": model_id, "provider": provider})

    # ═══════════════════════════════════════
    #  AI Operations
    # ═══════════════════════════════════════

    def _call_ollama_stream(self, prompt_text):
        model = self.current_model
        try:
            data = json.dumps({"model": model, "prompt": str(prompt_text), "stream": True}).encode('utf-8')
            req = urllib.request.Request("http://localhost:11434/api/generate", data=data, headers={"Content-Type": "application/json"})
            chunks = []
            with urllib.request.urlopen(req, timeout=120) as resp:
                buffer = ""
                while True:
                    byte = resp.read(1)
                    if not byte:
                        break
                    buffer += byte.decode('utf-8', errors='ignore')
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            try:
                                obj = json.loads(line)
                                chunk = obj.get("response", "")
                                if chunk:
                                    chunks.append(chunk)
                                if obj.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                pass
            return "".join(chunks), chunks, None
        except Exception as e:
            return "", [], str(e)

    def ask_ai(self, message, chatId="default"):
        try:
            provider = self.current_provider
            start_time = time.time()

            if provider != "ollama":
                return json.dumps({"status": "error", "response": f"Provider '{provider}' not supported yet.", "elapsed": 0})

            import threading

            session = self._get_session(chatId)
            history = session["history"]

            # Resolve model: worker inherits from master
            if session["type"] == "worker" and session.get("parentId"):
                parent_session = self._get_session(session["parentId"])
                model = parent_session.get("model", self.current_model)
            else:
                model = session.get("model", self.current_model)

            tools_prompt = """You are a helpful AI coding assistant. You have access to these tools:

read_file(path) - Read the content of a file in the current project.
write_file(path, content) - Overwrite an existing file with new content.
create_file(path, content) - Create a new file in the project.
search_files(query) - Search for text across all project files.

To use a tool, reply with ONLY the tool command on one line:

READ: <file path>
WRITE: <file path>
<content>
CREATE: <file path>
<content>
SEARCH: <query>

If you don't need a tool, just answer normally.
Current open file: {current_file}
Put any code in ```language ...``` blocks.
""".format(current_file=self.current_file or 'none')

            prompt = tools_prompt
            for entry in history[-10:]:
                prompt += f"\nUser: {entry['user']}\nAssistant: {entry['ai']}"

            if message:
                prompt += f"\nUser: {message}\nAssistant:"

            result_container = {}
            def call_with_model():
                host = self.settings.get("ollama_host", "http://localhost:11434")
                to = self.settings.get("timeout", 120)
                data = json.dumps({"model": model, "prompt": str(prompt), "stream": True}).encode('utf-8')
                req = urllib.request.Request(host + "/api/generate", data=data, headers={"Content-Type": "application/json"})
                chunks = []
                with urllib.request.urlopen(req, timeout=to) as resp:
                    buffer = ""
                    while True:
                        byte = resp.read(1)
                        if not byte:
                            break
                        buffer += byte.decode('utf-8', errors='ignore')
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if line:
                                try:
                                    obj = json.loads(line)
                                    chunk = obj.get("response", "")
                                    if chunk:
                                        chunks.append(chunk)
                                    if obj.get("done", False):
                                        break
                                except json.JSONDecodeError:
                                    pass
                result_container['text'] = "".join(chunks)
                result_container['chunks'] = chunks
            t = threading.Thread(target=call_with_model)
            t.start()
            t.join(timeout=120)

            if result_container.get('error'):
                return json.dumps({"status": "error", "response": f"Error: {result_container['error']}"})

            text = result_container.get('text', '')
            chunks = result_container.get('chunks', [])
            stripped = text.strip()

            if stripped.startswith("READ:") and "\n" not in stripped:
                file_path = stripped[5:].strip()
                file_content = self._read_project_file(file_path)
                history.append({"user": message or "(continue)", "ai": text.strip()})
                history.append({"user": "(tool result)", "ai": f"read_file {file_path}: {file_content[:500]}"})
                if len(history) > 50:
                    history[:] = history[-50:]
                return json.dumps({"status": "ok", "action": "tool", "tool": "READ", "path": file_path})

            if stripped.startswith("WRITE:"):
                lines = stripped.split("\n", 1)
                file_path = lines[0][6:].strip()
                content = lines[1] if len(lines) > 1 else ""
                write_result = self._write_project_file(file_path, content)
                history.append({"user": message or "(continue)", "ai": text.strip()})
                history.append({"user": "(tool result)", "ai": f"write_file {file_path}: {write_result}"})
                if len(history) > 50:
                    history[:] = history[-50:]
                return json.dumps({"status": "ok", "action": "tool", "tool": "WRITE", "path": file_path})

            if stripped.startswith("CREATE:"):
                lines = stripped.split("\n", 1)
                file_path = lines[0][7:].strip()
                content = lines[1] if len(lines) > 1 else ""
                create_result = self._create_project_file(file_path, content)
                history.append({"user": message or "(continue)", "ai": text.strip()})
                history.append({"user": "(tool result)", "ai": f"create_file {file_path}: {create_result}"})
                if len(history) > 50:
                    history[:] = history[-50:]
                return json.dumps({"status": "ok", "action": "tool", "tool": "CREATE", "path": file_path})

            if stripped.startswith("SEARCH:"):
                query = stripped[7:].strip()
                search_result = self._search_project_files(query)
                history.append({"user": message or "(continue)", "ai": text.strip()})
                history.append({"user": "(tool result)", "ai": f"search_files: {search_result[:500]}"})
                if len(history) > 50:
                    history[:] = history[-50:]
                return json.dumps({"status": "ok", "action": "tool", "tool": "SEARCH", "query": query})

            if text:
                import re
                if "done thinking." in text:
                    text = text.split("done thinking.")[-1].strip()
                text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
                if len(text) > 3000:
                    text = text[:3000]

            elapsed = round(time.time() - start_time, 1)
            history.append({"user": message or "(continue)", "ai": text.strip()})
            if len(history) > 50:
                history[:] = history[-50:]

            if text:
                if not chunks:
                    chunks = [text[i:i+3] for i in range(0, len(text), 3)]
            self._save_chat_histories()
            if text:
                if not chunks:
                    chunks = [text[i:i+3] for i in range(0, len(text), 3)]
                return json.dumps({"status": "ok", "action": "done", "response": text.strip(), "elapsed": elapsed, "chunks": chunks})
                return json.dumps({"status": "ok", "action": "done", "response": text.strip(), "elapsed": elapsed, "chunks": chunks})
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

    def _write_project_file(self, path, content):
        if not self.project_root:
            return "Error: No project open."
        full_path = os.path.join(self.project_root, path.strip())
        if not os.path.exists(full_path):
            return f"Error: File not found: {path}"
        try:
            self._create_backup(full_path)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return "Written successfully (backup created)."
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
            return "Created successfully."
        except Exception as e:
            return f"Error: {e}"

    def _search_project_files(self, query):
        if not self.project_root:
            return "Error: No project open."
        results = []
        try:
            for root, dirs, files in os.walk(self.project_root):
                dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules", ".vigo_chromadb", ".vigo_backups")]
                for file in files:
                    if file.startswith(".") or file.endswith((".exe", ".dll", ".pyd", ".pyc", ".db", ".zip", ".png", ".jpg", ".ico", ".vigo_backup")):
                        continue
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            for i, line in enumerate(f, 1):
                                if query.lower() in line.lower():
                                    rel = os.path.relpath(filepath, self.project_root)
                                    results.append(f"{rel}:{i}: {line.strip()[:200]}")
                                    if len(results) >= 20:
                                        break
                    except Exception:
                        pass
                    if len(results) >= 20:
                        break
                if len(results) >= 20:
                    break
        except Exception as e:
            return f"Search error: {e}"
        if results:
            return "\n".join(results)
        return f"No matches found for '{query}'."

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
                results.append({"key": m.get("key", ""), "value": str(m.get("value", ""))[:200], "similarity": m.get("similarity", 0)})
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
            result = subprocess.run(["python", "main.py", "tests/test_regression_v36.vigo"], cwd=self.vigo_root, capture_output=True, text=True, timeout=120)
            return json.dumps({"status": "ok" if result.returncode == 0 else "fail", "stdout": result.stdout[-2000:], "stderr": result.stderr[-500:]})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def run_vigo_file(self, path):
        if not self.project_root:
            return json.dumps({"status": "error", "output": "No project open."})
        full_path = os.path.join(self.project_root, path)
        if not os.path.exists(full_path):
            return json.dumps({"status": "error", "output": f"File not found: {path}"})
        try:
            result = subprocess.run(["python", "main.py", full_path], cwd=self.vigo_root, capture_output=True, text=True, timeout=30)
            output = result.stdout
            if result.stderr:
                output += "\n" + result.stderr
            return json.dumps({"status": "ok" if result.returncode == 0 else "error", "output": output.strip() or "(no output)"})
        except subprocess.TimeoutExpired:
            return json.dumps({"status": "error", "output": "Execution timed out (30s)."})
        except Exception as e:
            return json.dumps({"status": "error", "output": str(e)})

    # ═══════════════════════════════════════
    #  Git Operations
    # ═══════════════════════════════════════

    def _run_git(self, args):
        """Run a git command and return stdout, stderr, returncode."""
        if not self.project_root:
            return "", "No project open.", 1
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.project_root,
                capture_output=True, text=True, timeout=30
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Timeout", 1
        except FileNotFoundError:
            return "", "Git is not installed or not in PATH.", 1
        except Exception as e:
            return "", str(e), 1

    def git_status(self):
        """Get git status summary."""
        stdout, stderr, rc = self._run_git(["status", "--short"])
        if rc != 0:
            return json.dumps({"status": "error", "message": stderr or "Git error"})
        files = []
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if line:
                status = line[:2]
                filename = line[3:]
                files.append({"status": status, "file": filename})
        return json.dumps({"status": "ok", "files": files})

    def git_commit(self, message):
        """Stage all changes and commit."""
        self._run_git(["add", "-A"])
        stdout, stderr, rc = self._run_git(["commit", "-m", message])
        if rc != 0:
            return json.dumps({"status": "error", "message": stderr or stdout})
        return json.dumps({"status": "ok", "message": stdout.strip() or "Committed."})

    def git_push(self):
        """Push to remote."""
        stdout, stderr, rc = self._run_git(["push"])
        if rc != 0:
            return json.dumps({"status": "error", "message": stderr or stdout})
        return json.dumps({"status": "ok", "message": stdout.strip() or "Pushed."})

    def git_pull(self):
        """Pull from remote."""
        stdout, stderr, rc = self._run_git(["pull"])
        if rc != 0:
            return json.dumps({"status": "error", "message": stderr or stdout})
        return json.dumps({"status": "ok", "message": stdout.strip() or "Pulled."})

    def git_branches(self):
        """List branches."""
        stdout, stderr, rc = self._run_git(["branch"])
        if rc != 0:
            return json.dumps({"status": "error", "message": stderr or "Git error"})
        branches = []
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if line:
                is_current = line.startswith("*")
                name = line[2:] if is_current else line
                branches.append({"name": name, "current": is_current})
        return json.dumps({"status": "ok", "branches": branches})

    def git_checkout(self, branch_name):
        """Switch to a branch."""
        stdout, stderr, rc = self._run_git(["checkout", branch_name])
        if rc != 0:
            return json.dumps({"status": "error", "message": stderr or stdout})
        return json.dumps({"status": "ok", "message": "Switched to " + branch_name})

    def git_create_branch(self, branch_name):
        """Create and switch to a new branch."""
        stdout, stderr, rc = self._run_git(["checkout", "-b", branch_name])
        if rc != 0:
            return json.dumps({"status": "error", "message": stderr or stdout})
        return json.dumps({"status": "ok", "message": "Created and switched to " + branch_name})

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