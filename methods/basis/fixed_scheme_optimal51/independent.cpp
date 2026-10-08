// Independent exhaustive superset test of all <=12-gate arbitrary-root circuits.
// Input:20 distinct sign-canonical vectors of width9, scaled by2.
// Enumerate all nontarget H=canonical(Ti +/- Tj) or Ti/2.
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <vector>
using V=std::array<int,9>;using Mask=uint32_t;
V canon(V v){for(auto x:v){if(!x)continue;if(x<0)for(auto&y:v)y=-y;break;}return v;}
bool nonzero(V v){for(auto x:v)if(x)return true;return false;}
struct Rule{Mask in,out;};
std::vector<Rule> rules(const std::vector<V>&f){
 std::map<V,int> ids;for(int i=0;i<(int)f.size();i++)ids[f[i]]=i;
 std::set<std::pair<Mask,Mask>> uniq;
 for(int i=0;i<(int)f.size();i++)for(int j=i;j<(int)f.size();j++)for(int s:{-1,1}){
  V v;for(int k=0;k<9;k++)v[k]=f[i][k]+s*f[j][k];v=canon(v);auto it=ids.find(v);
  if(it!=ids.end()&&it->second!=i&&it->second!=j)uniq.emplace((1u<<i)|(1u<<j),1u<<it->second);
 }
 std::vector<Rule> out;for(auto [i,o]:uniq)out.push_back({i,o});return out;
}
int main(int argc,char**argv){
 if(argc!=2)return 2;
 auto begin=std::chrono::steady_clock::now();std::ifstream in(argv[1]);int n,w;in>>n>>w;if(n!=20||w!=9)return 3;
 std::vector<V> ts(n);for(auto&v:ts){for(auto&x:v)in>>x;v=canon(v);}if(!in)return 4;
 std::set<V> tv(ts.begin(),ts.end());if(tv.size()!=20||tv.count(V{}))return 5;
 auto rr=rules(ts);const Mask full=(1u<<20)-1,H=1u<<20;
 std::vector<Mask> closure(1u<<20);
 // Every enlargement has a greater integer mask, so this recurrence is exact.
 for(int64_t m=full;m>=0;m--){Mask out=m;for(auto r:rr)if((out&r.in)==r.in&&!(out&r.out)){out=closure[out|r.out];break;}closure[m]=out;}
 std::set<Mask> roots8,roots9;uint64_t raw8=0,raw9=0;
 for(Mask m=0;m<=full;m++){int c=__builtin_popcount(m);if(c==8){roots8.insert(closure[m]);raw8++;}if(c==9){roots9.insert(closure[m]);raw9++;}}
 if(raw8!=125970||raw9!=167960||roots9.count(full))return 6;
 std::set<V> helpers;
 for(int i=0;i<20;i++){
  V half;for(int k=0;k<9;k++){if(ts[i][k]%2)return 7;half[k]=ts[i][k]/2;}helpers.insert(canon(half));
  for(int j=i;j<20;j++)for(int s:{-1,1}){V v;for(int k=0;k<9;k++)v[k]=ts[i][k]+s*ts[j][k];helpers.insert(canon(v));}
 }
 helpers.erase(V{});for(auto t:tv)helpers.erase(t);
 uint64_t tested=0;unsigned maximum=0;size_t hi=0;
 for(auto helper:helpers){
  auto f=ts;f.push_back(helper);auto rs=rules(f);std::vector<Rule> extra;
  for(auto r:rs)if((r.in|r.out)&H)extra.push_back(r);
  auto run=[&](Mask initial){
   Mask mask=initial;bool change=true;
   while(change){change=false;for(auto r:extra)if((mask&r.in)==r.in&&!(mask&r.out)){mask|=r.out;mask=(mask&H)|closure[mask&full];change=true;}}
   tested++;maximum=std::max(maximum,(unsigned)__builtin_popcount(mask&full));
   if((mask&full)==full){std::cout<<"{\"status\":\"WITNESS\",\"helper_index\":"<<hi<<",\"root_closure\":"<<initial<<"}\n";return false;}
   return true;
  };
  for(auto m:roots8)if(!run(m|H))return 1;
  for(auto m:roots9)if(!run(m))return 1;
  hi++;
 }
 double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();
 std::cout<<"{\"status\":\"PASS\",\"helpers\":"<<helpers.size()<<",\"base_rules\":"<<rr.size()<<",\"root_subsets_per_helper\":"<<(raw8+raw9)<<",\"covered_root_subsets\":"<<(raw8+raw9)*helpers.size()<<",\"distinct_closure_tests\":"<<tested<<",\"max_targets_reached\":"<<maximum<<",\"no_12_gate_circuit\":true,\"seconds\":"<<seconds<<"}\n";
}
