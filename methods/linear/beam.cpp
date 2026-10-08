// Target-guided bounded 4-for-3 exchanges. Beam pruning is heuristic, not exhaustive.
#define main plateau_main
#include "plateau.cpp"
#undef main
int missing(const State&s){int n=0;for(int t:targets)n+=!s.ready[t];return n;}
State addhelper(const State& base,int h){++closures;State s=base;s.allowed[h]=1;for(int e:byout[h])if(s.ready[es[e].a]&&s.ready[es[e].b]){s.ready[h]=1;s.prod[h]=e;grow(s,{h});break;}return s;}
int main(int argc,char**argv){if(argc!=6)return 2;ifstream f(argv[1]);double secs=stod(argv[2]);mt19937 rng(stoul(argv[3]));int width=stoi(argv[4]);string out=argv[5];f>>N>>I>>O>>H>>E;targets.resize(O);vector<int> hs(H);es.resize(E);parent.resize(N);byout.resize(N);mandatory.assign(N,0);for(int i=0;i<I;++i)mandatory[i]=1;for(int&t:targets){f>>t;mandatory[t]=1;}for(int&h:hs)f>>h;for(int e=0;e<E;++e){auto&p=es[e];f>>p.o>>p.a>>p.b;parent[p.a].push_back(e);if(p.a!=p.b)parent[p.b].push_back(e);byout[p.o].push_back(e);}if(!f)return 3;if(!done(close(hs)))return 4;
 vector<vector<int>> removals;for(int a=0;a<H;++a)for(int b=a+1;b<H;++b)for(int c=b+1;c<H;++c)for(int d=c+1;d<H;++d)removals.push_back({hs[a],hs[b],hs[c],hs[d]});shuffle(removals.begin(),removals.end(),rng);auto start=chrono::steady_clock::now();
 for(auto&removed:removals){++steps;vector<int> keep;for(int h:hs)if(find(removed.begin(),removed.end(),h)==removed.end())keep.push_back(h);vector<State> beam{close(keep)};for(int depth=0;depth<3;++depth){vector<pair<pair<int,int>,State>> children;for(auto&s:beam){auto choices=viable(s);shuffle(choices.begin(),choices.end(),rng);for(int h:choices){auto t=addhelper(s,h);if(done(t)){save(t,out);cerr<<"FOUND removed=";for(int h:removed)cerr<<h<<",";cerr<<" steps="<<steps<<" closures="<<closures<<" seconds="<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<"\n";return 0;}int ready=count(t.ready.begin(),t.ready.end(),1);children.push_back({{missing(t),-ready},std::move(t)});}}
 stable_sort(children.begin(),children.end(),[](auto&a,auto&b){return a.first<b.first;});beam.clear();set<vector<char>> seen;for(auto&item:children){if(seen.insert(item.second.ready).second){beam.push_back(std::move(item.second));if((int)beam.size()==width)break;}}
 if(chrono::duration<double>(chrono::steady_clock::now()-start).count()>secs){cerr<<"TIME_LIMIT steps="<<steps<<" closures="<<closures<<" width="<<width<<" seconds="<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<"\n";return 0;}}
 }cerr<<"BEAM_COMPLETE_4_FOR_3 steps="<<steps<<" closures="<<closures<<" width="<<width<<"\n";
}
