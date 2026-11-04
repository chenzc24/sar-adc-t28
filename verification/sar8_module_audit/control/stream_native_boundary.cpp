// Adapted from the project's one-snapshot stream_psf.cpp; no PDK dependency.
// Selected native samples only, no decimation/interpolation/full-wave arrays.
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
#include <windows.h>
#include <psapi.h>
#else
#include <sys/resource.h>
#endif
using namespace std;

string trim(string x) {
    size_t a=x.find_first_not_of(" \t\r"), b=x.find_last_not_of(" \t\r");
    return a==string::npos ? string() : x.substr(a,b-a+1);
}
string norm(const string& x) {
    string r; for (unsigned char c:x) if(c!='\\') r+=char(tolower(c)); return r;
}
string quoted(const string& x) {
    string r="\""; for(char c:x) { if(c=='\\'||c=='\"')r+='\\'; r+=c; } return r+'\"';
}
unsigned long long rss_kib() {
#ifdef _WIN32
    PROCESS_MEMORY_COUNTERS p;
    if(!GetProcessMemoryInfo(GetCurrentProcess(),&p,sizeof(p))) throw runtime_error("RSS unavailable");
    return p.PeakWorkingSetSize/1024;
#else
    rusage u; if(getrusage(RUSAGE_SELF,&u)) throw runtime_error("RSS unavailable"); return u.ru_maxrss;
#endif
}
bool exists(const string& path) { ifstream f(path.c_str(),ios::binary); return bool(f); }
double number(const string& s) {
    char *p=0; double v=strtod(s.c_str(),&p);
    if(p==s.c_str()||!trim(string(p)).empty()||!isfinite(v))throw runtime_error("invalid scalar: "+s);
    return v;
}

