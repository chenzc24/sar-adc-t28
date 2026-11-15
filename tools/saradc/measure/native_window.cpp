// Bounded, read-only extraction of native PSFASCII windows; no decimation.
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
string norm(string s){string r;for(char c:s)if(c!='\\')r+=tolower(static_cast<unsigned char>(c));return r;}
int main(int argc,char**argv){try{
 if(argc!=4)throw runtime_error("raw layout csv required");
 ifstream cfg(argv[2]);int nn,nw;cfg>>nn>>nw;
 if(!cfg||nn<1||nn>64||nw<1||nw>64)throw runtime_error("Bad dimensions");
 vector<string> names(nn);unordered_map<string,int> nodes,aliases;
 for(int i=0;i<nn;i++){cfg>>names[i];if(!nodes.emplace(names[i],i).second)throw runtime_error("Duplicate node");}
 vector<pair<double,double>> windows(nw);for(auto&w:windows){cfg>>w.first>>w.second;if(w.first<0||w.second<=w.first)throw runtime_error("Bad window");}
 if(!cfg)throw runtime_error("Incomplete layout");
 ifstream raw(argv[1]);ofstream out(argv[3]);if(!raw||!out)throw runtime_error("File open failed");
 out<<setprecision(17)<<"time";for(auto&n:names)out<<','<<n;out<<'\n';
 vector<double> values(nn);vector<bool> have(nn,false);string section,line,pending,sweep;
 double t=-1,pt=-1;long count=0,saved=0;bool ended=false;
 auto flush=[&](){if(t<0)return;if((!count&&t!=0)||(count&&t<=pt))throw runtime_error("Invalid time axis");
   for(bool h:have)if(!h)throw runtime_error("Missing requested waveform");
   bool keep=false;for(auto&w:windows)keep|=t>=w.first&&t<=w.second;
   if(keep){if(++saved>100000)throw runtime_error("Window row budget exceeded");out<<t;for(double v:values)out<<','<<v;out<<'\n';}
   pt=t;count++;
 };
 while(getline(raw,line)){
   auto first=line.find_first_not_of(" \t\r");if(first==string::npos)continue;line=line.substr(first);
   while(!line.empty()&&(line.back()=='\r'||line.back()==' '))line.pop_back();
   if(line=="HEADER"||line=="TYPE"||line=="SWEEP"||line=="TRACE"||line=="VALUE"||line=="END"){
     section=line;if(line=="END"){flush();ended=true;break;}continue;
   }
   if(line[0]!='"')continue;auto q=line.find('"',1);if(q==string::npos)throw runtime_error("Bad key");
   string key=line.substr(1,q-1),tail=line.substr(q+1);
   if(section=="SWEEP"){if(sweep.empty())sweep=key;}
   else if(section=="TRACE"){
     if(tail.find("GROUP")!=string::npos)pending=key;
     else{auto it=nodes.find(norm(key));if(it!=nodes.end()){aliases[key]=it->second;if(!pending.empty())aliases[pending]=it->second;}pending.clear();}
   }else if(section=="VALUE"){
     if(key==sweep){char*end;double v=strtod(tail.c_str(),&end);if(end==tail.c_str()||!isfinite(v))throw runtime_error("Bad time");flush();t=v;}
     else{auto it=aliases.find(key);if(it!=aliases.end()){char*end;double v=strtod(tail.c_str(),&end);if(end==tail.c_str()||!isfinite(v))throw runtime_error("Bad value");values[it->second]=v;have[it->second]=true;}}
   }
 }
 if(!ended||sweep!="time"||!count||!saved||!out)throw runtime_error("Incomplete extraction");
 cout<<setprecision(17)<<"{\"native_points\":"<<count<<",\"saved_points\":"<<saved<<",\"stop\":"<<pt<<"}\n";
 return 0;
}catch(const exception&e){cerr<<e.what()<<endl;return 1;}}
