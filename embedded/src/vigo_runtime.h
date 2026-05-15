#ifndef VIGO_RUNTIME_H
#define VIGO_RUNTIME_H

#include "../include/vigo.h"

struct VigoEngine {
    void* bridge_state;
    char* last_error;
    VigoErrorType error_type;
    int initialized;
};

#endif /* VIGO_RUNTIME_H */