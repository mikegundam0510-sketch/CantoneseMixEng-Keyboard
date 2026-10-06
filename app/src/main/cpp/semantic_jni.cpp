#include "semantic_core.h"
#include <jni.h>
#include <memory>
#include <mutex>
#include <unordered_map>

static std::mutex handles_mutex;
static std::unordered_map<jlong,std::shared_ptr<SemanticCore>> handles;
static jlong next_handle=1;
static std::shared_ptr<SemanticCore> get(jlong handle) {
    std::lock_guard<std::mutex> lock(handles_mutex);
    auto found=handles.find(handle); return found==handles.end()?nullptr:found->second;
}
static std::string bytes(JNIEnv *env,jbyteArray array) {
    std::string value(env->GetArrayLength(array),'\0');
    env->GetByteArrayRegion(array,0,value.size(),reinterpret_cast<jbyte*>(value.data())); return value;
}
extern "C" JNIEXPORT jlong JNICALL Java_hk_kaiboard_android_SemanticNative_nativeLoad(JNIEnv *env,jclass,jbyteArray path,jint threads) {
    try {
        auto model=std::make_shared<SemanticCore>(bytes(env,path),std::max(1,std::min(4,threads)));
        std::lock_guard<std::mutex> lock(handles_mutex);
        jlong id=next_handle++;handles.emplace(id,model);return id;
    } catch (...) { return 0; }
}
extern "C" JNIEXPORT jfloatArray JNICALL Java_hk_kaiboard_android_SemanticNative_nativeRank(JNIEnv *env,jclass,jlong handle,jbyteArray prompt,jint count,jint budget) {
    auto model=get(handle); if(!model)return nullptr;
    try {
        auto result=model->rank(bytes(env,prompt),count,std::max(1,std::min(60000,budget)));
        if(result.empty())return nullptr;
        auto array=env->NewFloatArray(result.size());
        if(array)env->SetFloatArrayRegion(array,0,result.size(),result.data());return array;
    } catch (...) { return nullptr; }
}
extern "C" JNIEXPORT void JNICALL Java_hk_kaiboard_android_SemanticNative_nativeCancel(JNIEnv*,jclass,jlong handle) {
    auto model=get(handle); if(model)model->cancel();
}
extern "C" JNIEXPORT void JNICALL Java_hk_kaiboard_android_SemanticNative_nativeClose(JNIEnv*,jclass,jlong handle) {
    auto model=get(handle); if(model)model->cancel();
    std::lock_guard<std::mutex> lock(handles_mutex);handles.erase(handle);
}

extern "C" JNIEXPORT void JNICALL Java_hk_kaiboard_android_SemanticNative_nativeArm(JNIEnv*,jclass,jlong handle) {
    auto model=get(handle); if(model)model->arm();
}

extern "C" JNIEXPORT jint JNICALL Java_hk_kaiboard_android_SemanticNative_nativeModelCount(JNIEnv*,jclass) {
    std::lock_guard<std::mutex> lock(handles_mutex);return handles.size();
}
