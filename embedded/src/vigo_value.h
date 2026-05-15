#ifndef VIGO_VALUE_H
#define VIGO_VALUE_H

#include "../include/vigo.h"

/* ── Internal value structure ── */
struct VigoValue {
    VigoValueType type;
    union {
        int    bool_val;
        double number_val;
        char*  string_val;
        struct {
            VigoValue** items;
            int         size;
            int         capacity;
        } list;
    } data;
};

/* ── Internal helpers ── */
VigoValue* vigo_value_alloc(void);
void vigo_value_decref(VigoValue* value);

#endif /* VIGO_VALUE_H */