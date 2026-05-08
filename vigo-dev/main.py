import os, sys, json, webview

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
    sys.path.insert(0, os.path.dirname(APP_DIR))
else:
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
    def ask_ai(self, message, chatId): return self.api.ask_ai(message, chatId)
    def mem_save(self, key, content): return self.api.mem_save(key, content)
    def mem_search(self, query, limit=5): return self.api.mem_search(query, limit)
    def mem_snapshot(self): return self.api.mem_snapshot()
    def run_test(self): return self.api.run_test()
    def run_vigo_file(self, path): return self.api.run_vigo_file(path)
    def list_backups(self, path): return self.api.list_backups(path)
    def restore_backup(self, backup_path, target_path): return self.api.restore_backup(backup_path, target_path)
    def set_chat_model(self, chatId, model_id, provider): return self.api.set_chat_model(chatId, model_id, provider)
    def clear_chat_history(self, chatId): return self.api.clear_chat_history(chatId)
    def get_settings(self): return self.api.get_settings()
    def save_settings(self, settings_json): return self.api.save_settings(settings_json)
    def save_conversation(self, conv_id, conv_type, messages_json, task_description):
        return self.api.save_conversation(conv_id, conv_type, messages_json, task_description)
    def list_conversations(self): return self.api.list_conversations()
    def shutdown_save(self): return self.api.shutdown_save()
    def search_memories(self, query): return self.api.search_memories(query)
    def save_project_state(self, state_json): return self.api.save_project_state(state_json)
    def load_project_state(self): return self.api.load_project_state()
    def save_template(self, name, template_json): return self.api.save_template(name, template_json)
    def list_templates(self): return self.api.list_templates()
    def load_template(self, name): return self.api.load_template(name)
    def delete_template(self, name): return self.api.delete_template(name)
    def get_chat_history(self, chatId): return self.api.get_chat_history(chatId)
    def create_project_manager(self, name, system_prompt, default_provider, max_masters, max_workers_per_master, model_preferences_json):
        return self.api.create_project_manager(name, system_prompt, default_provider, max_masters, max_workers_per_master, model_preferences_json)
    def update_project_manager(self, pm_id, name, system_prompt, default_provider, max_masters, max_workers_per_master, model_preferences_json):
        return self.api.update_project_manager(pm_id, name, system_prompt, default_provider, max_masters, max_workers_per_master, model_preferences_json)
    def delete_project_manager(self, pm_id): return self.api.delete_project_manager(pm_id)
    def list_project_managers(self): return self.api.list_project_managers()
    def launch_agent(self, pm_id, project_name, goal, plan_json, project_path): 
        return self.api.launch_agent(pm_id, project_name, goal, plan_json, project_path)
    def list_available_models(self): return self.api.list_available_models()
    def download_model(self, model_name): return self.api.download_model(model_name)
    def get_download_progress(self, model_name): return self.api.get_download_progress(model_name)
    def delete_model(self, model_name): return self.api.delete_model(model_name)
    def cancel_download(self, model_name): return self.api.cancel_download(model_name)
    def read_backup(self, backup_name, target_path): return self.api.read_backup(backup_name, target_path)
    def git_status(self): return self.api.git_status()
    def git_commit(self, message): return self.api.git_commit(message)
    def git_push(self): return self.api.git_push()
    def git_pull(self): return self.api.git_pull()
    def git_branches(self): return self.api.git_branches()
    def git_checkout(self, branch_name): return self.api.git_checkout(branch_name)
    def git_create_branch(self, branch_name): return self.api.git_create_branch(branch_name)
    def copy_to_clipboard(self, text):
        import subprocess
        escaped = text.replace('"', '`"')
        ps_script = f'Set-Clipboard -Value "{escaped}"'
        subprocess.run(["powershell", "-Command", ps_script], timeout=5)
        return True

def main():
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = APP_DIR
    html_path = os.path.join(base_dir, "ui", "index.html")
    window = webview.create_window(
        title="ViGo Dev - AI Development Environment",
        url=html_path,
        js_api=JSBridge(),
        width=1400, height=900,
        min_size=(900, 600)
    )
    window.events.closed += on_window_close
    webview.start()

def on_window_close():
    try:
        for chat_id, session in api.chat_sessions.items():
            messages = []
            for entry in session.get("history", []):
                messages.append({"role": "user", "content": entry.get("user", "")})
                messages.append({"role": "ai", "content": entry.get("ai", "")})
            if messages:
                from vigo.stdlib.conversation_memory import save_conversation as do_save
                try:
                    do_save(
                        api.project_root or "", chat_id,
                        session.get("type", "master"), messages,
                        api.current_model, ""
                    )
                except:
                    pass
        api._save_chat_histories()
        api._save_config()
    except:
        pass

if __name__ == "__main__": main()