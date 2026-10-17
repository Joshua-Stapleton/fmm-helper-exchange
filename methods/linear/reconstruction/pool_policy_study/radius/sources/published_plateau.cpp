// Randomized feasible helper-set expansion, deletion and plateau population.
// Each accepted population state is exact closure-feasible; Python verifies outputs.
#include <algorithm>
#include <chrono>
#include <fstream>
#include <iostream>
#include <random>
#include <set>
#include <vector>
using namespace std;
struct Edge {int o,a,b;};
int N,I,O,H,E; vector<int> targets; vector<Edge> es;
vector<vector<int>> parent,byout;vector<char> mandatory;
long long closures=0,steps=0,accepted=0;
struct State { vector<char> allowed,ready;vector<int> prod; };
void grow(State&s,vector<int> q){for(size_t j=0;j<q.size();++j)for(int e:parent[q[j]]){auto p=es[e];if(s.allowed[p.o]&&!s.ready[p.o]&&s.ready[p.a]&&s.ready[p.b]){s.ready[p.o]=1;s.prod[p.o]=e;q.push_back(p.o);}}}
State close(const vector<int>& hs){++closures;State s{mandatory,vector<char>(N,0),vector<int>(N,-1)};for(int h:hs)s.allowed[h]=1;vector<int> q;for(int i=0;i<I;++i){q.push_back(i);s.ready[i]=1;}grow(s,q);return s;}
bool done(const State&s){for(int t:targets)if(!s.ready[t])return false;return true;}
vector<int> live(const State&s){vector<char> used(N,0);vector<int> q=targets,hs;for(size_t j=0;j<q.size();++j){int v=q[j];if(v<I||used[v])continue;used[v]=1;if(!mandatory[v])hs.push_back(v);auto p=es[s.prod[v]];q.push_back(p.a);q.push_back(p.b);}sort(hs.begin(),hs.end());return hs;}
vector<int> viable(const State&s){vector<int> v;for(int o=I;o<N;++o){if(s.allowed[o])continue;for(int e:byout[o])if(s.ready[es[e].a]&&s.ready[es[e].b]){v.push_back(o);break;}}return v;}
void save(const State&s,const string& path){ofstream f(path);f<<"FOUND\n";for(int i=0;i<N;++i)if(s.ready[i]&&s.prod[i]>=0)f<<i<<" "<<s.prod[i]<<"\n";}
int main(int argc,char**argv){if(argc!=6)return 2;ifstream f(argv[1]);double secs=stod(argv[2]);mt19937 rng(stoul(argv[3]));int perturb=stoi(argv[4]);string out=argv[5];f>>N>>I>>O>>H>>E;targets.resize(O);vector<int> initial(H);es.resize(E);parent.resize(N);byout.resize(N);mandatory.assign(N,0);for(int i=0;i<I;++i)mandatory[i]=1;for(int&t:targets){f>>t;mandatory[t]=1;}for(int&h:initial)f>>h;for(int e=0;e<E;++e){auto&p=es[e];f>>p.o>>p.a>>p.b;parent[p.a].push_back(e);if(p.a!=p.b)parent[p.b].push_back(e);byout[p.o].push_back(e);}if(!f)return 3;
 auto base=close(initial);if(!done(base))return 4;initial=live(base);int best=initial.size();vector<vector<int>> pop{initial};set<vector<int>> seen{initial};auto start=chrono::steady_clock::now();
 while(chrono::duration<double>(chrono::steady_clock::now()-start).count()<secs){++steps;auto hs=pop[rng()%pop.size()];State s=close(hs);int adds=1+rng()%perturb;for(int k=0;k<adds;++k){auto v=viable(s);if(v.empty())break;hs.push_back(v[rng()%v.size()]);s=close(hs);}shuffle(hs.begin(),hs.end(),rng);for(int j=0;j<(int)hs.size();){auto attempt=hs;attempt.erase(attempt.begin()+j);auto t=close(attempt);if(done(t)){hs=std::move(attempt);s=std::move(t);}else ++j;}hs=live(s);if((int)hs.size()>best)continue;if((int)hs.size()<best){best=hs.size();pop.clear();seen.clear();save(s,out);cerr<<"IMPROVED helpers="<<best<<" step="<<steps<<" seconds="<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<"\n";}if(seen.insert(hs).second){++accepted;if(pop.size()<512)pop.push_back(hs);else pop[rng()%pop.size()]=hs;}if(steps%128==0){for(auto& p:parent)shuffle(p.begin(),p.end(),rng);}}
 cerr<<"FINISHED steps="<<steps<<" closures="<<closures<<" accepted="<<accepted<<" seen="<<seen.size()<<" best_helpers="<<best<<" initial_helpers="<<initial.size()<<" seconds="<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<"\n";
 return 0;
}
