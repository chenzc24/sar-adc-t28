// One native PSF sample in memory; no full-waveform arrays. C++11, no PDK deps.
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
#include <sys/resource.h>
using namespace std;
string norm(string s){string r;for(char c:s)if(c!='\\')r+=char(tolower(c));return r;}
struct Pair {string a,b;int ai,bi;double peak=-1,time=0;};
int main(int argc,char**argv){try{
 if(argc!=5)throw runtime_error("input.psf selected.txt pairs.txt output_prefix");
 vector<string> selected;string line;ifstream sf(argv[2]);while(getline(sf,line)){if(!line.empty()&&line.back()=='\r')line.pop_back();if(!line.empty())selected.push_back(line);}
 vector<Pair> pairs;ifstream pf(argv[3]);while(getline(pf,line)){istringstream s(line);Pair p;s>>p.a>>p.b;if(!p.a.empty())pairs.push_back(p);}
 vector<char> ibuf(4*1024*1024),obuf(1024*1024);
 ifstream in;in.rdbuf()->pubsetbuf(ibuf.data(),ibuf.size());in.open(argv[1]);if(!in)throw runtime_error("no input");
 string prefix=argv[4];ofstream binary;binary.rdbuf()->pubsetbuf(obuf.data(),obuf.size());binary.open(prefix+".bin",ios::binary);
 vector<string> names;unordered_map<string,int> rawidx,idx;vector<double> values,mn,mx,tmin,tmax;vector<int> selectidx;
 string section,pending,sweep;double t=0,oldtime=-1;bool have=false,ended=false;unsigned long long points=0,lines=0;
 auto val=[&](int i)->double{return i<0?0:values[i];};
 auto index=[&](const string&n)->int{if(n=="0")return -1;auto it=idx.find(n);if(it==idx.end())throw runtime_error("missing required node "+n);return it->second;};
 auto snapshot=[&](){
  if(!(t>oldtime))throw runtime_error("time not increasing");
  for(size_t i=0;i<values.size();++i){double v=values[i];if(!isfinite(v))throw runtime_error("uninitialized trace "+names[i]);if(v<mn[i]){mn[i]=v;tmin[i]=t;}if(v>mx[i]){mx[i]=v;tmax[i]=t;}}
  for(auto&p:pairs){double v=abs(val(p.ai)-val(p.bi));if(v>=p.peak){p.peak=v;p.time=t;}}
  binary.write(reinterpret_cast<char*>(&t),8);for(int i:selectidx){double v=val(i);binary.write(reinterpret_cast<char*>(&v),8);}
  oldtime=t;++points;if(points%25000==0){rusage u;getrusage(RUSAGE_SELF,&u);cout<<"PROGRESS "<<points<<" "<<t*1e9<<" ns RSS_KiB "<<u.ru_maxrss<<endl;}
 };
 while(getline(in,line)){
  ++lines;if(!line.empty()&&line.back()=='\r')line.pop_back();
  if(line=="HEADER"||line=="TYPE"||line=="SWEEP"||line=="TRACE"||line=="VALUE"||line=="END"){
   section=line;
   if(section=="VALUE"){
    if(sweep!="time")throw runtime_error("not time sweep");
    values.assign(names.size(),numeric_limits<double>::quiet_NaN());mn.assign(names.size(),numeric_limits<double>::infinity());mx.assign(names.size(),-numeric_limits<double>::infinity());tmin.resize(names.size());tmax.resize(names.size());
    for(auto&n:selected)selectidx.push_back(index(n));for(auto&p:pairs){p.ai=index(p.a);p.bi=index(p.b);}
    ofstream cols(prefix+".columns");cols<<"time\n";for(auto&n:selected)cols<<n<<"\n";
   }
   if(section=="END"){if(have)snapshot();ended=true;break;}continue;
  }
  if(section!="TRACE"&&section!="SWEEP"&&section!="VALUE")continue;
  size_t q=line.find('"');if(q==string::npos)continue;size_t e=line.find('"',q+1);if(e==string::npos)throw runtime_error("unclosed quote");
  string key=line.substr(q+1,e-q-1);const char*tail=line.c_str()+e+1;while(*tail==' '||*tail=='\t')++tail;
  if(section=="SWEEP"){if(sweep.empty())sweep=key;continue;}
  if(section=="TRACE"){
   if(string(tail).find("GROUP")==0){if(string(tail)!="GROUP 1")throw runtime_error("unsupported group");pending=key;continue;}
   string n=norm(key);if(idx.count(n))throw runtime_error("duplicate trace "+n);int i=names.size();names.push_back(n);idx[n]=i;rawidx[key]=i;if(!pending.empty()){rawidx[pending]=i;pending.clear();}continue;
  }
  char*end;double v=strtod(tail,&end);if(end==tail||!isfinite(v))throw runtime_error("bad value");
  if(key==sweep){if(have)snapshot();t=v;have=true;}
  else{auto it=rawidx.find(key);if(it==rawidx.end())throw runtime_error("unknown value trace "+key);values[it->second]=v;}
 }
 binary.close();if(!binary)throw runtime_error("binary output failed");if(!ended||!points)throw runtime_error("incomplete PSF");
 ofstream stress(prefix+".stress.tsv");stress<<setprecision(17);for(size_t i=0;i<pairs.size();++i)stress<<i<<'\t'<<pairs[i].peak<<'\t'<<pairs[i].time<<'\n';
 ofstream extrema(prefix+".extrema.tsv");extrema<<setprecision(17);for(size_t i=0;i<names.size();++i)extrema<<names[i]<<'\t'<<mn[i]<<'\t'<<tmin[i]<<'\t'<<mx[i]<<'\t'<<tmax[i]<<'\n';
 rusage u;getrusage(RUSAGE_SELF,&u);ofstream meta(prefix+".meta.json");meta<<setprecision(17)<<"{\"points\":"<<points<<",\"last_time_s\":"<<t<<",\"traces\":"<<names.size()<<",\"columns\":"<<selected.size()+1<<",\"pairs\":"<<pairs.size()<<",\"peak_rss_kib\":"<<u.ru_maxrss<<",\"PSF_END\":true,\"lines\":"<<lines<<"}\n";
 cout<<"STREAM_OK "<<points<<" RSS_KiB "<<u.ru_maxrss<<endl;return 0;
 }catch(const exception&e){cerr<<e.what()<<endl;return 1;}}
