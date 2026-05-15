#include "vigo_utils.h"

char* vigo_strdup(const char* src) {
    if (!src) return NULL;
    size_t len = strlen(src);
    char* dst = (char*)malloc(len + 1);
    if (dst) {
        memcpy(dst, src, len + 1);
    }
    return dst;
}

int vigo_str_empty(const char* s) {
    return !s || !*s;
}