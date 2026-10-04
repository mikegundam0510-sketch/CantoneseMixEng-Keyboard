#include <jni.h>
#include <memory>
#include <vector>
#include "zinnia/zinnia.h"
extern "C" JNIEXPORT jlong JNICALL Java_hk_kaiboard_android_HandwritingEngine_open(JNIEnv* env,jclass,jstring path) {
  const char* file=env->GetStringUTFChars(path,nullptr);
  std::unique_ptr<zinnia::Recognizer> r(zinnia::Recognizer::create());
  bool ok=r->open(file);env->ReleaseStringUTFChars(path,file);
  return ok?reinterpret_cast<jlong>(r.release()):0;
}
extern "C" JNIEXPORT void JNICALL Java_hk_kaiboard_android_HandwritingEngine_close(JNIEnv*,jclass,jlong handle) {
  delete reinterpret_cast<zinnia::Recognizer*>(handle);
}
extern "C" JNIEXPORT jobjectArray JNICALL Java_hk_kaiboard_android_HandwritingEngine_recognize(JNIEnv* env,jclass,jlong handle,jintArray input) {
  auto empty=[&](){return env->NewObjectArray(0,env->FindClass("java/lang/String"),nullptr);};
  if(!handle)return empty();int n=env->GetArrayLength(input);if(n<3||n%3||n>6144)return empty();
  std::vector<jint> points(n);env->GetIntArrayRegion(input,0,n,points.data());
  std::unique_ptr<zinnia::Character> c(zinnia::Character::create());c->set_width(1000);c->set_height(1000);
  int previous=0;
  for(int i=0;i<n;i+=3){int stroke=points[i],x=points[i+1],y=points[i+2];
    if(stroke<previous||stroke>47||x<0||x>1000||y<0||y>1000)return empty();
    previous=stroke;c->add(stroke,x,y);
  }
  std::unique_ptr<zinnia::Result> result(reinterpret_cast<zinnia::Recognizer*>(handle)->classify(*c,16));
  if(!result)return empty();auto out=env->NewObjectArray(result->size(),env->FindClass("java/lang/String"),nullptr);
  for(size_t i=0;i<result->size();i++){auto word=env->NewStringUTF(result->value(i));env->SetObjectArrayElement(out,i,word);env->DeleteLocalRef(word);}
  return out;
}
