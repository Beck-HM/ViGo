#include "vigo_bridge.h"
#include "vigo_runtime.h"
#include "vigo_value.h"
#include "vigo_utils.h"
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>

static PyObject* g_interpreter = NULL;
static PyObject* g_ai_client = NULL;
static PyObject* g_global_env = NULL;
static PyObject* g_persistent_registry = NULL;

int vigo_bridge_py_init(void) {
    if (Py_IsInitialized()) return 0;
    Py_Initialize();
    if (!Py_IsInitialized()) return -1;

    PyObject* sys = PyImport_ImportModule("sys");
    if (sys) {
        PyObject* path = PyObject_GetAttrString(sys, "path");
        if (path) {
            PyObject* vigo_path = PyUnicode_FromString("F:\\ViGo");
            PyList_Insert(path, 0, vigo_path);
            Py_DECREF(vigo_path);
            Py_DECREF(path);
        }
        Py_DECREF(sys);
    }

    /* Inject persistent registry and interpreter into Python's __main__ */
    PyObject* main_mod = PyImport_AddModule("__main__");
    if (main_mod) {
        PyObject* main_dict = PyModule_GetDict(main_mod);
        PyObject* interp = vigo_bridge_get_interpreter();
        if (interp) {
            PyDict_SetItemString(main_dict, "_vigo_interp", interp);
            PyObject* env = PyObject_GetAttrString(interp, "global_env");
            if (env) {
                PyDict_SetItemString(main_dict, "_vigo_env", env);
                Py_XDECREF(g_global_env);
                g_global_env = env;
                Py_INCREF(g_global_env);
                Py_DECREF(env);
            }
            Py_DECREF(interp);
        }
        PyObject* registry = vigo_bridge_get_persistent_registry();
        if (registry) {
            PyDict_SetItemString(main_dict, "_vigo_registry", registry);
            Py_DECREF(registry);
        }
    }

    return 0;
}

void vigo_bridge_py_finalize(void) {
    Py_XDECREF(g_interpreter);
    Py_XDECREF(g_ai_client);
    Py_XDECREF(g_global_env);
    Py_XDECREF(g_persistent_registry);
    g_interpreter = NULL;
    g_ai_client = NULL;
    g_global_env = NULL;
    g_persistent_registry = NULL;
}

PyObject* vigo_bridge_get_interpreter(void) {
    if (g_interpreter) { Py_INCREF(g_interpreter); return g_interpreter; }
    PyObject* vigo_module = PyImport_ImportModule("vigo");
    if (!vigo_module) { PyErr_Print(); return NULL; }
    PyObject* interp_class = PyObject_GetAttrString(vigo_module, "Interpreter");
    Py_DECREF(vigo_module);
    if (!interp_class) { PyErr_Print(); return NULL; }
    PyObject* interp = PyObject_CallObject(interp_class, NULL);
    Py_DECREF(interp_class);
    if (!interp) { PyErr_Print(); return NULL; }
    PyObject* stdlib = PyImport_ImportModule("vigo.stdlib");
    if (stdlib) {
        PyObject* register_all = PyObject_GetAttrString(stdlib, "register_all");
        if (register_all) {
            PyObject* env = PyObject_GetAttrString(interp, "global_env");
            if (env) { PyObject_CallFunctionObjArgs(register_all, env, NULL); Py_DECREF(env); }
            Py_DECREF(register_all);
        }
        Py_DECREF(stdlib);
    }
    g_interpreter = interp;
    Py_INCREF(g_interpreter);
    /* Sync persistent registry into Python's __main__ */
    PyObject* main_mod = PyImport_AddModule("__main__");
    if (main_mod) {
        PyObject* main_dict = PyModule_GetDict(main_mod);
        PyObject* registry = vigo_bridge_get_persistent_registry();
        if (registry) {
            PyDict_SetItemString(main_dict, "_vigo_registry", registry);
            Py_DECREF(registry);
        }
    }
    return interp;
}

PyObject* vigo_bridge_get_ai_client(void) {
    if (g_ai_client) { Py_INCREF(g_ai_client); return g_ai_client; }
    PyObject* ailib = PyImport_ImportModule("vigo.stdlib.ailib");
    if (!ailib) { PyErr_Print(); return NULL; }
    PyObject* ai = PyObject_GetAttrString(ailib, "_ai");
    Py_DECREF(ailib);
    if (!ai) { PyErr_Print(); return NULL; }
    g_ai_client = ai;
    Py_INCREF(g_ai_client);
    return ai;
}

PyObject* vigo_bridge_get_global_env(void) {
    if (!g_global_env) {
        PyObject* interp = vigo_bridge_get_interpreter();
        if (interp) { g_global_env = PyObject_GetAttrString(interp, "global_env"); Py_DECREF(interp); }
    }
    if (g_global_env) Py_INCREF(g_global_env);
    return g_global_env;
}

PyObject* vigo_bridge_get_persistent_registry(void) {
    if (!g_persistent_registry) {
        g_persistent_registry = PyDict_New();
    }
    Py_INCREF(g_persistent_registry);
    return g_persistent_registry;
}

