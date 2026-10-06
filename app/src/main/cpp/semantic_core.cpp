#include "semantic_core.h"
#include <chrono>
#include <cmath>
#include <stdexcept>

static int64_t now_ms() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}
static void silent_log(enum ggml_log_level, const char *, void *) {}
bool SemanticCore::abort(void *state) {
    auto *self = static_cast<SemanticCore *>(state);
    return self->cancelled.load() || now_ms() > self->deadline;
}
SemanticCore::SemanticCore(const std::string &path, int threads) {
    llama_log_set(silent_log, nullptr);
    llama_backend_init();
    auto mp = llama_model_default_params();
    mp.n_gpu_layers = 0; mp.load_mode = LLAMA_LOAD_MODE_MMAP;
    model = llama_model_load_from_file(path.c_str(), mp);
    if (!model) throw std::runtime_error("Model unavailable");
    vocab = llama_model_get_vocab(model);
    auto cp = llama_context_default_params();
    cp.n_ctx = 1024; cp.n_batch = 256; cp.n_ubatch = 128;
    cp.n_threads = threads; cp.n_threads_batch = threads;
    cp.abort_callback = abort; cp.abort_callback_data = this;
    context = llama_init_from_model(model, cp);
    if (!context) { llama_model_free(model); model = nullptr; throw std::runtime_error("Context unavailable"); }
}
SemanticCore::~SemanticCore() {
    if (context) llama_free(context);
    if (model) llama_model_free(model);
}
std::vector<float> SemanticCore::rank(const std::string &prompt, int count, int budget_ms) {
    if (count < 2 || count > 20) return {};
    cancelled.store(false); deadline = now_ms() + budget_ms;
    // Keep every request ephemeral. No KV/session serialization or prompt cache on disk.
    llama_memory_clear(llama_get_memory(context), true);
    int needed = -llama_tokenize(vocab, prompt.data(), prompt.size(), nullptr, 0, false, true);
    if (needed <= 0 || needed > 1000) return {};
    std::vector<llama_token> tokens(needed);
    if (llama_tokenize(vocab, prompt.data(), prompt.size(), tokens.data(), needed, false, true) != needed) return {};
    std::vector<float> result;
    for (int start = 0; start < needed; start += 256) {
        int size = std::min(256, needed - start);
        auto batch = llama_batch_get_one(tokens.data() + start, size);
        if (abort(this) || llama_decode(context, batch) != 0) {
            llama_memory_clear(llama_get_memory(context), true); return {};
        }
    }
    float *logits = llama_get_logits_ith(context, -1);
    for (int i = 0; i < count; i++) {
        char label = 'A' + i; llama_token token;
        if (llama_tokenize(vocab, &label, 1, &token, 1, false, false) != 1 || !std::isfinite(logits[token])) {
            result.clear(); break;
        }
        result.push_back(logits[token]);
    }
    llama_memory_clear(llama_get_memory(context), true);
    return result;
}
