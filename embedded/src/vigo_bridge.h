#ifndef VIGO_BRIDGE_H
#define VIGO_BRIDGE_H

#include <Python.h>
#include "../include/vigo.h"

int  vigo_bridge_py_init(void);
void vigo_bridge_py_finalize(void);

PyObject* vigo_bridge_get_interpreter(void);
PyObject* vigo_bridge_get_ai_client(void);
PyObject* vigo_bridge_get_global_env(void);
PyObject* vigo_bridge_get_persistent_registry(void);
PyObject* vigo_bridge_run_string(const char* source);

PyObject*    vigo_bridge_c_to_py(VigoValue* value);
VigoValue*   vigo_bridge_py_to_c(PyObject* obj);
VigoValueType vigo_bridge_py_type_to_vigo(PyObject* obj);

void vigo_bridge_set_error(VigoEngine* engine, const char* format, ...);
void vigo_bridge_set_error_type(VigoEngine* engine, VigoErrorType type, const char* format, ...);
int  vigo_bridge_has_error(VigoEngine* engine);
void vigo_bridge_clear_error(VigoEngine* engine);
void vigo_bridge_reset_interpreter(void);

#endif /* VIGO_BRIDGE_H */