int main(int argc,char** argv) { try {
    if(argc!=9) throw runtime_error("input.psf selected.txt output-dir stop_s diagnostic_start_s diagnostic_stop_s max_data_bytes max_rss_kib");
    uint16_t endian=1; if(*reinterpret_cast<unsigned char*>(&endian)!=1||sizeof(double)!=8)
        throw runtime_error("little-endian float64 host required");
    const double stop=number(argv[4]), begin_diag=number(argv[5]), end_diag=number(argv[6]);
    const unsigned long long max_bytes=strtoull(argv[7],0,10), max_rss=strtoull(argv[8],0,10);
    if(!(0<=begin_diag && begin_diag<end_diag && end_diag<=stop) || !max_bytes || !max_rss)
        throw runtime_error("invalid interval/resource bound");
    vector<string> selected; string line;
    ifstream selection(argv[2]); if(!selection)throw runtime_error("missing selected list");
    while(getline(selection,line)) {
        line=trim(line); if(line.empty())continue;
        if(norm(line)!=line || find(selected.begin(),selected.end(),line)!=selected.end())
            throw runtime_error("selected names must be unique canonical native names");
        selected.push_back(line);
    }
    if(selected.empty())throw runtime_error("empty selection");
    const string out=argv[3];
    for(const string& f:vector<string>{"boundary.native.bin","peak.native.bin","initial_state.json","peak_summary.json","native_export.meta.json"})
        if(exists(out+"/"+f))throw runtime_error("preserve existing output: "+f);
    vector<char> input_buffer(4*1024*1024);
    ifstream in; in.rdbuf()->pubsetbuf(input_buffer.data(),input_buffer.size()); in.open(argv[1],ios::binary);
    if(!in)throw runtime_error("missing ASCII PSF input");
    ofstream history((out+"/boundary.native.bin").c_str(),ios::binary);
    ofstream diagnostic((out+"/peak.native.bin").c_str(),ios::binary);
    if(!history||!diagnostic)throw runtime_error("cannot create new output files");
    vector<string> names, raw_names; unordered_map<string,int> raw_index, canonical;
    vector<double> values, minimum, maximum, min_time, max_time, initial;
    vector<unsigned char> seen, ever_initialized; vector<int> indices;
    string section, sweep, group; bool property=false, have=false, ended=false, covered=false;
    double t=0, previous=-1, first=-1, beyond=-1, largest_gap=0;
    unsigned long long points=0, diag_points=0, lines=0, consumed=0, data_bytes=0, held_values=0;
    auto flush=[&]() {
        if(!(t>previous) || (points==0 && t!=0))throw runtime_error("native time must start at zero and strictly increase");
        for(int i:indices) {
            if(!ever_initialized[i] || !isfinite(values[i]))throw runtime_error("uninitialized selected native value: "+names[i]);
            // Native ASCII sparse updates mean unchanged values, not missing
            // measurements. Preserve the last explicitly initialized value.
            if(!seen[i])++held_values;
        }
        if(points==0) { first=t; for(int i:indices)initial.push_back(values[i]); }
        if(previous>=0)largest_gap=max(largest_gap,t-previous);
        const bool is_diag=t>=begin_diag && t<=end_diag;
        const unsigned long long row_bytes=(indices.size()+1)*8;
        if(data_bytes+row_bytes*(is_diag?2:1)>max_bytes)throw runtime_error("native binary output budget exceeded");
        history.write(reinterpret_cast<const char*>(&t),8);
        if(is_diag)diagnostic.write(reinterpret_cast<const char*>(&t),8);
        for(size_t j=0;j<indices.size();++j) {
            double v=values[indices[j]]; history.write(reinterpret_cast<const char*>(&v),8);
            if(is_diag) {
                diagnostic.write(reinterpret_cast<const char*>(&v),8);
                if(v<minimum[j]){minimum[j]=v;min_time[j]=t;}
                if(v>maximum[j]){maximum[j]=v;max_time[j]=t;}
            }
        }
        data_bytes+=row_bytes*(is_diag?2:1); ++points; if(is_diag)++diag_points;
        previous=t;
        if(points%1000==0 && rss_kib()>max_rss)throw runtime_error("RSS budget exceeded");
        if(points%25000==0)cout<<"NATIVE_PREFIX "<<points<<" time_ns "<<setprecision(12)<<t*1e9<<endl;
    };
    while(getline(in,line)) {
        ++lines; consumed+=line.size()+(in.eof()?0:1);
        if(line.size()>1024*1024)throw runtime_error("oversize ASCII PSF line");
        line=trim(line);
        if(line=="HEADER"||line=="TYPE"||line=="SWEEP"||line=="TRACE"||line=="VALUE"||line=="END") {
            section=line;
            if(section=="VALUE") {
                if(sweep!="time")throw runtime_error("expected a time sweep in seconds");
                values.assign(names.size(),numeric_limits<double>::quiet_NaN()); seen.assign(names.size(),0);
                ever_initialized.assign(names.size(),0);
                for(const string& n:selected) {
                    auto it=canonical.find(n); if(it==canonical.end())throw runtime_error("missing required TRACE: "+n);
                    indices.push_back(it->second);
                }
                minimum.assign(indices.size(),numeric_limits<double>::infinity());
                maximum.assign(indices.size(),-numeric_limits<double>::infinity());
                min_time.resize(indices.size()); max_time.resize(indices.size());
            }
            if(section=="END") { if(have)flush(); ended=true; covered=previous>=stop; break; }
            continue;
        }
        if(section!="TRACE"&&section!="SWEEP"&&section!="VALUE")continue;
        if(section=="TRACE" && property){if(line==")")property=false;continue;}
        size_t q=line.find('"'); if(q==string::npos)continue;
        size_t e=line.find('"',q+1); if(e==string::npos)throw runtime_error("unclosed PSF quote");
        string key=line.substr(q+1,e-q-1), tail=trim(line.substr(e+1));
        if(section=="SWEEP"){if(sweep.empty())sweep=key;continue;}
        if(section=="TRACE") {
            size_t prop=tail.find("PROP(");
            property=prop!=string::npos && tail.find(')',prop)==string::npos;
            if(tail.find("GROUP")==0){if(tail!="GROUP 1")throw runtime_error("unsupported TRACE group");group=key;continue;}
            if(names.size()>=100000)throw runtime_error("too many traces");
            string n=norm(key); if(canonical.count(n))throw runtime_error("duplicate canonical TRACE: "+n);
            int i=names.size();names.push_back(n);raw_names.push_back(key);canonical[n]=i;raw_index[key]=i;
            if(!group.empty()) {
                string alias=norm(group);
                if(canonical.count(alias)&&canonical[alias]!=i)throw runtime_error("ambiguous group alias");
                canonical[alias]=i;raw_index[group]=i;group.clear();
            }
            continue;
        }
        double v=number(tail);
        if(key==sweep) {
            if(have)flush();
            if(v<=previous)throw runtime_error("non-increasing native time marker");
            if(v>stop){beyond=v;covered=true;have=false;break;}
            t=v;have=true;fill(seen.begin(),seen.end(),0);
        } else {
            if(!have)throw runtime_error("value before first time");
            auto it=raw_index.find(key);if(it==raw_index.end())throw runtime_error("unknown value TRACE: "+key);
            if(seen[it->second])throw runtime_error("duplicate value at native point: "+key);
            values[it->second]=v;seen[it->second]=1;ever_initialized[it->second]=1;
        }
    }
    history.close();diagnostic.close();
    if(!history||!diagnostic)throw runtime_error("binary output write failed");
    if(!covered||!points||!diag_points)throw runtime_error("requested native prefix/window incomplete");
    const unsigned long long peak_rss=rss_kib(); if(peak_rss>max_rss)throw runtime_error("RSS budget exceeded");
    ofstream initial_file((out+"/initial_state.json").c_str()); initial_file<<setprecision(17)<<"{\"time_s\":"<<first<<",\"values_v\":{";
    ofstream peaks((out+"/peak_summary.json").c_str()); peaks<<setprecision(17)<<"{\"window_start_s\":"<<begin_diag<<",\"window_stop_s\":"<<end_diag<<",\"signals\":{";
    for(size_t j=0;j<selected.size();++j) {
        if(j){initial_file<<',';peaks<<',';}
        initial_file<<quoted(selected[j])<<':'<<initial[j];
        peaks<<quoted(selected[j])<<":{\"min_v\":"<<minimum[j]<<",\"min_time_s\":"<<min_time[j]<<",\"max_v\":"<<maximum[j]<<",\"max_time_s\":"<<max_time[j]<<'}';
    }
    initial_file<<"}}\n";peaks<<"}}\n";
    ofstream meta((out+"/native_export.meta.json").c_str());meta<<setprecision(17)
        <<"{\"points\":"<<points<<",\"diagnostic_points\":"<<diag_points<<",\"columns\":"<<indices.size()+1
        <<",\"first_time_s\":"<<first<<",\"last_exported_time_s\":"<<previous<<",\"first_time_marker_beyond_s\":";
    if(beyond<0)meta<<"null";else meta<<beyond;
    meta<<",\"largest_native_gap_s\":"<<largest_gap<<",\"source_END_observed\":"<<(ended?"true":"false")
        <<",\"requested_prefix_covered\":true,\"consumed_source_prefix_bytes\":"<<consumed
        <<",\"source_lines_read\":"<<lines<<",\"trace_count\":"<<names.size()<<",\"binary_output_bytes\":"<<data_bytes
        <<",\"parser_peak_rss_kib\":"<<peak_rss<<",\"interpolated_points\":0,\"decimated_points\":0"
        <<",\"held_selected_values_from_native_sparse_updates\":"<<held_values<<",\"trace_bindings\":{";
    for(size_t j=0;j<selected.size();++j){if(j)meta<<',';meta<<quoted(selected[j])<<':'<<quoted(raw_names[indices[j]]);}
    meta<<"}}\n";
    initial_file.close();peaks.close();meta.close();
    if(!initial_file||!peaks||!meta)throw runtime_error("metadata output failed");
    cout<<"NATIVE_PREFIX_OK "<<points<<" RSS_KiB "<<peak_rss<<endl;return 0;
} catch(const exception& e) {cerr<<e.what()<<endl;return 1;} }
