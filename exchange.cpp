// Bounded exhaustive helper exchanges, with exact production closure.
// Coefficients are independently checked by the Python exporter/replayer.
#include <algorithm>
#include <chrono>
#include <fstream>
#include <iostream>
#include <vector>
using namespace std;
struct Edge {int o,a,b;};
int N,I,O,H,E;vector<int> targets,helpers;vector<Edge> edges;
vector<vector<int>> byparent,byout;vector<char> mandatory;
long long closures=0,pairs=0,triples=0;
auto start=chrono::steady_clock::now();double limitsec;
bool expired(){return chrono::duration<double>(chrono::steady_clock::now()-start).count()>limitsec;}
struct State{vector<char> allowed,ready;vector<int> prod;int nt=0;};
void grow(State& s,vector<int> queue){
  size_t cursor=0;
  while(cursor<queue.size()){
    int v=queue[cursor++];
    for(int e:byparent[v]){
      auto p=edges[e];
      if(!s.allowed[p.o]||s.ready[p.o]||!s.ready[p.a]||!s.ready[p.b])continue;
      s.ready[p.o]=1;s.prod[p.o]=e;queue.push_back(p.o);
    }
  }
}
State close(const vector<int>& removed){
  ++closures;State s{mandatory,vector<char>(N,0),vector<int>(N,-1)};
  for(int h:helpers)s.allowed[h]=1;
  for(int h:removed)s.allowed[h]=0;
  vector<int> q;for(int i=0;i<I;++i){s.ready[i]=1;q.push_back(i);}
  grow(s,q);return s;
}
bool done(const State&s){for(int o:targets)if(!s.ready[o])return false;return true;}
vector<int> viable(const State&s){
  vector<int> v;
  for(int o=I;o<N;++o){
    if(s.allowed[o])continue;
    for(int e:byout[o])if(s.ready[edges[e].a]&&s.ready[edges[e].b]){v.push_back(o);break;}
  }
  return v;
}
State add(const State& base,int h){
  ++closures;State s=base;s.allowed[h]=1;
  for(int e:byout[h])if(s.ready[edges[e].a]&&s.ready[edges[e].b]){
    s.ready[h]=1;s.prod[h]=e;grow(s,{h});break;
  }
  return s;
}
void save(const State&s,const vector<int>&removed,const vector<int>&added){
  cout<<"FOUND\n"<<removed.size();for(int h:removed)cout<<" "<<h;cout<<"\n"<<added.size();for(int h:added)cout<<" "<<h;cout<<"\n";
  for(int i=0;i<N;++i)if(s.ready[i]&&s.prod[i]>=0)cout<<i<<" "<<s.prod[i]<<"\n";
}
int main(int argc,char**argv){
  if(argc!=3)return 2;limitsec=stod(argv[2]);ifstream f(argv[1]);
  f>>N>>I>>O>>H>>E;targets.resize(O);helpers.resize(H);edges.resize(E);byparent.resize(N);byout.resize(N);mandatory.assign(N,0);
  for(int i=0;i<I;++i)mandatory[i]=1;
  for(int&v:targets){f>>v;mandatory[v]=1;}for(int&v:helpers)f>>v;
  for(int i=0;i<E;++i){auto&p=edges[i];f>>p.o>>p.a>>p.b;byout[p.o].push_back(i);byparent[p.a].push_back(i);if(p.a!=p.b)byparent[p.b].push_back(i);}
  if(!f)return 3;
  if(!done(close({})))return 4;
  auto finish=[&](const char*status){cerr<<status<<" closures="<<closures<<" pairs="<<pairs<<" triples="<<triples<<" seconds="<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<"\n";};
  for(int a:helpers){auto s=close({a});if(done(s)){save(s,{a},{});finish("PASS");return 0;}}
  for(int a=0;a<H;++a)for(int b=a+1;b<H;++b){
    ++pairs;vector<int> removed{helpers[a],helpers[b]};auto s=close(removed);
    if(done(s)){save(s,removed,{});finish("PASS");return 0;}
    for(int h:viable(s)){auto t=add(s,h);if(done(t)){save(t,removed,{h});finish("PASS");return 0;}}
    if(expired()){finish("TIME_LIMIT");return 0;}
  }
  for(int a=0;a<H;++a)for(int b=a+1;b<H;++b)for(int c=b+1;c<H;++c){
    ++triples;vector<int> removed{helpers[a],helpers[b],helpers[c]};auto s=close(removed);
    if(done(s)){save(s,removed,{});finish("PASS");return 0;}
    for(int h:viable(s)){
      auto t=add(s,h);if(done(t)){save(t,removed,{h});finish("PASS");return 0;}
      for(int j:viable(t)){auto u=add(t,j);if(done(u)){save(u,removed,{h,j});finish("PASS");return 0;}}
      if(expired()){finish("TIME_LIMIT");return 0;}
    }
    if(expired()){finish("TIME_LIMIT");return 0;}
  }
  finish("EXHAUSTED_3_FOR_2");return 0;
}
