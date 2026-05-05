import os, sys, json, webview
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(APP_DIR))
from api import Api
api = Api()

class JSBridge:
    def __init__(self): self.api = api
    def list_projects(self): return self.api.list_projects()
    def create_project(self, name): return self.api.create_project(name)
    def open_project(self, name): return self.api.open_project(name)
    def close_project(self): return self.api.close_project()
    def import_project(self, name, path): return self.api.import_project(name, path)
    def get_file_tree(self): return self.api.get_file_tree()
    def get_dir_children(self, dir_path): return self.api.get_dir_children(dir_path)
    def read_file(self, path): return self.api.read_file(path)
    def save_file(self, path, content): return self.api.save_file(path, content)
    def get_current_file(self): return self.api.get_current_file()
    def create_file(self, dir_path, name): return self.api.create_file(dir_path, name)
    def create_folder(self, dir_path, name): return self.api.create_folder(dir_path, name)
    def delete_item(self, path): return self.api.delete_item(path)
    def rename_item(self, path, new_name): return self.api.rename_item(path, new_name)
    def open_folder_dialog(self): return self.api.open_folder_dialog()
    def list_models(self): return self.api.list_models()
    def set_model(self, model_id, provider): return self.api.set_model(model_id, provider)
    def ask_ai(self, message): return self.api.ask_ai(message)
    def mem_save(self, key, content): return self.api.mem_save(key, content)
    def mem_search(self, query, limit=5): return self.api.mem_search(query, limit)
    def mem_snapshot(self): return self.api.mem_snapshot()
    def run_test(self): return self.api.run_test()
    def run_vigo_file(self, path): return self.api.run_vigo_file(path)
    def copy_to_clipboard(self, text):
        """Copy text to Windows clipboard via PowerShell."""
        import subprocess
        escaped = text.replace('"', '`"')
        ps_script = f'Set-Clipboard -Value "{escaped}"'
        subprocess.run(["powershell", "-Command", ps_script], timeout=5)
        return True

def main():
    html_path = os.path.join(APP_DIR, "ui", "index.html")
    with open(html_path, "r", encoding="utf-8") as f: html_content = f.read()
    webview.create_window(title="ViGo Dev - AI Development Environment", html=html_content, js_api=JSBridge(), width=1400, height=900, min_size=(900, 600))
    webview.start()

if __name__ == "__main__": main()