// Thin one-worker API adapter. Upstream LEO sources are not modified.
#include <leo/leo.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <unordered_set>
using namespace leo;
using Clock = std::chrono::steady_clock;
void require(bool ok, const std::string& s) { if (!ok) throw std::runtime_error(s); }
double elapsed(Clock::time_point s) {return std::chrono::duration<double>(Clock::now()-s).count();}
struct StdoutFile {std::ofstream file;std::streambuf* old=nullptr;void open(const std::string&path){file.open(path);require(bool(file),"Cannot open output");old=std::cout.rdbuf(file.rdbuf());}~StdoutFile(){if(old){std::cout.flush();std::cout.rdbuf(old);}}};
void raw(std::ostream& o,const Solution&s) {
 o<<"{\"dimension\":"<<s.dimension<<",\"additions\":"<<s.getAdditions()<<",\"substitutions\":[";
 for(size_t i=0;i<s.substitutions.size();i++){if(i)o<<',';auto g=s.substitutions[i];o<<"{\"i\":"<<g.i<<",\"j\":"<<g.j<<",\"ai\":"<<g.ai<<",\"aj\":"<<g.aj<<'}';}
 o<<"],\"expressions\":[";
 for(size_t i=0;i<s.expressions.size();i++){if(i)o<<',';o<<'[';for(size_t j=0;j<s.expressions[i].size();j++){if(j)o<<',';auto t=s.expressions[i][j];o<<"{\"index\":"<<t.index<<",\"value\":"<<t.value<<'}';}o<<']';}o<<"]}";
}
std::vector<Substitution> retention(const Solution&s,std::mt19937&r,double p){
 std::uniform_real_distribution<double>u(0,1);std::vector<bool>keep(s.substitutions.size());std::vector<size_t>idx(s.substitutions.size());std::vector<Substitution>out;
 for(size_t j=0;j<s.substitutions.size();j++){auto g=s.substitutions[j];if(u(r)>p||(g.i>=s.dimension&&!keep[g.i-s.dimension])||(g.j>=s.dimension&&!keep[g.j-s.dimension]))continue;keep[j]=true;idx[j]=out.size();if(g.i>=s.dimension)g.i=s.dimension+idx[g.i-s.dimension];if(g.j>=s.dimension)g.j=s.dimension+idx[g.j-s.dimension];out.push_back(g);}return out;
}
int main(int argc,char**argv){try{
 auto programStart=Clock::now();std::map<std::string,std::string>a;bool inspect=false,jsonl=false;
 for(int i=1;i<argc;i++){std::string k=argv[i];if(k=="--inspect"){inspect=true;continue;}if(k=="--jsonl"){jsonl=true;continue;}require(i+1<argc,"Missing argument value");a[k]=argv[++i];}
 StdoutFile outputFile;if(a.count("--output"))outputFile.open(a.at("--output"));
 auto get=[&](std::string k,std::string d){return a.count(k)?a.at(k):d;};require(a.count("--input"),"--input required");
 std::ifstream in(a.at("--input"));size_t n,m,ng;in>>n>>m>>ng;require(bool(in)&&n>0&&m>0,"Invalid input header");
 std::vector<std::vector<int>>targets(m,std::vector<int>(n));int targetMax=0;for(auto&v:targets)for(auto&x:v){in>>x;require(bool(in)&&std::abs(int64_t(x))<=1000000,"Invalid target coefficient");targetMax=std::max(targetMax,std::abs(x));}
 Solution donor;donor.dimension=n;std::vector<std::vector<int64_t>>vals(n,std::vector<int64_t>(n));for(size_t i=0;i<n;i++)vals[i][i]=1;
 for(size_t j=0;j<ng;j++){Substitution g;in>>g.i>>g.ai>>g.j>>g.aj;require(bool(in)&&g.i<n+j&&g.j<n+j&&(g.ai==1||g.ai==-1)&&(g.aj==1||g.aj==-1),"Invalid donor gate");std::vector<int64_t>v(n);bool nz=false;for(size_t k=0;k<n;k++){v[k]=g.ai*vals[g.i][k]+g.aj*vals[g.j][k];require(std::abs(v[k])<=1000000,"Unsafe intermediate coefficient");nz|=v[k]!=0;}require(nz,"Zero donor intermediate unsupported");vals.push_back(v);donor.substitutions.push_back(g);}
 for(size_t i=0;i<m;i++){size_t count;in>>count;std::vector<Term>row;for(size_t j=0;j<count;j++){Term t;in>>t.index>>t.value;require(bool(in)&&t.index<n+ng&&(t.value==1||t.value==-1),"Invalid donor output");row.push_back(t);}donor.expressions.push_back(row);}std::string extra;require(!(in>>extra),"Trailing input");
 ExpressionsSystem system(targets);require(system.validateSolution(donor),"Donor does not compute target");
 auto prep=Clock::now();Reducer reducer(1);auto intermediates=reducer.getIntermediates(targets,donor);HelperPool pool(n);pool.addSolution(donor,1.0);double preparation=elapsed(prep);
 std::unordered_set<Vector>done;for(auto&row:targets){Vector v(row);if(v.getSupport()>=2)done.insert(v.getCanonized());}
 std::vector<size_t>wires;for(size_t j=0;j<ng;j++){std::vector<int>v(vals[n+j].begin(),vals[n+j].end());Vector x(v);auto c=x.getCanonized();if(x.getSupport()<2||done.count(c))continue;done.insert(c);wires.push_back(n+j);}
 require(wires.size()==intermediates.size(),"Inspection helper mapping differs from upstream");
 std::cout<<std::setprecision(17);if(inspect){std::cout<<"{\"status\":\"inspect\",\"helpers\":[";for(size_t i=0;i<intermediates.size();i++){if(i)std::cout<<',';std::cout<<"{\"helper_index\":"<<i<<",\"wire\":"<<wires[i]<<",\"coefficients\":[";for(size_t j=0;j<n;j++){if(j)std::cout<<',';std::cout<<intermediates[i][j];}std::cout<<"]}";}std::cout<<"]}\n";return 0;}
 std::string mode=get("--mode","vectors");require(mode=="vectors"||mode=="explicit"||mode=="helpers"||mode=="retention"||mode=="mixed"||mode=="scratch","Invalid mode");
 uint64_t seed=std::stoull(get("--seed","1")),calls=std::stoull(get("--draws",get("--calls","1")));require(calls>0&&calls<=100000&&seed<=UINT32_MAX&&calls-1<=UINT32_MAX-seed,"Invalid seed/call range");
 double seconds=std::stod(get("--seconds-per-draw",get("--seconds","2"))),wall=std::stod(get("--budget-seconds",get("--wall-seconds","0"))),retain=std::stod(get("--retention","0.5")),savings=std::stod(get("--savings","0"));require(std::isfinite(seconds)&&seconds>0&&std::isfinite(wall)&&wall>=0&&std::isfinite(retain)&&retain>=0&&retain<=1&&std::isfinite(savings),"Invalid time/retention/savings");
 int slack=std::stoi(get("--slack","2"));size_t minRemove=std::stoull(get("--min-remove","1")),maxRemove=std::stoull(get("--max-remove","8"));require(minRemove<=maxRemove,"Invalid removal limits");
 std::set<size_t>explicitRemoved;if(a.count("--removed")){std::stringstream ss(a.at("--removed"));std::string x;while(std::getline(ss,x,','))if(!x.empty()){size_t z=std::stoull(x);require(z<intermediates.size()&&explicitRemoved.insert(z).second,"Invalid/duplicate removal index");}}
 std::vector<std::set<size_t>>removedRows;if(a.count("--removed-file")){std::ifstream choices(a.at("--removed-file"));require(bool(choices),"Cannot open removals file");std::string line;while(std::getline(choices,line)){std::set<size_t>row;std::stringstream ss(line);std::string x;while(std::getline(ss,x,','))if(!x.empty()){size_t z=std::stoull(x);require(z<intermediates.size()&&row.insert(z).second,"Invalid removal file row");}removedRows.push_back(std::move(row));}require(!removedRows.empty(),"Empty removal file");}
 vector_covering::Parameters params;params.maxAbsValue=std::stoi(get("--max-abs",std::to_string(targetMax)));require(params.maxAbsValue>=0,"Invalid coefficient limit");params.naiveFallback=false;params.removeUnused=true;int ignoreUnused=std::stoi(get("--ignore-unused-bound","1"));require(ignoreUnused==0||ignoreUnused==1,"Invalid bound mode");params.ignoreUnusedInBound=bool(ignoreUnused);params.addTargetPairs=false;params.maxTimeInSeconds=seconds;
 std::cout<<"{\"event\":\"metadata\",\"mode\":\""<<mode<<"\",\"workers\":1,\"helpers\":"<<intermediates.size()<<",\"donor_additions\":"<<donor.getAdditions()<<",\"ignore_unused_bound\":"<<(params.ignoreUnusedInBound?"true":"false")<<",\"savings_weight\":"<<savings<<",\"support_slack\":"<<slack<<",\"max_abs_coefficient\":"<<params.maxAbsValue<<",\"seed\":"<<seed<<",\"attempt_cap\":"<<calls<<",\"budget_seconds\":"<<wall<<",\"per_draw_seconds\":"<<seconds<<",\"preparation_seconds\":"<<preparation;if(jsonl)std::cout<<"}\n"<<std::flush;else std::cout<<",\"calls\":[";size_t completedCalls=0;
 for(size_t call=0;call<calls;call++){
  if(wall>0&&elapsed(programStart)>=wall)break;uint32_t s=seed+call;std::mt19937 rng(s);std::string arm=mode;if(mode=="mixed")arm=std::uniform_real_distribution<double>(0,1)(rng)<0.5?"helpers":"vectors";
  std::vector<Substitution>prefix;std::vector<Vector>seeds;std::vector<size_t>removed;auto sampling=Clock::now();
  if(arm=="vectors")seeds=reducer.getVectors(intermediates,rng,minRemove,maxRemove);
  else if(arm=="explicit"){const auto&selection=removedRows.empty()?explicitRemoved:removedRows[call%removedRows.size()];for(size_t j=0;j<intermediates.size();j++)if(!selection.count(j))seeds.push_back(intermediates[j]);}
  else if(arm=="helpers"){auto count=std::uniform_int_distribution<size_t>(size_t(donor.getAdditions()*.1),size_t(donor.getAdditions()*.5))(rng);prefix=pool.getRandomSubstitutions(rng,count);}
  else if(arm=="retention")prefix=retention(donor,rng,retain);
  if(arm=="vectors"||arm=="explicit"){std::unordered_set<Vector>remaining(seeds.begin(),seeds.end());for(size_t j=0;j<intermediates.size();j++)if(!remaining.count(intermediates[j]))removed.push_back(j);}
  double sampleSeconds=elapsed(sampling);if(wall>0){double remain=wall-elapsed(programStart);if(remain<=0)break;params.maxTimeInSeconds=std::min(seconds,remain);}auto scorer=std::make_shared<vector_covering::DistanceScorer>(1000.,1.,savings,10.,slack);auto selector=std::make_shared<GreedyAlternativeSelector>();vector_covering::VectorCoveringSolver solver(targets,params,scorer,selector,s);
  if(a.count("--bound"))solver.setBound(std::stoull(a.at("--bound")));auto start=Clock::now();std::optional<size_t>result;
  if(arm=="vectors"||arm=="explicit")result=solver.solve(seeds);else if(arm=="scratch")result=solver.solve();else result=solver.solve(prefix);double solveSeconds=elapsed(start);
  if(completedCalls&&!jsonl)std::cout<<',';std::cout<<"{\"event\":\"draw\",\"seed\":"<<s<<",\"arm\":\""<<arm<<"\",\"retained_vectors\":"<<seeds.size()<<",\"prefix_gates\":"<<prefix.size()<<",\"sampling_seconds\":"<<sampleSeconds<<",\"solver_seconds\":"<<solveSeconds<<",\"removed_helper_indices\":[";for(size_t j=0;j<removed.size();j++){if(j)std::cout<<',';std::cout<<removed[j];}std::cout<<"],\"status\":\""<<(result?"complete":"timeout_or_bound_or_no_candidate")<<"\",\"solution\":";
  if(result){auto solution=solver.getSolution();require(system.validateSolution(solution),"Completion fails native exact replay");for(auto g:solution.substitutions)require((g.ai==1||g.ai==-1)&&(g.aj==1||g.aj==-1),"Nonunit completion scalar");for(auto row:solution.expressions)for(auto t:row)require(t.value==1||t.value==-1,"Nonunit output scalar");raw(std::cout,solution);}else std::cout<<"null";
  std::cout<<'}';if(jsonl)std::cout<<'\n';std::cout<<std::flush;completedCalls++;
 }
 if(jsonl)std::cout<<"{\"event\":\"summary\",\"draws\":"<<completedCalls<<",\"elapsed_seconds\":"<<elapsed(programStart)<<"}\n";else std::cout<<"]}\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
