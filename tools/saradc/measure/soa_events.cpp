// Streaming PSFASCII terminal-pair evidence pass; reads a completed native waveform only.
// Reproduces the soa_scan.cpp interval screen and adds exact over-limit intervals with native
// sample support, native-time excerpts for requested events, and a 2x-decimated screen used as a
// time-step sensitivity review. C++11 (g++ 4.8).
#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
using namespace std;
typedef vector<pair<double,double> > Spans;
struct Pair {int a,b,covered;double peak=0,at=0,cpeak=0;Spans over,cover;};
struct Event {int pair;double t0,t1;vector<double> rows;};
string norm(string s){string r;for(char c:s)if(c!='\\')r+=tolower(static_cast<unsigned char>(c));return r;}
// Exact above-limit pieces of one piecewise-linear segment; adjacent pieces merge.
void segment(Spans&list,double old,double v,double pt,double t,double limit,long&budget){
  vector<double> cuts{pt,t};
  if(v!=old)for(double level:{-limit,limit}){double f=(level-old)/(v-old);if(f>0&&f<1)cuts.push_back(pt+f*(t-pt));}
  sort(cuts.begin(),cuts.end());
  for(size_t j=1;j<cuts.size();j++){
    double a=cuts[j-1],b=cuts[j];
    if(abs(old+(v-old)*((a+b)/2-pt)/(t-pt))<=limit)continue;
    if(!list.empty()&&list.back().second==a)list.back().second=b;
    else{list.push_back(make_pair(a,b));if(++budget>500000)throw runtime_error("Interval budget exceeded");}
  }
}
void spans(ofstream&out,const Spans&s,bool support,const vector<double>&times){
  out<<'[';
  for(size_t j=0;j<s.size();j++){
    if(j)out<<',';
    out<<'['<<s[j].first<<','<<s[j].second;
    if(support){
      size_t lo=lower_bound(times.begin(),times.end(),s[j].first)-times.begin();
      size_t hi=upper_bound(times.begin(),times.end(),s[j].second)-times.begin();
      size_t i=upper_bound(times.begin(),times.end(),s[j].first)-times.begin();
      double dt=i==0?times[1]-times[0]:(i>=times.size()?times.back()-times[times.size()-2]:times[i]-times[i-1]);
      out<<','<<(hi-lo)<<','<<dt;
    }
    out<<']';
  }
  out<<']';
}
int main(int argc,char**argv){try{
 if(argc!=5)throw runtime_error("raw layout events output required");
 ifstream layout(argv[2]);int nn,np;double limit;layout>>nn>>np>>limit;
 if(!layout||nn<=0||np<=0)throw runtime_error("Invalid layout");
 unordered_map<string,int> nodes,aliases;string name;
 for(int i=0;i<nn;i++){layout>>name;nodes[name]=i;}
 vector<Pair> pairs(np);for(auto &p:pairs)layout>>p.a>>p.b>>p.covered;
 if(!layout)throw runtime_error("Incomplete layout");
 ifstream plan(argv[3]);int ne=0;plan>>ne;vector<Event> events(ne);
 for(auto &e:events){plan>>e.pair>>e.t0>>e.t1;if(!plan||e.pair<0||e.pair>=np||e.t1<e.t0)throw runtime_error("Invalid event plan");}
 vector<double> values(nn,0),previous(np,0),coarse(np,0),times;vector<bool> have(nn,false);
 have[nodes.at("0")]=true;
 ifstream raw(argv[1]);if(!raw)throw runtime_error("No native file");
 string line,section,pending,sweep;double t=-1,pt=-1,ct=-1,maxdt=0;long count=0,fine=0,rough=0;bool ended=false;
 const double edges[]={0.5e-12,1e-12,1.5e-12,2e-12,3e-12,5e-12,10e-12,20e-12,50e-12};
 vector<long> hist(10,0);
 auto flush=[&](){
   if(t<0)return;
   if(count==0){if(t!=0)throw runtime_error("Missing startup");for(bool b:have)if(!b)throw runtime_error("Missing terminal waveform");}
   if(pt>=0){
     if(t<=pt)throw runtime_error("Nonmonotonic time");
     double dt=t-pt;maxdt=max(maxdt,dt);size_t k=0;while(k<9&&dt>edges[k])k++;hist[k]++;
   }
   bool even=count%2==0;
   for(int i=0;i<np;i++){
     Pair &p=pairs[i];double v=values[p.a]-values[p.b],old=previous[i];
     if(!isfinite(v))throw runtime_error("Nonfinite voltage");
     if(abs(v)>p.peak){p.peak=abs(v);p.at=t;}
     if(pt>=0&&p.covered&&(abs(v)>limit||abs(old)>limit))segment(p.over,old,v,pt,t,limit,fine);
     previous[i]=v;
     if(even){
       if(abs(v)>p.cpeak)p.cpeak=abs(v);
       if(ct>=0&&p.covered&&(abs(v)>limit||abs(coarse[i])>limit))segment(p.cover,coarse[i],v,ct,t,limit,rough);
       coarse[i]=v;
     }
   }
   if(even)ct=t;
   for(auto &e:events)if(t>=e.t0&&t<=e.t1){
     const Pair &p=pairs[e.pair];e.rows.push_back(t);e.rows.push_back(values[p.a]);e.rows.push_back(values[p.b]);
   }
   times.push_back(t);pt=t;count++;if(count%100000==0)cerr<<"points="<<count<<" time="<<setprecision(17)<<t<<endl;
 };
 while(getline(raw,line)){
   size_t first=line.find_first_not_of(" \t\r");if(first==string::npos)continue;line=line.substr(first);
   while(!line.empty()&&(line.back()=='\r'||line.back()==' '))line.pop_back();
   if(line=="HEADER"||line=="TYPE"||line=="SWEEP"||line=="TRACE"||line=="VALUE"||line=="END"){
     section=line;if(line=="END"){flush();ended=true;break;}continue;
   }
   if(line[0]!='"')continue;size_t quote=line.find('"',1);if(quote==string::npos)throw runtime_error("Bad native key");
   string key=line.substr(1,quote-1),tail=line.substr(quote+1);
   if(section=="SWEEP"){if(sweep.empty())sweep=key;}
   else if(section=="TRACE"){
     if(tail.find("GROUP")!=string::npos)pending=key;
     else{auto it=nodes.find(norm(key));if(it!=nodes.end()){aliases[key]=it->second;if(!pending.empty())aliases[pending]=it->second;}pending.clear();}
   }else if(section=="VALUE"){
     char*end;double value=strtod(tail.c_str(),&end);if(end==tail.c_str())throw runtime_error("Bad numeric value");
     if(key==sweep){flush();t=value;}
     else{auto it=aliases.find(key);if(it!=aliases.end()){values[it->second]=value;have[it->second]=true;}}
   }
 }
 if(!ended||sweep!="time"||count<2)throw runtime_error("Incomplete native file");
 ofstream out(argv[4]);out<<setprecision(17)<<"{\"count\":"<<count<<",\"stop\":"<<pt<<",\"max_dt\":"<<maxdt<<",\"dt_hist\":[";
 for(size_t i=0;i<hist.size();i++){if(i)out<<',';out<<hist[i];}
 out<<"],\"pairs\":[";
 for(int i=0;i<np;i++){
   if(i)out<<',';Pair&p=pairs[i];
   out<<"{\"peak_abs_V\":"<<p.peak<<",\"peak_time_s\":"<<p.at<<",\"coarse_peak_abs_V\":"<<p.cpeak<<",\"intervals\":";
   spans(out,p.over,true,times);out<<",\"coarse_intervals\":";spans(out,p.cover,false,times);out<<'}';
 }
 out<<"],\"events\":[";
 for(size_t i=0;i<events.size();i++){
   if(i)out<<',';out<<'[';
   for(size_t j=0;j<events[i].rows.size();j++){if(j)out<<',';out<<events[i].rows[j];}
   out<<']';
 }
 out<<"]}\n";if(!out)throw runtime_error("Write failed");
 return 0;
}catch(const exception&e){cerr<<e.what()<<endl;return 1;}}
