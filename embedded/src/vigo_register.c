#include "vigo_register.h"
#include "vigo_bridge.h"
#include "vigo_value.h"
#include "vigo_utils.h"
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    VigoEngine* engine;
    VigoCFunction func;
} CFunctionWrapper;

static PyObject* cfunc_wrapper(PyObject* self, PyObject* args) {
    CFunctionWrapper* wrapper = (CFunctionWrapper*)PyCapsule_GetPointer(self, "vigo_cfunc");
    if (!wrapper) {
        PyErr_SetString(PyExc_RuntimeError, "CFunction wrapper not found");
        return NULL;
    }
    Py_ssize_t argc = PyTuple_Size(args);
    VigoValue** argv = (VigoValue**)calloc(argc, sizeof(VigoValue*));
    for (Py_ssize_t i = 0; i < argc; i++) {
        argv[i] = vigo_bridge_py_to_c(PyTuple_GetItem(args, i));
    }
    VigoValue* result = wrapper->func(wrapper->engine, (int)argc, argv);
    for (Py_ssize_t i = 0; i < argc; i++) {
        vigo_value_free(argv[i]);
    }
    free(argv);
    if (!result) { Py_RETURN_NONE; }
    PyObject* py_result = vigo_bridge_c_to_py(result);
    vigo_value_free(result);
    return py_result ? py_result : Py_None;
}

static PyMethodDef cfunc_methods[] = {
    {"__call__", (PyCFunction)cfunc_wrapper, METH_VARARGS, "Call the registered C function"},
    {NULL, NULL, 0, NULL}
};

void vigo_register(VigoEngine* engine, const char* name, VigoCFunction func) {
    if (!engine || vigo_str_empty(name) || !func) return;
    PyObject* interp = vigo_bridge_get_interpreter();
    if (!interp) return;
    CFunctionWrapper* wrapper = (CFunctionWrapper*)malloc(sizeof(CFunctionWrapper));
    wrapper->engine = engine;
    wrapper->func = func;
    PyObject* capsule = PyCapsule_New(wrapper, "vigo_cfunc", NULL);
    PyObject* callable = PyCFunction_New(cfunc_methods, capsule);
    Py_DECREF(capsule);
    if (!callable) { free(wrapper); Py_DECREF(interp); return; }
    PyObject* env = vigo_bridge_get_global_env();
    if (env) {
        PyObject* define = PyObject_GetAttrString(env, "define");
        if (define) {
            PyObject* py_name = PyUnicode_FromString(name);
            PyObject_CallFunctionObjArgs(define, py_name, callable, NULL);
            Py_DECREF(py_name);
            Py_DECREF(define);
        }
        Py_DECREF(env);
    }
    PyObject* registry = vigo_bridge_get_persistent_registry();
    if (registry) {
        PyObject* py_name = PyUnicode_FromString(name);
        PyDict_SetItem(registry, py_name, callable);
        Py_DECREF(py_name);
        Py_DECREF(registry);
    }
    Py_DECREF(callable);
    Py_DECREF(interp);
}

VigoValue* vigo_call(VigoEngine* engine, const char* name, int argc, VigoValue** argv) {
    if (!engine || vigo_str_empty(name)) return NULL;
    PyObject* registry = vigo_bridge_get_persistent_registry();
    if (!registry) return NULL;
    PyObject* py_name = PyUnicode_FromString(name);
    PyObject* py_func = PyDict_GetItem(registry, py_name);
    Py_XINCREF(py_func);
    Py_DECREF(py_name);
    if (!py_func) {
        vigo_bridge_set_error_type(engine, VIGO_ERR_RUNTIME, "Function '%s' not found in registry", name);
        return NULL;
    }
    PyObject* py_args = PyTuple_New(argc);
    for (int i = 0; i < argc; i++) {
        PyObject* py_arg = vigo_bridge_c_to_py(argv[i]);
        PyTuple_SetItem(py_args, i, py_arg ? py_arg : Py_None);
        Py_XINCREF(py_arg);
    }
    PyObject* py_result = PyObject_CallObject(py_func, py_args);
    Py_DECREF(py_args);
    Py_DECREF(py_func);
    if (!py_result) {
        PyErr_Print(); PyErr_Clear();
        vigo_bridge_set_error_type(engine, VIGO_ERR_RUNTIME, "Function '%s' not found in registry", name);
        return NULL;
    }
    VigoValue* result = vigo_bridge_py_to_c(py_result);
    Py_DECREF(py_result);
    return result;
}