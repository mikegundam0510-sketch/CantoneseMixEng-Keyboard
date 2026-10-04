#pragma once
#include <vector>
#include <array>
#include <string>
#include <fstream>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <set>
#include <limits>
namespace hkhw {
struct Point {int stroke,x,y;};
struct Shape {std::string word;int strokes;std::vector<uint16_t> pixels;std::array<uint8_t,1024> distance;};
inline std::array<uint8_t,1024> field(const std::vector<uint16_t>& pixels){
 std::array<uint8_t,1024>d;d.fill(64);for(auto p:pixels)d[p]=0;
 for(int y=0;y<32;y++)for(int x=0;x<32;x++){int i=y*32+x;if(x)d[i]=std::min<int>(d[i],d[i-1]+1);if(y)d[i]=std::min<int>(d[i],d[i-32]+1);}
 for(int y=31;y>=0;y--)for(int x=31;x>=0;x--){int i=y*32+x;if(x<31)d[i]=std::min<int>(d[i],d[i+1]+1);if(y<31)d[i]=std::min<int>(d[i],d[i+32]+1);}
 return d;
}
inline std::vector<uint16_t> raster(const std::vector<Point>&points){
 if(points.empty())return {};
 int lx=1000,rx=0,ty=1000,by=0;for(auto p:points){lx=std::min(lx,p.x);rx=std::max(rx,p.x);ty=std::min(ty,p.y);by=std::max(by,p.y);}
 float scale=24.f/std::max(1,std::max(rx-lx,by-ty)),cx=(lx+rx)/2.f,cy=(ty+by)/2.f;
 std::array<bool,1024>ink{};int previous=-1,px=0,py=0;
 for(auto p:points){int x=std::max(0,std::min(31,(int)std::lround((p.x-cx)*scale+15.5f))),y=std::max(0,std::min(31,(int)std::lround((p.y-cy)*scale+15.5f)));
  if(p.stroke==previous){int steps=std::max(std::abs(x-px),std::abs(y-py));for(int t=0;t<=steps;t++){int xx=steps?std::lround(px+(x-px)*t/(float)steps):x,yy=steps?std::lround(py+(y-py)*t/(float)steps):y;ink[yy*32+xx]=true;}}
  else ink[y*32+x]=true;previous=p.stroke;px=x;py=y;
 }
 std::vector<uint16_t>out;for(int i=0;i<1024;i++)if(ink[i])out.push_back(i);return out;
}
class Matcher {
 std::vector<Shape> shapes;
 public:
 bool open(const char*path){
  std::ifstream in(path,std::ios::binary);char magic[4];uint32_t count=0;in.read(magic,4);in.read((char*)&count,4);
  if(!in||std::string(magic,4)!="HKS1"||count>30000)return false;
  std::vector<Shape> parsed;parsed.reserve(count);
  for(uint32_t i=0;i<count;i++){char word[16];uint16_t strokes,n;in.read(word,16);in.read((char*)&strokes,2);in.read((char*)&n,2);
   if(!in||!n||n>1024||!strokes||strokes>48||!std::memchr(word,0,16))return false;
   Shape s;s.word=word;s.strokes=strokes;s.pixels.resize(n);in.read((char*)s.pixels.data(),n*2);
   if(!in||std::any_of(s.pixels.begin(),s.pixels.end(),[](uint16_t p){return p>=1024;}))return false;
   s.distance=field(s.pixels);parsed.push_back(std::move(s));
  }shapes.swap(parsed);return !shapes.empty();
 }
 std::vector<std::pair<std::string,float>> classify(const std::vector<Point>&points,int limit=32)const{
  auto pixels=raster(points);if(pixels.empty())return {};auto distances=field(pixels);int strokes=points.back().stroke+1;
  std::vector<std::pair<float,size_t>>scores;scores.reserve(shapes.size());
  for(size_t i=0;i<shapes.size();i++){const auto&s=shapes[i];float sum=0,reverse=0;for(auto p:s.pixels)sum+=distances[p];for(auto p:pixels)reverse+=s.distance[p];
   float score=sum/s.pixels.size()+reverse/pixels.size()+.08f*std::abs(strokes-s.strokes)+.3f*std::abs(std::log((float)s.pixels.size()/pixels.size()));scores.emplace_back(score,i);
  }
  size_t n=std::min(scores.size(),(size_t)limit*3);std::partial_sort(scores.begin(),scores.begin()+n,scores.end());
  std::vector<std::pair<std::string,float>>out;std::set<std::string>seen;
  for(size_t k=0;k<n&&out.size()<(size_t)limit;k++){auto&word=shapes[scores[k].second].word;if(seen.insert(word).second)out.emplace_back(word,scores[k].first);}return out;
 }
};
}
