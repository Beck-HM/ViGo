"""ViGo Internationalization Library - Multi-language Error Messages"""
from ..runtime.objects import BuiltinFunction


class I18NManager:
    def __init__(self):
        self.current_lang = "en"
        self.messages = {
            "en": {
                "file_not_found": "File not found: {path}",
                "syntax_error": "Syntax error at line {line}, column {col}",
                "runtime_error": "Runtime error: {msg}",
                "type_error": "Type error: expected {expected}, got {actual}",
                "division_zero": "Division by zero",
                "index_out_of_range": "Index {index} out of range (length {length})",
                "variable_undefined": "Variable '{name}' is not defined",
                "function_missing": "Function '{name}' is not defined",
                "auth_failed": "Authentication failed",
                "network_error": "Network error: {detail}",
                "timeout": "Operation timed out after {seconds}s",
                "permission_denied": "Permission denied: {path}",
            },
            "zh": {
                "file_not_found": "File not found: {path}",
                "syntax_error": "Syntax error at line {line}, column {col}",
                "runtime_error": "Runtime error: {msg}",
                "type_error": "Type error: expected {expected}, got {actual}",
                "division_zero": "Division by zero",
                "index_out_of_range": "Index {index} out of range (length {length})",
                "variable_undefined": "Variable '{name}' is not defined",
                "function_missing": "Function '{name}' is not defined",
                "auth_failed": "Authentication failed",
                "network_error": "Network error: {detail}",
                "timeout": "Operation timed out after {seconds}s",
                "permission_denied": "Permission denied: {path}",
            },
            "ja": {
                "file_not_found": "File not found: {path}",
                "syntax_error": "Syntax error at line {line}, column {col}",
                "runtime_error": "Runtime error: {msg}",
                "type_error": "Type error: expected {expected}, got {actual}",
                "division_zero": "Division by zero",
                "index_out_of_range": "Index {index} out of range (length {length})",
                "variable_undefined": "Variable '{name}' is not defined",
                "function_missing": "Function '{name}' is not defined",
                "auth_failed": "Authentication failed",
                "network_error": "Network error: {detail}",
                "timeout": "Operation timed out after {seconds}s",
                "permission_denied": "Permission denied: {path}",
            },
        }

    def set_language(self, lang):
        if lang in self.messages:
            self.current_lang = lang
            return True
        return False

    def get_languages(self):
        return list(self.messages.keys())

    def translate(self, key, params=None):
        msgs = self.messages.get(self.current_lang, self.messages["en"])
        template = msgs.get(key, key)
        if params:
            for k, v in params.items():
                template = template.replace("{" + k + "}", str(v))
        return template


_i18n = I18NManager()


def register(env):
    env.define('i18n_set_lang', BuiltinFunction(
        lambda lang: _i18n.set_language(lang),
        'i18n_set_lang'))
    env.define('i18n_languages', BuiltinFunction(
        lambda: _i18n.get_languages(),
        'i18n_languages'))
    env.define('i18n_translate', BuiltinFunction(
        lambda key, params=None: _i18n.translate(key, params),
        'i18n_translate'))