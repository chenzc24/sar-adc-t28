// One native PSFASCII point in memory. stdout contains binary boundary rows.
// New parser: historical source-run files and parsers are read-only.
#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdint>
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
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#else
#include <sys/resource.h>
#endif
using namespace std;
static string trim(string s) {
    size_t a=s.find_first_not_of(" \t\r\n"), b=s.find_last_not_of(" \t\r\n");
    return a==string::npos ? string() : s.substr(a,b-a+1);
}
static string norm(string s) {
    string out; for(unsigned char c:s) if(c!='\\') out+=char(tolower(c)); return out;
}
static vector<string> read_list(const string &path) {
    ifstream f(path); if(!f) throw runtime_error("missing signal list");
    vector<string> v; string s;
    while(getline(f,s)) if(!(s=trim(s)).empty()) v.push_back(norm(s));
    return v;
}
static void strings(ostream &out,const vector<string> &v) {
    out<<'['; for(size_t i=0;i<v.size();++i) {if(i) out<<','; out<<'"'<<v[i]<<'"';} out<<']';
}
int main(int argc,char **argv) {try {
    if(argc!=10) throw runtime_error("input boundary.list diagnostic.list prefix stop diag_start diag_end diag_max min_cover");
#ifdef _WIN32
    _setmode(_fileno(stdout),_O_BINARY);
#endif
    uint16_t endian=1;
    if(*reinterpret_cast<unsigned char*>(&endian)!=1) throw runtime_error("little-endian host required");
    vector<string> boundary=read_list(argv[2]);
    if(boundary.empty()) throw runtime_error("no boundary signals");
    vector<string> diag_names; vector<bool> diag_required;
    ifstream df(argv[3]); if(!df) throw runtime_error("missing diagnostic list");
    string line;
    while(getline(df,line)) {
        istringstream row(line); int required; string name;
        if(!(row>>required>>name) || (required!=0 && required!=1)) throw runtime_error("invalid diagnostic list");
        diag_names.push_back(norm(name)); diag_required.push_back(required==1);
    }
    string prefix=argv[4];
    double stop=stod(argv[5]), dstart=stod(argv[6]), dend=stod(argv[7]), mincover=stod(argv[9]);
    uint64_t diag_limit=stoull(argv[8]), diag_bytes=0;
    vector<char> inbuf(4*1024*1024);
    ifstream in; in.rdbuf()->pubsetbuf(inbuf.data(),inbuf.size()); in.open(argv[1]);
    if(!in) throw runtime_error("cannot open source raw");
    vector<string> names,present_diag,absent_diag;
    unordered_map<string,int> aliases,indices;
    vector<int> bi,di; vector<double> values,first_boundary;
    string section,sweep,pending;
    bool property=false,have=false,source_end=false,reached=false;
    double time=0,previous=-1,first=-1;
    uint64_t points=0,diag_points=0,lines=0;
    ofstream diagnostic;
    auto index=[&](const string &n)->int {
        auto found=indices.find(n);
        if(found==indices.end()) throw runtime_error("missing required signal "+n);
        return found->second;
    };
    auto emit=[&]() {
        if(!isfinite(time)||time<0||time<=previous) throw runtime_error("native time not strictly increasing");
        if(!points && time!=0) throw runtime_error("native initial point is not t=0");
        for(int i:bi) if(!isfinite(values[i])) throw runtime_error("uninitialized required boundary "+names[i]);
        for(int i:di) if(!isfinite(values[i])) throw runtime_error("uninitialized diagnostic "+names[i]);
        if(!points) {first=time; for(int i:bi) first_boundary.push_back(values[i]);}
        cout.write(reinterpret_cast<char*>(&time),8);
        for(int i:bi) cout.write(reinterpret_cast<char*>(&values[i]),8);
        if(!cout) throw runtime_error("boundary pipe write failed");
        if(time>=dstart && time<=dend) {
            uint64_t row_bytes=8*(di.size()+1);
            if(diag_bytes+row_bytes>diag_limit) throw runtime_error("diagnostic output budget exceeded");
            diagnostic.write(reinterpret_cast<char*>(&time),8);
            for(int i:di) diagnostic.write(reinterpret_cast<char*>(&values[i]),8);
            if(!diagnostic) throw runtime_error("diagnostic write failed");
            diag_bytes+=row_bytes; ++diag_points;
        }
        previous=time; ++points;
    };
    while(getline(in,line)) {
        ++lines; line=trim(line);
        if(line=="HEADER"||line=="TYPE"||line=="SWEEP"||line=="TRACE"||line=="VALUE"||line=="END") {
            section=line;
            if(section=="VALUE") {
                if(sweep!="time" || !pending.empty()) throw runtime_error("invalid time sweep or unfinished GROUP");
                values.assign(names.size(),numeric_limits<double>::quiet_NaN());
                for(const auto &n:boundary) bi.push_back(index(n));
                for(size_t i=0;i<diag_names.size();++i) {
                    auto found=indices.find(diag_names[i]);
                    if(found==indices.end()) {
                        if(diag_required[i]) throw runtime_error("missing required diagnostic "+diag_names[i]);
                        absent_diag.push_back(diag_names[i]);
                    } else {di.push_back(found->second); present_diag.push_back(diag_names[i]);}
                }
                ofstream bc(prefix+".boundary.columns"),dc(prefix+".diagnostic.columns");
                bc<<"time\n"; for(const auto &n:boundary) bc<<n<<'\n';
                dc<<"time\n"; for(const auto &n:present_diag) dc<<n<<'\n';
                if(!bc||!dc) throw runtime_error("column output failed");
                diagnostic.open(prefix+".diagnostic.f64le",ios::binary);
                if(!diagnostic) throw runtime_error("cannot create diagnostic output");
            }
            if(section=="END") {if(have) emit(); source_end=true; reached=previous>=stop; break;}
            continue;
        }
        if(section!="SWEEP"&&section!="TRACE"&&section!="VALUE") continue;
        if(section=="TRACE"&&property) {if(line==")") property=false; continue;}
        size_t q=line.find('"'); if(q==string::npos) continue;
        size_t e=line.find('"',q+1); if(e==string::npos) throw runtime_error("unclosed quote");
        string key=line.substr(q+1,e-q-1),tail=trim(line.substr(e+1));
        if(section=="SWEEP") {if(sweep.empty()) sweep=key; continue;}
        if(section=="TRACE") {
            property=tail.find("PROP(")!=string::npos;
            if(tail.find("GROUP")==0) {
                if(tail!="GROUP 1"||!pending.empty()) throw runtime_error("unsupported GROUP");
                pending=key; continue;
            }
            string n=norm(key);
            if(indices.count(n)||aliases.count(key)) throw runtime_error("duplicate trace "+n);
            int i=names.size(); names.push_back(n); indices[n]=i; aliases[key]=i;
            if(!pending.empty()) {if(aliases.count(pending)) throw runtime_error("duplicate GROUP alias"); aliases[pending]=i; pending.clear();}
            continue;
        }
        char *end; double value=strtod(tail.c_str(),&end);
        if(end==tail.c_str()||!isfinite(value)||!trim(string(end)).empty()) throw runtime_error("bad native value");
        if(key==sweep) {
            if(have) emit();
            if(value>stop) {reached=true; break;}
            time=value; have=true;
        } else {
            auto found=aliases.find(key); if(found==aliases.end()||!have) throw runtime_error("unknown value trace or missing time");
            values[found->second]=value;
        }
    }
    cout.flush(); diagnostic.close();
    if(!cout||!diagnostic) throw runtime_error("output close failed");
    if(!reached||!points||previous<mincover||!diag_points) throw runtime_error("incomplete extraction history or diagnostic window");
    ofstream meta(prefix+".meta.json"); meta<<setprecision(17);
    meta<<"{\"native_points_exported\":"<<points<<",\"first_time_s\":"<<first
        <<",\"last_native_time_s\":"<<previous<<",\"requested_end_s\":"<<stop
        <<",\"lookahead_or_source_end_covers_end\":true,\"source_PSF_END_seen\":"<<(source_end?"true":"false")
        <<",\"boundary_columns\":"<<bi.size()+1<<",\"diagnostic_columns\":"<<di.size()+1
        <<",\"diagnostic_native_points\":"<<diag_points<<",\"diagnostic_bytes\":"<<diag_bytes
        <<",\"source_traces\":"<<names.size()<<",\"source_lines_read\":"<<lines
        <<",\"interpolated\":false,\"decimated\":false,\"optional_diagnostics_absent\":";
    strings(meta,absent_diag); meta<<",\"first_boundary_values\":[";
    for(size_t i=0;i<first_boundary.size();++i) {if(i)meta<<',';meta<<first_boundary[i];}
    meta<<"],\"parser_peak_rss_kib\":";
#ifdef _WIN32
    meta<<"null";
#else
    rusage usage; getrusage(RUSAGE_SELF,&usage); meta<<usage.ru_maxrss;
#endif
    meta<<"}\n"; if(!meta) throw runtime_error("metadata write failed");
    return 0;
} catch(const exception &error) {cerr<<error.what()<<'\n'; return 1;} }
