#include "vigo_ai.h"
#include "vigo_bridge.h"
#include "vigo_utils.h"
#include <stdlib.h>
#include <stdio.h>

struct VigoAgent {
    PyObject* py_agent;
    VigoEngine* engine;
};

void vigo_ai_set_key(VigoEngine* engine, const char* key) {
    if (!engine || vigo_str_empty(key)) return;
    PyObject* ai = vigo_bridge_get_ai_client();
    if (!ai) return;
    PyObject* py_key = PyUnicode_FromString(key);
    PyObject* set_key = PyObject_GetAttrString(ai, "set_api_key");
    if (set_key) { PyObject_CallFunctionObjArgs(set_key, py_key, NULL); Py_DECREF(set_key); }
    Py_DECREF(py_key);
    Py_DECREF(ai);
}

void vigo_ai_set_provider(VigoEngine* engine, const char* provider) {
    if (!engine || vigo_str_empty(provider)) return;
    PyObject* ai = vigo_bridge_get_ai_client();
    if (!ai) return;
    PyObject* py_provider = PyUnicode_FromString(provider);
    PyObject* set_provider = PyObject_GetAttrString(ai, "set_provider");
    if (set_provider) { PyObject_CallFunctionObjArgs(set_provider, py_provider, NULL); Py_DECREF(set_provider); }
    Py_DECREF(py_provider);
    Py_DECREF(ai);
}

const char* vigo_ai_ask(VigoEngine* engine, const char* prompt) {
    return vigo_ai_ask_model(engine, prompt, NULL, 0.7, 2000);
}

const char* vigo_ai_ask_model(VigoEngine* engine, const char* prompt,
                               const char* model, double temp, int max_tokens) {
    if (!engine || vigo_str_empty(prompt)) return "";
    PyObject* ai = vigo_bridge_get_ai_client();
    if (!ai) {
        vigo_bridge_set_error_type(engine, VIGO_ERR_AI, "AI client not available");
        return "";
    }
    PyObject* py_prompt = PyUnicode_FromString(prompt);
    PyObject* py_model = model ? PyUnicode_FromString(model) : Py_None;
    PyObject* py_temp = PyFloat_FromDouble(temp);
    PyObject* py_max = PyLong_FromLong(max_tokens);
    PyObject* ask = PyObject_GetAttrString(ai, "ask");
    static char result_buf[8192];
    result_buf[0] = '\0';
    if (ask) {
        PyObject* py_result = PyObject_CallFunctionObjArgs(ask, py_prompt, py_model, py_temp, py_max, NULL);
        if (py_result) {
            const char* s = PyUnicode_AsUTF8(py_result);
            if (s) snprintf(result_buf, sizeof(result_buf), "%s", s);
            Py_DECREF(py_result);
        } else {
            vigo_bridge_set_error_type(engine, VIGO_ERR_AI, "AI call failed");
            PyErr_Print(); PyErr_Clear();
        }
        Py_DECREF(ask);
    }
    Py_DECREF(py_prompt);
    Py_DECREF(py_model);
    Py_DECREF(py_temp);
    Py_DECREF(py_max);
    Py_DECREF(ai);
    return result_buf;
}

VigoAgent* vigo_ai_create_agent(VigoEngine* engine, const char* model, int max_steps, int verbose) {
    if (!engine) return NULL;
    PyObject* ailib = PyImport_ImportModule("vigo.stdlib.ailib");
    if (!ailib) return NULL;
    PyObject* agent_class = PyObject_GetAttrString(ailib, "AIAgent");
    Py_DECREF(ailib);
    if (!agent_class) return NULL;
    PyObject* py_model = model ? PyUnicode_FromString(model) : Py_None;
    PyObject* py_steps = PyLong_FromLong(max_steps > 0 ? max_steps : 5);
    PyObject* py_verbose = PyBool_FromLong(verbose);
    PyObject* py_agent = PyObject_CallFunctionObjArgs(agent_class, py_model, py_steps, py_verbose, NULL);
    Py_DECREF(py_model);
    Py_DECREF(py_steps);
    Py_DECREF(py_verbose);
    Py_DECREF(agent_class);
    if (!py_agent) { PyErr_Print(); PyErr_Clear(); return NULL; }
    VigoAgent* agent = (VigoAgent*)malloc(sizeof(VigoAgent));
    agent->py_agent = py_agent;
    agent->engine = engine;
    return agent;
}

void vigo_ai_agent_add_tool(VigoAgent* agent, const char* name, VigoCFunction func, const char* description) {
    if (!agent || vigo_str_empty(name) || !func) return;
    vigo_register(agent->engine, name, func);
    PyObject* add_tool = PyObject_GetAttrString(agent->py_agent, "add_tool");
    if (!add_tool) return;
    PyObject* py_name = PyUnicode_FromString(name);
    PyObject* interp = vigo_bridge_get_interpreter();
    PyObject* env = PyObject_GetAttrString(interp, "global_env");
    PyObject* lookup = PyObject_GetAttrString(env, "lookup");
    PyObject* py_func = PyObject_CallFunctionObjArgs(lookup, py_name, NULL);
    PyObject* py_desc = PyUnicode_FromString(description ? description : "");
    PyObject_CallFunctionObjArgs(add_tool, py_name, py_func, py_desc, NULL);
    Py_DECREF(py_desc);
    Py_DECREF(py_func);
    Py_DECREF(lookup);
    Py_DECREF(env);
    Py_DECREF(interp);
    Py_DECREF(py_name);
    Py_DECREF(add_tool);
}

const char* vigo_ai_agent_run(VigoAgent* agent, const char* task) {
    if (!agent || vigo_str_empty(task)) return "";
    PyObject* run = PyObject_GetAttrString(agent->py_agent, "run");
    if (!run) return "";
    PyObject* py_task = PyUnicode_FromString(task);
    static char result_buf[8192];
    result_buf[0] = '\0';
    PyObject* py_result = PyObject_CallFunctionObjArgs(run, py_task, NULL);
    if (py_result) {
        const char* s = PyUnicode_AsUTF8(py_result);
        if (s) snprintf(result_buf, sizeof(result_buf), "%s", s);
        Py_DECREF(py_result);
    }
    Py_DECREF(py_task);
    Py_DECREF(run);
    return result_buf;
}

void vigo_ai_destroy_agent(VigoAgent* agent) {
    if (!agent) return;
    Py_XDECREF(agent->py_agent);
    free(agent);
}