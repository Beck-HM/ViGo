#ifndef VIGO_H
#define VIGO_H

#ifdef __cplusplus
extern "C" {
#endif

typedef struct VigoEngine VigoEngine;
typedef struct VigoValue VigoValue;
typedef struct VigoAgent VigoAgent;

typedef enum {
    VIGO_NULL   = 0,
    VIGO_BOOL   = 1,
    VIGO_NUMBER = 2,
    VIGO_STRING = 3,
    VIGO_LIST   = 4,
} VigoValueType;

typedef enum {
    VIGO_ERR_NONE    = 0,
    VIGO_ERR_SYNTAX  = 1,
    VIGO_ERR_RUNTIME = 2,
    VIGO_ERR_AI      = 3,
    VIGO_ERR_NETWORK = 4,
} VigoErrorType;

const char*   vigo_get_last_error(VigoEngine* engine);
VigoErrorType vigo_get_last_error_type(VigoEngine* engine);

VigoEngine* vigo_init(void);
void        vigo_destroy(VigoEngine* engine);
void        vigo_reset(VigoEngine* engine);

VigoValue*  vigo_eval(VigoEngine* engine, const char* source);
VigoValue*  vigo_eval_file(VigoEngine* engine, const char* filepath);
int         vigo_eval_bool(VigoEngine* engine, const char* source);
const char* vigo_eval_string(VigoEngine* engine, const char* source);
double      vigo_eval_number(VigoEngine* engine, const char* source);

typedef VigoValue* (*VigoCFunction)(VigoEngine* engine, int argc, VigoValue** argv);

void vigo_register(VigoEngine* engine, const char* name, VigoCFunction func);
VigoValue* vigo_call(VigoEngine* engine, const char* name, int argc, VigoValue** argv);

VigoValue* vigo_new_null(void);
VigoValue* vigo_new_bool(int value);
VigoValue* vigo_new_number(double value);
VigoValue* vigo_new_string(const char* value);
VigoValue* vigo_new_list(int size, VigoValue** items);

VigoValueType vigo_value_type(VigoValue* value);

int    vigo_value_to_bool(VigoValue* value);
double vigo_value_to_number(VigoValue* value);
const char* vigo_value_to_string(VigoValue* value);

int        vigo_list_size(VigoValue* list);
VigoValue* vigo_list_get(VigoValue* list, int index);

void vigo_value_free(VigoValue* value);
void vigo_string_free(const char* str);

void        vigo_ai_set_key(VigoEngine* engine, const char* key);
void        vigo_ai_set_provider(VigoEngine* engine, const char* provider);
const char* vigo_ai_ask(VigoEngine* engine, const char* prompt);
const char* vigo_ai_ask_model(VigoEngine* engine, const char* prompt,
                               const char* model, double temp, int max_tokens);

VigoAgent*  vigo_ai_create_agent(VigoEngine* engine, const char* model,
                                  int max_steps, int verbose);
void        vigo_ai_agent_add_tool(VigoAgent* agent, const char* name,
                                    VigoCFunction func, const char* description);
const char* vigo_ai_agent_run(VigoAgent* agent, const char* task);
void        vigo_ai_destroy_agent(VigoAgent* agent);

#ifdef __cplusplus
}
#endif

#endif /* VIGO_H */