void vigo_bridge_reset_interpreter(void) {
    Py_XDECREF(g_interpreter);
    Py_XDECREF(g_global_env);
    g_interpreter = NULL;
    g_global_env = NULL;
}

PyObject* vigo_bridge_run_string(const char* source) {
    PyObject* main_module = PyImport_AddModule("__main__");
    if (!main_module) return NULL;
    PyObject* main_dict = PyModule_GetDict(main_module);
    PyObject* interp = vigo_bridge_get_interpreter();
    if (!interp) return NULL;
    char py_code[4096];
    snprintf(py_code, sizeof(py_code),
        "from vigo.runtime.interpreter import run_vigo\n_result = run_vigo(\"%s\")\n", source);
    PyObject* result = PyRun_String(py_code, Py_file_input, main_dict, main_dict);
    if (!result) { PyErr_Print(); Py_DECREF(interp); return NULL; }
    Py_DECREF(result);
    PyObject* py_result = PyDict_GetItemString(main_dict, "_result");
    Py_XINCREF(py_result);
    Py_DECREF(interp);
    return py_result;
}

PyObject* vigo_bridge_c_to_py(VigoValue* value) {
    if (!value) Py_RETURN_NONE;
    switch (value->type) {
        case VIGO_NULL: Py_RETURN_NONE;
        case VIGO_BOOL: if (value->data.bool_val) Py_RETURN_TRUE; else Py_RETURN_FALSE;
        case VIGO_NUMBER: return PyFloat_FromDouble(value->data.number_val);
        case VIGO_STRING: return PyUnicode_FromString(value->data.string_val ? value->data.string_val : "");
        case VIGO_LIST: {
            PyObject* list = PyList_New(value->data.list.size);
            for (int i = 0; i < value->data.list.size; i++) {
                PyObject* item = vigo_bridge_c_to_py(value->data.list.items[i]);
                PyList_SetItem(list, i, item ? item : Py_None);
            }
            return list;
        }
        default: Py_RETURN_NONE;
    }
}

VigoValue* vigo_bridge_py_to_c(PyObject* obj) {
    if (!obj || obj == Py_None) return vigo_new_null();
    if (PyBool_Check(obj)) return vigo_new_bool(obj == Py_True ? 1 : 0);
    if (PyLong_Check(obj)) return vigo_new_number((double)PyLong_AsLong(obj));
    if (PyFloat_Check(obj)) return vigo_new_number(PyFloat_AsDouble(obj));
    if (PyUnicode_Check(obj)) { const char* s = PyUnicode_AsUTF8(obj); return vigo_new_string(s ? s : ""); }
    if (PyList_Check(obj)) {
        Py_ssize_t size = PyList_Size(obj);
        VigoValue** items = (VigoValue**)calloc(size, sizeof(VigoValue*));
        for (Py_ssize_t i = 0; i < size; i++) items[i] = vigo_bridge_py_to_c(PyList_GetItem(obj, i));
        VigoValue* list = vigo_new_list((int)size, items);
        for (Py_ssize_t i = 0; i < size; i++) vigo_value_free(items[i]);
        free(items);
        return list;
    }
    PyObject* str_obj = PyObject_Str(obj);
    if (str_obj) { const char* s = PyUnicode_AsUTF8(str_obj); VigoValue* r = vigo_new_string(s ? s : ""); Py_DECREF(str_obj); return r; }
    return vigo_new_null();
}

VigoValueType vigo_bridge_py_type_to_vigo(PyObject* obj) {
    if (!obj || obj == Py_None) return VIGO_NULL;
    if (PyBool_Check(obj)) return VIGO_BOOL;
    if (PyLong_Check(obj) || PyFloat_Check(obj)) return VIGO_NUMBER;
    if (PyUnicode_Check(obj)) return VIGO_STRING;
    if (PyList_Check(obj)) return VIGO_LIST;
    return VIGO_NULL;
}

void vigo_bridge_set_error(VigoEngine* engine, const char* format, ...) {
    if (!engine) return;
    VIGO_FREE(engine->last_error);
    va_list args;
    va_start(args, format);
    int len = vsnprintf(NULL, 0, format, args);
    va_end(args);
    if (len > 0) {
        engine->last_error = (char*)malloc(len + 1);
        va_start(args, format);
        vsnprintf(engine->last_error, len + 1, format, args);
        va_end(args);
    }
}

void vigo_bridge_set_error_type(VigoEngine* engine, VigoErrorType type, const char* format, ...) {
    if (!engine) return;
    engine->error_type = type;
    VIGO_FREE(engine->last_error);
    va_list args;
    va_start(args, format);
    int len = vsnprintf(NULL, 0, format, args);
    va_end(args);
    if (len > 0) {
        engine->last_error = (char*)malloc(len + 1);
        va_start(args, format);
        vsnprintf(engine->last_error, len + 1, format, args);
        va_end(args);
    }
}

int vigo_bridge_has_error(VigoEngine* engine) {
    return engine && engine->last_error && engine->last_error[0] != '\0';
}

void vigo_bridge_clear_error(VigoEngine* engine) {
    if (engine) VIGO_FREE(engine->last_error);
}