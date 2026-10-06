// Host-only experiment: compare continuation likelihood without candidate label/position bias.
#include "llama.h"
#include <algorithm>
#include <cmath>
#include <chrono>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>
static void silent(enum ggml_log_level,const char*,void*){}
static std::vector<llama_token> tokenize(const llama_vocab *v,const std::string &s){
    int n=-llama_tokenize(v,s.data(),s.size(),nullptr,0,false,false);
    if(n<=0)throw std::runtime_error("Tokenization");
    std::vector<llama_token> t(n);llama_tokenize(v,s.data(),s.size(),t.data(),n,false,false);return t;
}
static double log_probability(const float *logits,int n,llama_token token){
    float maximum=*std::max_element(logits,logits+n);double sum=0;
    for(int i=0;i<n;i++)sum+=std::exp(double(logits[i]-maximum));
    return logits[token]-maximum-std::log(sum);
}
int main(int argc,char **argv){
    if(argc!=3)return 2;
    llama_log_set(silent,nullptr);llama_backend_init();
    auto mp=llama_model_default_params();mp.n_gpu_layers=0;mp.load_mode=LLAMA_LOAD_MODE_MMAP;
    auto *model=llama_model_load_from_file(argv[1],mp);if(!model)return 3;
    auto cp=llama_context_default_params();cp.n_ctx=1024;cp.n_batch=256;cp.n_ubatch=128;cp.n_threads=2;cp.n_threads_batch=2;
    auto *ctx=llama_init_from_model(model,cp);if(!ctx)return 4;
    auto *vocab=llama_model_get_vocab(model);int vocabulary=llama_vocab_n_tokens(vocab);
    std::ifstream manifest(argv[2]);std::string path;
    while(std::getline(manifest,path)){
        std::ifstream data(path);std::string context,candidate;std::getline(data,context);
        std::vector<std::string> candidates;while(std::getline(data,candidate))candidates.push_back(candidate);
        auto start=std::chrono::steady_clock::now();
        // No chat-template delimiters are parsed from editor data.
        std::string prefix="粵語對話：\n"+context;
        std::vector<std::vector<llama_token>> sequences;
        for(const auto &s:candidates)sequences.push_back(tokenize(vocab,prefix+s));
        auto base=tokenize(vocab,prefix);size_t shared=base.size();
        for(const auto &tokens:sequences){
            shared=std::min(shared,tokens.size());size_t i=0;
            while(i<shared&&base[i]==tokens[i])i++;shared=i;
        }
        if(!shared)return 5;
        llama_memory_clear(llama_get_memory(ctx),true);
        auto batch=llama_batch_get_one(base.data(),shared);if(llama_decode(ctx,batch))return 6;
        const float *initial=llama_get_logits_ith(ctx,-1);
        std::vector<float> first(initial,initial+vocabulary);std::vector<double> scores;
        for(const auto &tokens:sequences){
            if(!llama_memory_seq_rm(llama_get_memory(ctx),0,shared,-1))return 7;
            int n=tokens.size()-shared;if(n<=0||tokens.size()>1000)return 8;
            auto continuation=llama_batch_init(n,0,1);continuation.n_tokens=n;
            for(int i=0;i<n;i++){
                continuation.token[i]=tokens[shared+i];continuation.pos[i]=shared+i;
                continuation.n_seq_id[i]=1;continuation.seq_id[i][0]=0;continuation.logits[i]=1;
            }
            if(llama_decode(ctx,continuation))return 9;
            double score=log_probability(first.data(),vocabulary,tokens[shared]);
            for(int i=1;i<n;i++)score+=log_probability(llama_get_logits_ith(ctx,i-1),vocabulary,tokens[shared+i]);
            // Exact Quick candidates normally share character count; token count can differ substantially.
            scores.push_back(score);llama_batch_free(continuation);
        }
        llama_memory_clear(llama_get_memory(ctx),true);
        std::cout<<std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-start).count();
        for(double score:scores)std::cout<<'\t'<<score;std::cout<<std::endl;
    }
    llama_free(ctx);llama_model_free(model);
}
