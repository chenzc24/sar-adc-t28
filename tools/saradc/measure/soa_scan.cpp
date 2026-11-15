// Streaming PSFASCII terminal-pair reductions; no simulator or circuit changes.
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
struct Pair {int a,b,covered;double peak=0,at=0;vector<pair<double,double> > over;};
string norm(string s){string r;for(char c:s)if(c!='\\')r+=tolower(static_cast<unsigned char>(c));return r;}
int main(int argc,char**argv){try{
 if(argc!=4)throw runtime_error("raw layout output required");
 ifstream layout(argv[2]);int nn,np;double limit;layout>>nn>>np>>limit;
 if(!layout||nn<=0||np<=0)throw runtime_error("Invalid layout");
 unordered_map<string,int> nodes,aliases;string name;
 for(int i=0;i<nn;i++){layout>>name;nodes[name]=i;}
 vector<Pair> pairs(np);for(auto &p:pairs)layout>>p.a>>p.b>>p.covered;
 if(!layout)throw runtime_error("Incomplete layout");
 vector<double> values(nn,0),previous(np,0);vector<bool> have(nn,false);
 have[nodes.at("0")]=true;
 ifstream raw(argv[1]);if(!raw)throw runtime_error("No native file");
 string line,section,pending,sweep;double t=-1,pt=-1,maxdt=0;long count=0,intervals=0;bool ended=false;
 auto flush=[&](){
   if(t<0)return;
   if(count==0){if(t!=0)throw runtime_error("Missing startup");for(bool b:have)if(!b)throw runtime_error("Missing terminal waveform");}
   if(pt>=0){if(t<=pt)throw runtime_error("Nonmonotonic time");maxdt=max(maxdt,t-pt);}
   for(int i=0;i<np;i++){
     Pair &p=pairs[i];double v=values[p.a]-values[p.b],old=previous[i];
     if(!isfinite(v))throw runtime_error("Nonfinite voltage");
     if(abs(v)>p.peak){p.peak=abs(v);p.at=t;}
     if(pt>=0&&p.covered&&(abs(v)>limit||abs(old)>limit)){
       vector<double> cuts{pt,t};
       if(v!=old)for(double level:{-limit,limit}){double f=(level-old)/(v-old);if(f>0&&f<1)cuts.push_back(pt+f*(t-pt));}
       sort(cuts.begin(),cuts.end());
       for(size_t j=1;j<cuts.size();j++){
         double a=cuts[j-1],b=cuts[j];
         if(abs(old+(v-old)*((a+b)/2-pt)/(t-pt))<=limit)continue;
         if(!p.over.empty()&&p.over.back().second==a)p.over.back().second=b;
         else{p.over.push_back(make_pair(a,b));if(++intervals>500000)throw runtime_error("Interval budget exceeded");}
       }
     }
     previous[i]=v;
   }
   pt=t;count++;if(count%100000==0)cerr<<"points="<<count<<" time="<<setprecision(17)<<t<<endl;
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
 if(!ended||sweep!="time"||!count)throw runtime_error("Incomplete native file");
 ofstream out(argv[3]);out<<setprecision(17)<<"{\"count\":"<<count<<",\"stop\":"<<pt<<",\"max_dt\":"<<maxdt<<",\"pairs\":[";
 for(int i=0;i<np;i++){if(i)out<<',';Pair&p=pairs[i];out<<"{\"peak_abs_V\":"<<p.peak<<",\"peak_time_s\":"<<p.at<<",\"intervals\":[";
   for(size_t j=0;j<p.over.size();j++){if(j)out<<',';out<<'['<<p.over[j].first<<','<<p.over[j].second<<']';}out<<"]}";
 }out<<"]}\n";if(!out)throw runtime_error("Write failed");
 return 0;
}catch(const exception&e){cerr<<e.what()<<endl;return 1;}}
