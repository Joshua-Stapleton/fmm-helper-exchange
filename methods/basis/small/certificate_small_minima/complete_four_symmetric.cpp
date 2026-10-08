#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <unordered_map>
#include <vector>
using Vec=std::array<int64_t,12>;
struct Hash{size_t operator()(const Vec&v)const{uint64_t h=1469598103934665603ull;for(auto x:v){h^=uint64_t(x);h*=1099511628211ull;}return h;}};
Vec canon(Vec v){for(auto x:v)if(x){if(x<0)for(auto&y:v)y=-y;break;}return v;}
Vec combine(const Vec&a,const Vec&b,int s=1){Vec v{};for(int i=0;i<12;i++)v[i]=a[i]+s*b[i];return canon(v);}
bool nonzero(const Vec&v){for(auto x:v)if(x)return true;return false;}
struct Basis{uint32_t p[32]={};int rank=0;void add(uint32_t x){while(x){int j=31-__builtin_clz(x);if(!p[j]){p[j]=x;rank++;return;}x^=p[j];}}};
struct Anchor{uint32_t t;bool h;};
int main(int argc,char**argv){
 if(argc!=3)return 2;std::ifstream in(argv[1]);std::ofstream out(argv[2]);int q,d,patterns;in>>q>>d>>patterns;if(q+4>31||d>12)return 3;
 std::vector<Vec>T(q);std::unordered_map<Vec,int,Hash>ti;for(int i=0;i<q;i++){for(int j=0;j<d;j++)in>>T[i][j];T[i]=canon(T[i]);ti[T[i]]=i;}
 std::unordered_map<Vec,std::vector<Anchor>,Hash>anchors;std::unordered_map<Vec,int,Hash>pairset;Basis base;
 for(int i=0;i<q;i++){
  Vec half=T[i];for(auto&x:half){if(x%2)return 4;x/=2;}anchors[half].push_back({1u<<i,false});
  for(int j=i;j<q;j++)for(int sg:{-1,1}){Vec h=combine(T[i],T[j],sg);if(!nonzero(h))continue;pairset[h]=1;auto it=ti.find(h);if(it!=ti.end())base.add((1u<<i)^(1u<<j)^(1u<<it->second));else anchors[h].push_back({(1u<<i)^(1u<<j),true});}
 }
 std::vector<Vec>dom[3],pos[3];dom[0].push_back({});pos[0]=dom[0];pos[1]=T;for(auto&[v,k]:pairset)pos[2].push_back(v);
 for(int t=1;t<=2;t++){std::sort(pos[t].begin(),pos[t].end());dom[t]=pos[t];for(auto v:pos[t]){for(auto&x:v)x=-x;dom[t].push_back(v);}}
 uint64_t trials=0,valid=0,hits=0;int minimum=q;std::unordered_map<int,uint64_t>hist;
 for(int pat=0;pat<patterns;pat++){
  int det,types[4],adj[4][4];in>>det;for(auto&t:types)in>>t;for(auto&r:adj)for(auto&x:r)in>>x;
  // Disjoint adjugate blocks permit independent sign flips of all their helpers.
  int parent[4]={0,1,2,3};auto root=[&](int x){while(parent[x]!=x)x=parent[x];return x;};
  for(int i=0;i<4;i++)for(int j=0;j<4;j++)for(int k=j+1;k<4;k++)if(adj[i][j]&&adj[i][k])parent[root(k)]=root(j);
  bool positive[4]={};for(int j=0;j<4;j++)if(types[j]){bool prior=false;for(int k=0;k<j;k++)if(types[k]&&root(k)==root(j))prior=true;if(!prior)positive[j]=true;}
  const auto&A=positive[0]?pos[types[0]]:dom[types[0]];const auto&B=positive[1]?pos[types[1]]:dom[types[1]];const auto&C=positive[2]?pos[types[2]]:dom[types[2]];const auto&D=positive[3]?pos[types[3]]:dom[types[3]];
  // Equal isolated one-helper blocks are interchangeable labels.
  int isolated[4]={};for(int j=0;j<4;j++){int row=-1,count=0;for(int i=0;i<4;i++)if(adj[i][j]){row=i;count++;}if(count==1){int n=0;for(int k=0;k<4;k++)if(adj[row][k])n++;if(n==1)isolated[j]=std::abs(adj[row][j]);}}
  bool order[4][4]={};for(int j=0;j<4;j++)for(int k=j+1;k<4;k++)order[j][k]=isolated[j]&&isolated[j]==isolated[k]&&types[j]==types[k];
  uint64_t old=trials,oldhits=hits;int pmin=q;
  for(auto&a:A)for(auto&b:B)for(auto&c:C)for(auto&dd:D){
   const Vec*r[4]={&a,&b,&c,&dd};bool ordered=true;for(int j=0;j<4;j++)for(int k=j+1;k<4;k++)if(order[j][k]&&*r[k]<*r[j])ordered=false;if(!ordered)continue;
   trials++;std::array<Vec,4>h{};bool ok=true;
   for(int i=0;i<4;i++){for(int k=0;k<d;k++){int64_t v=0;for(int j=0;j<4;j++)v+=adj[i][j]*(*r[j])[k];if(v%det){std::cerr<<"nonintegral scale\n";return 5;}h[i][k]=v/det;}h[i]=canon(h[i]);if(!nonzero(h[i])||ti.count(h[i])){ok=false;break;}}
   for(int i=0;i<4;i++)for(int j=i+1;j<4;j++)if(h[i]==h[j])ok=false;if(!ok)continue;valid++;Basis all=base,hp;
   auto add=[&](uint32_t t,uint32_t hm){all.add(t|(hm<<q));hp.add(hm);};
   for(int i=0;i<4;i++){auto it=anchors.find(h[i]);if(it!=anchors.end())for(auto r:it->second)add(r.t,r.h?1u<<i:0);}
   for(int i=0;i<4;i++)for(int j=i+1;j<4;j++){
    for(int sg:{-1,1}){Vec v=combine(h[i],h[j],sg);auto it=ti.find(v);if(it!=ti.end())add(1u<<it->second,(1u<<i)|(1u<<j));for(int k=0;k<4;k++)if(k!=i&&k!=j&&v==h[k])add(0,(1u<<i)|(1u<<j)|(1u<<k));}
    if(combine(h[i],h[i])==h[j])add(0,1u<<j);
    if(combine(h[j],h[j])==h[i])add(0,1u<<i);
   }
   int z=q+hp.rank-all.rank;pmin=std::min(pmin,z);minimum=std::min(minimum,z);hist[z]++;
   if(z<=d){hits++;out<<pat<<' '<<z;for(auto v:h)for(int k=0;k<d;k++)out<<' '<<v[k];out<<'\n';}
  }
  std::cout<<"{\"pattern\":"<<pat<<",\"trials\":"<<trials-old<<",\"hits\":"<<hits-oldhits<<",\"minimum\":"<<pmin<<"}\n"<<std::flush;
 }
 std::cout<<"{\"complete\":true,\"patterns\":"<<patterns<<",\"trials\":"<<trials<<",\"valid\":"<<valid<<",\"passes\":"<<hits<<",\"minimum\":"<<minimum<<",\"histogram\":{";bool first=true;for(auto[z,n]:hist){if(!first)std::cout<<',';first=false;std::cout<<'\"'<<z<<"\":"<<n;}std::cout<<"}}\n";
}
