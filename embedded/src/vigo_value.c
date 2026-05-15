#include "vigo_value.h"
#include "vigo_utils.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#define LIST_INITIAL_CAPACITY 8

VigoValue* vigo_value_alloc(void) {
    VigoValue* v = VIGO_ALLOC(VigoValue);
    if (v) {
        v->type = VIGO_NULL;
    }
    return v;
}

void vigo_value_decref(VigoValue* value) {
    if (!value) return;
    if (value->type == VIGO_STRING) {
        VIGO_FREE(value->data.string_val);
    } else if (value->type == VIGO_LIST) {
        for (int i = 0; i < value->data.list.size; i++) {
            vigo_value_decref(value->data.list.items[i]);
        }
        VIGO_FREE(value->data.list.items);
    }
    VIGO_FREE(value);
}

VigoValue* vigo_new_null(void) {
    return vigo_value_alloc();
}

VigoValue* vigo_new_bool(int value) {
    VigoValue* v = vigo_value_alloc();
    if (v) {
        v->type = VIGO_BOOL;
        v->data.bool_val = value ? 1 : 0;
    }
    return v;
}

VigoValue* vigo_new_number(double value) {
    VigoValue* v = vigo_value_alloc();
    if (v) {
        v->type = VIGO_NUMBER;
        v->data.number_val = value;
    }
    return v;
}

VigoValue* vigo_new_string(const char* value) {
    VigoValue* v = vigo_value_alloc();
    if (v) {
        v->type = VIGO_STRING;
        v->data.string_val = vigo_strdup(value ? value : "");
    }
    return v;
}

VigoValue* vigo_new_list(int size, VigoValue** items) {
    VigoValue* v = vigo_value_alloc();
    if (v) {
        v->type = VIGO_LIST;
        v->data.list.capacity = size > LIST_INITIAL_CAPACITY ? size : LIST_INITIAL_CAPACITY;
        v->data.list.size = size;
        v->data.list.items = (VigoValue**)calloc(v->data.list.capacity, sizeof(VigoValue*));
        if (items && size > 0) {
            memcpy(v->data.list.items, items, size * sizeof(VigoValue*));
        }
    }
    return v;
}

VigoValueType vigo_value_type(VigoValue* value) {
    return value ? value->type : VIGO_NULL;
}

int vigo_value_to_bool(VigoValue* value) {
    if (!value) return 0;
    switch (value->type) {
        case VIGO_BOOL:   return value->data.bool_val;
        case VIGO_NUMBER: return value->data.number_val != 0.0;
        case VIGO_STRING: return value->data.string_val && value->data.string_val[0];
        case VIGO_LIST:   return value->data.list.size > 0;
        default:          return 0;
    }
}

double vigo_value_to_number(VigoValue* value) {
    if (!value) return 0.0;
    switch (value->type) {
        case VIGO_NUMBER: return value->data.number_val;
        case VIGO_BOOL:   return value->data.bool_val ? 1.0 : 0.0;
        case VIGO_STRING: return value->data.string_val ? atof(value->data.string_val) : 0.0;
        default:          return 0.0;
    }
}

const char* vigo_value_to_string(VigoValue* value) {
    if (!value) return "";
    if (value->type == VIGO_STRING) {
        return value->data.string_val ? value->data.string_val : "";
    }
    static char buf[64];
    switch (value->type) {
        case VIGO_BOOL:   snprintf(buf, sizeof(buf), "%s", value->data.bool_val ? "ok" : "no"); break;
        case VIGO_NUMBER: snprintf(buf, sizeof(buf), "%g", value->data.number_val); break;
        case VIGO_NULL:   snprintf(buf, sizeof(buf), "null"); break;
        default:          snprintf(buf, sizeof(buf), "<value>"); break;
    }
    return buf;
}

int vigo_list_size(VigoValue* list) {
    if (!list || list->type != VIGO_LIST) return 0;
    return list->data.list.size;
}

VigoValue* vigo_list_get(VigoValue* list, int index) {
    if (!list || list->type != VIGO_LIST) return NULL;
    if (index < 0 || index >= list->data.list.size) return NULL;
    return list->data.list.items[index];
}

void vigo_value_free(VigoValue* value) {
    vigo_value_decref(value);
}

void vigo_string_free(const char* str) {
    (void)str;
}