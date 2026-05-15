#include "vigo_runtime.h"
#include "vigo_bridge.h"
#include "vigo_utils.h"

VigoEngine* vigo_init(void) {
    if (vigo_bridge_py_init() != 0) return NULL;
    VigoEngine* engine = VIGO_ALLOC(VigoEngine);
    if (!engine) return NULL;
    engine->initialized = 1;
    engine->error_type = VIGO_ERR_NONE;
    engine->last_error = NULL;
    PyObject* interp = vigo_bridge_get_interpreter();
    if (!interp) { VIGO_FREE(engine); return NULL; }
    Py_DECREF(interp);
    PyObject* ai = vigo_bridge_get_ai_client();
    if (!ai) { VIGO_FREE(engine); return NULL; }
    Py_DECREF(ai);
    return engine;
}

void vigo_destroy(VigoEngine* engine) {
    if (!engine) return;
    VIGO_FREE(engine->last_error);
    VIGO_FREE(engine);
    vigo_bridge_py_finalize();
}

void vigo_reset(VigoEngine* engine) {
    if (!engine) return;
    VIGO_FREE(engine->last_error);
    engine->last_error = NULL;
    engine->error_type = VIGO_ERR_NONE;
    vigo_bridge_reset_interpreter();
    PyObject* interp = vigo_bridge_get_interpreter();
    if (interp) Py_DECREF(interp);
}

const char* vigo_get_last_error(VigoEngine* engine) {
    if (!engine || !engine->last_error) return "";
    return engine->last_error;
}

VigoErrorType vigo_get_last_error_type(VigoEngine* engine) {
    if (!engine) return VIGO_ERR_NONE;
    return engine->error_type;
}