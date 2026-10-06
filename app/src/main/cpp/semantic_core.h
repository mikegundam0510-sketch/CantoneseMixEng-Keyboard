#pragma once
#include <atomic>
#include <string>
#include <vector>
#include "llama.h"

class SemanticCore {
public:
    SemanticCore(const std::string &path, int threads);
    ~SemanticCore();
    std::vector<float> rank(const std::string &prompt, int count, int budget_ms);
    void cancel() { cancelled.store(true); }
private:
    llama_model *model = nullptr;
    llama_context *context = nullptr;
    const llama_vocab *vocab = nullptr;
    std::atomic<bool> cancelled{false};
    int64_t deadline = 0;
    static bool abort(void *state);
};
