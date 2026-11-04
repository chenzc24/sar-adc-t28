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
 string section,pending,sweep;double t=0,oldtime=-1;double exported=-1;unsigned long long exported_points=0;bool have=false,ended=false,property=false;unsigned long long points=0,lines=0;
 auto val=[&](int i)->double{return i<0?0:values[i];};
 auto index=[&](const string&n)->int{if(n=="0")return -1;auto it=idx.find(n);if(it==idx.end())throw runtime_error("missing required node "+n);return it->second;};

 struct Product {string name,a,b;int ai,bi;double prev=0;double integral[2]={0,0};};
 vector<Product> products;string config=argv[2];config=config.substr(0,config.find_last_of("/\\")+1);
 ifstream powerfile(config+"products.txt");while(getline(powerfile,line)){istringstream s(line);Product p;s>>p.name>>p.a>>p.b;if(!p.name.empty())products.push_back(p);}
 vector<string> eventnames;vector<int> eventidx;vector<double> eventprev;
 ifstream eventfile(config+"events.txt");while(getline(eventfile,line)){if(!line.empty()&&line.back()=='\r')line.pop_back();if(!line.empty())eventnames.push_back(line);}
 ofstream eventout(prefix+".events.tsv");eventout<<setprecision(17);int supplyidx=-1;


 vector<string> snames;vector<int>sidx;vector<double>sprev;string sline;
 ifstream sfile(config+"snapshot_nodes.txt");while(getline(sfile,sline))if(!sline.empty())snames.push_back(sline);
 struct Check{string label;double at;};vector<Check>checks;size_t ci=0;
 ifstream cfile(config+"check_times.txt");while(getline(cfile,sline)){istringstream z(sline);Check c;z>>c.label>>c.at;if(!c.label.empty())checks.push_back(c);}
 ofstream sout(prefix+".samples.tsv");sout<<setprecision(17)<<"kind\tlabel\ttime_s";for(auto&n:snames)sout<<'\t'<<n;sout<<'\n';
 ofstream lout(prefix+".reset90.tsv");lout<<setprecision(17);
 vector<string>lnames={"xdut.comp_p","xdut.comp_n","xdut.xcomp.x","xdut.xcomp.y"};vector<int>lidx;vector<double>lprev;
 vector<int>triggeridx;vector<double>triggerprev;

 auto snapshot=[&](){
  if(!(t>oldtime))throw runtime_error("time not increasing");
  for(size_t i=0;i<values.size();++i){double v=values[i];if(!isfinite(v))throw runtime_error("uninitialized trace "+names[i]);if(v<mn[i]){mn[i]=v;tmin[i]=t;}if(v>mx[i]){mx[i]=v;tmax[i]=t;}}
  for(auto&p:pairs){double v=abs(val(p.ai)-val(p.bi));if(v>=p.peak){p.peak=v;p.time=t;}}
  if(t-exported>=20e-12 || section=="END") {binary.write(reinterpret_cast<char*>(&t),8);for(int i:selectidx){double v=val(i);binary.write(reinterpret_cast<char*>(&v),8);}exported=t;++exported_points;}

  for(auto &p:products){double current=val(p.ai)*val(p.bi);
   if(oldtime>=0){for(int f=0;f<1;++f){double a=max(oldtime,f*260e-9),b=min(t,(f+1)*260e-9);
    if(b>a){double ya=p.prev+(current-p.prev)*(a-oldtime)/(t-oldtime),yb=p.prev+(current-p.prev)*(b-oldtime)/(t-oldtime);p.integral[f]+=.5*(ya+yb)*(b-a);}}}
   p.prev=current;
  }
  for(size_t i=0;i<eventidx.size();++i){double current=val(eventidx[i])-.5*val(supplyidx);
   if(oldtime>=0 && ((eventprev[i]<0 && current>=0)||(eventprev[i]>0 && current<=0)))
    eventout<<eventnames[i]<<'\t'<<(current>eventprev[i]?1:0)<<'\t'<<(oldtime-eventprev[i]*(t-oldtime)/(current-eventprev[i]))<<'\n';
   eventprev[i]=current;
  }

  auto sample=[&](const string&kind,const string&label,double at){
   double f=(t==oldtime?1:(at-oldtime)/(t-oldtime));sout<<kind<<'\t'<<label<<'\t'<<at;
   for(size_t j=0;j<sidx.size();++j)sout<<'\t'<<(sprev[j]+f*(val(sidx[j])-sprev[j]));sout<<'\n';
  };
  for(size_t j=0;j<triggeridx.size();++j){double now=val(triggeridx[j])-.5*val(supplyidx),before=triggerprev[j];
   if(oldtime>=0 && ((before<0&&now>=0)||(before>0&&now<=0))){double at=oldtime-before*(t-oldtime)/(now-before);
    sample(j==0?(now>before?"clock_rise":"clock_fall"):(now>before?"write_rise":"write_fall"),j==0?"cmp_clk":"phi_w",at);}
   triggerprev[j]=now;
  }
  if(oldtime>=0)while(ci<checks.size()&&checks[ci].at<=t){
   if(checks[ci].at<oldtime)throw runtime_error("missed fixed checkpoint");
   sample("fixed",checks[ci].label,checks[ci].at);++ci;
  }
  for(size_t j=0;j<lidx.size();++j){double now=val(lidx[j])-.9*val(supplyidx),before=lprev[j];
   if(oldtime>=0&&((before<0&&now>=0)||(before>0&&now<=0)))lout<<lnames[j]<<'\t'<<(now>before?1:0)<<'\t'<<(oldtime-before*(t-oldtime)/(now-before))<<'\n';
   lprev[j]=now;
  }
  for(size_t j=0;j<sidx.size();++j)sprev[j]=val(sidx[j]);

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

    for(auto &p:products){p.ai=index(p.a);p.bi=index(p.b);}
    supplyidx=index("vdd!");for(auto &n:eventnames)eventidx.push_back(index(n));eventprev.resize(eventidx.size());

    for(auto&n:snames)sidx.push_back(index(n));sprev.resize(sidx.size());
    for(auto&n:lnames)lidx.push_back(index(n));lprev.resize(lidx.size());
    triggeridx={index("cmp_clk"),index("xdut.xctrl.phi_w")};triggerprev.resize(2);

    ofstream cols(prefix+".columns");cols<<"time\n";for(auto&n:selected)cols<<n<<"\n";
   }
   if(section=="END"){if(have)snapshot();ended=true;break;}continue;
  }
  if(section!="TRACE"&&section!="SWEEP"&&section!="VALUE")continue;
  // Native terminal-current declarations may carry a multiline PROP(units).
  if(section=="TRACE" && property){if(line==")")property=false;continue;}
  size_t q=line.find('"');if(q==string::npos)continue;size_t e=line.find('"',q+1);if(e==string::npos)throw runtime_error("unclosed quote");
  string key=line.substr(q+1,e-q-1);const char*tail=line.c_str()+e+1;while(*tail==' '||*tail=='\t')++tail;
  if(section=="SWEEP"){if(sweep.empty())sweep=key;continue;}
  if(section=="TRACE"){
   property=string(tail).find("PROP(")!=string::npos;
   if(string(tail).find("GROUP")==0){if(string(tail)!="GROUP 1")throw runtime_error("unsupported group");pending=key;continue;}
   string n=norm(key);if(idx.count(n))throw runtime_error("duplicate trace "+n);int i=names.size();names.push_back(n);idx[n]=i;rawidx[key]=i;if(!pending.empty()){rawidx[pending]=i;pending.clear();}continue;
  }
  char*end;double v=strtod(tail,&end);if(end==tail||!isfinite(v))throw runtime_error("bad value");
  if(key==sweep){if(have)snapshot();t=v;have=true;}
  else{auto it=rawidx.find(key);if(it==rawidx.end())throw runtime_error("unknown value trace "+key);values[it->second]=v;}
 }
 binary.close();if(!binary)throw runtime_error("binary output failed");if(!ended||!points)throw runtime_error("incomplete PSF");
 ofstream energy(prefix+".products.tsv");energy<<setprecision(17);
 for(auto&p:products)for(int f=0;f<1;++f)energy<<p.name<<'\t'<<f<<'\t'<<p.integral[f]<<'\n';
 ofstream stress(prefix+".stress.tsv");stress<<setprecision(17);for(size_t i=0;i<pairs.size();++i)stress<<i<<'\t'<<pairs[i].peak<<'\t'<<pairs[i].time<<'\n';
 ofstream extrema(prefix+".extrema.tsv");extrema<<setprecision(17);for(size_t i=0;i<names.size();++i)extrema<<names[i]<<'\t'<<mn[i]<<'\t'<<tmin[i]<<'\t'<<mx[i]<<'\t'<<tmax[i]<<'\n';
 rusage u;getrusage(RUSAGE_SELF,&u);ofstream meta(prefix+".meta.json");meta<<setprecision(17)<<"{\"points\":"<<exported_points<<",\"native_points\":"<<points<<",\"last_time_s\":"<<t<<",\"traces\":"<<names.size()<<",\"columns\":"<<selected.size()+1<<",\"pairs\":"<<pairs.size()<<",\"peak_rss_kib\":"<<u.ru_maxrss<<",\"PSF_END\":true,\"lines\":"<<lines<<"}\n";
 cout<<"STREAM_OK "<<points<<" RSS_KiB "<<u.ru_maxrss<<endl;return 0;
 }catch(const exception&e){cerr<<e.what()<<endl;return 1;}}
