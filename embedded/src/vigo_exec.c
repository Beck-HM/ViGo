#include "vigo_exec.h"
#include "vigo_runtime.h"
#include "vigo_bridge.h"
#include "vigo_value.h"
#include "vigo_utils.h"
#include <stdio.h>
#include <stdlib.h>

static PyObject* exec_source(VigoEngine* engine, const char* source) {
    if (!engine || !engine->initialized) return NULL;
    if (vigo_str_empty(source)) return NULL;
    PyObject* main_module = PyImport_AddModule("__main__");
    if (!main_module) return NULL;
    PyObject* main_dict = PyModule_GetDict(main_module);
    char py_code[8192];
    snprintf(py_code, sizeof(py_code),
        "from vigo.lexer.lexer import Lexer\n"
        "from vigo.parser.parser import Parser\n"
        "from vigo.runtime.objects import BuiltinFunction\n"
        "for _name, _func in _vigo_registry.items():\n"
        "    _vigo_interp.global_env.define(_name, BuiltinFunction(_func, _name))\n"
        "_ast = Parser(Lexer(\"\"\"%s\"\"\")).parse_program()\n"
        "_result = _vigo_interp.interpret(_ast)\n",
        source);
    PyObject* result = PyRun_String(py_code, Py_file_input, main_dict, main_dict);
    if (!result) {
        vigo_bridge_set_error_type(engine, VIGO_ERR_SYNTAX, "ViGo syntax error in: %s", source);
        PyErr_Print(); PyErr_Clear();
        return NULL;
    }
    if (!result) { PyErr_Print(); PyErr_Clear(); return NULL; }
    Py_DECREF(result);
    PyObject* py_result = PyDict_GetItemString(main_dict, "_result");
    if (!py_result) {
        vigo_bridge_set_error_type(engine, VIGO_ERR_RUNTIME, "ViGo execution failed: %s", source);
        return NULL;
    }
    Py_XINCREF(py_result);
    return py_result;
    Py_XINCREF(py_result);
    return py_result;
}

VigoValue* vigo_eval(VigoEngine* engine, const char* source) {
    PyObject* py_result = exec_source(engine, source);
    if (!py_result) return NULL;
    return vigo_bridge_py_to_c(py_result);
}

VigoValue* vigo_eval_file(VigoEngine* engine, const char* filepath) {
    if (!engine || vigo_str_empty(filepath)) return NULL;
    FILE* f = fopen(filepath, "r");
    if (!f) { vigo_bridge_set_error(engine, "Cannot open file: %s", filepath); return NULL; }
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    char* source = (char*)malloc(size + 1);
    if (!source) { fclose(f); return NULL; }
    size_t read_size = fread(source, 1, size, f);
    source[read_size] = '\0';
    fclose(f);
    VigoValue* result = vigo_eval(engine, source);
    free(source);
    return result;
}

int vigo_eval_bool(VigoEngine* engine, const char* source) {
    VigoValue* v = vigo_eval(engine, source);
    int result = vigo_value_to_bool(v);
    vigo_value_free(v);
    return result;
}

const char* vigo_eval_string(VigoEngine* engine, const char* source) {
    VigoValue* v = vigo_eval(engine, source);
    static char buf[4096];
    const char* s = vigo_value_to_string(v);
    snprintf(buf, sizeof(buf), "%s", s);
    vigo_value_free(v);
    return buf;
}

double vigo_eval_number(VigoEngine* engine, const char* source) {
    VigoValue* v = vigo_eval(engine, source);
    double result = vigo_value_to_number(v);
    vigo_value_free(v);
    return result;
}