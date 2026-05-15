#ifndef VIGO_UTILS_H
#define VIGO_UTILS_H

#include <stdlib.h>
#include <string.h>

/* ── Memory ── */
#define VIGO_ALLOC(type)  (type*)calloc(1, sizeof(type))
#define VIGO_FREE(ptr)    do { if (ptr) { free(ptr); (ptr) = NULL; } } while(0)

/* ── String ── */
char* vigo_strdup(const char* src);
int   vigo_str_empty(const char* s);

#endif /* VIGO_UTILS_H */