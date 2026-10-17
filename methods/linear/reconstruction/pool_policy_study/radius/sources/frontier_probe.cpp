// Test harness only: exercise the actual native last_viable implementation.
#define main frontier_search_main
#include "frontier.cpp"
#undef main
int main(){
 while(cin>>N>>I>>O>>H>>E){
  targets.resize(O);helpers.resize(H);edges.resize(E);byparent.assign(N,{});byout.assign(N,{});mandatory.assign(N,0);
  for(int i=0;i<I;++i)mandatory[i]=1;for(int&t:targets){cin>>t;mandatory[t]=1;}for(int&h:helpers)cin>>h;
  for(int e=0;e<E;++e){auto&p=edges[e];cin>>p.o>>p.a>>p.b;byparent[p.a].push_back(e);if(p.a!=p.b)byparent[p.b].push_back(e);byout[p.o].push_back(e);}
  auto s=close({});cout<<"READY";for(int i=0;i<N;++i)if(s.ready[i])cout<<" "<<i;cout<<"\nVIABLE";for(int h:viable(s))cout<<" "<<h;cout<<"\nLAST";for(int h:last_viable(s))cout<<" "<<h;cout<<"\n";
 }
}
