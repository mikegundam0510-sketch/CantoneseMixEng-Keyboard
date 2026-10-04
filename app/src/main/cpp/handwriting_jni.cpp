#include <jni.h>
#include <memory>
#include <vector>
#include <map>
#include "zinnia/zinnia.h"
#include "handwriting_shape.h"
struct HandwritingRecognizer {std::unique_ptr<zinnia::Recognizer> stroke;hkhw::Matcher shape;};
extern "C" JNIEXPORT jlong JNICALL Java_hk_kaiboard_android_HandwritingEngine_open(JNIEnv* env,jclass,jstring path,jstring shapePath) {
 const char* file=env->GetStringUTFChars(path,nullptr);const char* shapes=env->GetStringUTFChars(shapePath,nullptr);
 std::unique_ptr<HandwritingRecognizer> r(new HandwritingRecognizer());r->stroke.reset(zinnia::Recognizer::create());
 bool ok=r->stroke->open(file)&&r->shape.open(shapes);env->ReleaseStringUTFChars(path,file);env->ReleaseStringUTFChars(shapePath,shapes);
 return ok?reinterpret_cast<jlong>(r.release()):0;
}
extern "C" JNIEXPORT void JNICALL Java_hk_kaiboard_android_HandwritingEngine_close(JNIEnv*,jclass,jlong handle){delete reinterpret_cast<HandwritingRecognizer*>(handle);}
extern "C" JNIEXPORT jobjectArray JNICALL Java_hk_kaiboard_android_HandwritingEngine_recognize(JNIEnv* env,jclass,jlong handle,jintArray input){
 auto empty=[&](){return env->NewObjectArray(0,env->FindClass("java/lang/String"),nullptr);};
 if(!handle)return empty();int n=env->GetArrayLength(input);if(n<3||n%3||n>6144)return empty();
 std::vector<jint> data(n);env->GetIntArrayRegion(input,0,n,data.data());std::vector<hkhw::Point>points;points.reserve(n/3);
 int previous=0,lx=1000,rx=0,ty=1000,by=0;
 for(int i=0;i<n;i+=3){int stroke=data[i],x=data[i+1],y=data[i+2];if(stroke<previous||stroke>47||x<0||x>1000||y<0||y>1000)return empty();
  previous=stroke;points.push_back({stroke,x,y});lx=std::min(lx,x);rx=std::max(rx,x);ty=std::min(ty,y);by=std::max(by,y);
 }
 auto*r=reinterpret_cast<HandwritingRecognizer*>(handle);
 std::unique_ptr<zinnia::Character> c(zinnia::Character::create());c->set_width(1000);c->set_height(1000);
 float scale=800.f/std::max(1,std::max(rx-lx,by-ty)),cx=(lx+rx)/2.f,cy=(ty+by)/2.f;
 for(auto p:points)c->add(p.stroke,std::lround((p.x-cx)*scale+500),std::lround((p.y-cy)*scale+500));
 std::unique_ptr<zinnia::Result> stroke(r->stroke->classify(*c,32));auto shape=r->shape.classify(points,32);
 std::map<std::string,float> scores;
 for(size_t i=0;i<shape.size();i++)scores[shape[i].first]+=.85f/(2+i);
 if(stroke)for(size_t i=0;i<stroke->size();i++)scores[stroke->value(i)]+=.15f/(2+i);
 std::vector<std::pair<float,std::string>> ranked;for(auto&s:scores)ranked.emplace_back(s.second,s.first);std::sort(ranked.rbegin(),ranked.rend());
 size_t count=std::min(ranked.size(),(size_t)24);auto out=env->NewObjectArray(count,env->FindClass("java/lang/String"),nullptr);
 for(size_t i=0;i<count;i++){auto word=env->NewStringUTF(ranked[i].second.c_str());env->SetObjectArrayElement(out,i,word);env->DeleteLocalRef(word);}return out;
}
