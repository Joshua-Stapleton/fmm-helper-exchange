#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <vector>
#include <unordered_map>
struct Rel{uint32_t t; unsigned h;};
struct Basis {uint32_t p[32]={};int r=0;void add(uint32_t x){while(x){int i=31-__builtin_clz(x);if(!p[i]){p[i]=x;r++;return;}x^=p[i];}}};
int main(int argc,char**argv){
 if(argc<3||argc>4)return 2;int helpers=argc==4?std::stoi(argv[3]):3;std::ifstream in(argv[1]);std::ofstream out(argv[2]);int q,d,H,G;in>>q>>d>>H>>G;if(q+helpers>31)return 3;
 std::vector<Rel> zero;std::vector<std::vector<Rel>> one(H),two(H*H);std::unordered_map<uint64_t,std::vector<Rel>> three;
 for(int x=0;x<G;x++){int a,b,c;in>>a>>b>>c;std::vector<int>h;for(int i:{a,b,c})if(i>=q)h.push_back(i-q);std::sort(h.begin(),h.end());h.erase(std::unique(h.begin(),h.end()),h.end());Rel r{0,0};for(int i:{a,b,c}){if(i<q)r.t^=1u<<i;else r.h^=1u<<(std::lower_bound(h.begin(),h.end(),i-q)-h.begin());}if(h.empty())zero.push_back(r);else if(h.size()==1)one[h[0]].push_back(r);else if(h.size()==2)two[h[0]*H+h[1]].push_back(r);else three[(uint64_t(h[0])*H+h[1])*H+h[2]].push_back(r);}
 auto apply=[q](Basis&b,Basis&hp,const std::vector<Rel>&rs,std::array<int,3>m){for(auto&r:rs){uint32_t z=0;for(int k=0;k<3;k++)if(r.h&(1u<<k))z|=1u<<m[k];b.add(r.t|(z<<q));hp.add(z);}};
 Basis base,hbase;apply(base,hbase,zero,{0,0,0});uint64_t tested=0,hits=0;int best=q;std::map<int,uint64_t>hist;
 auto add3=[&](Basis&b,Basis&hp,int i,int j,int k,std::array<int,3>m){auto it=three.find((uint64_t(i)*H+j)*H+k);if(it!=three.end())apply(b,hp,it->second,m);};
 auto check=[&](Basis&b,Basis&hp,int i,int j,int k,int l){int z=q+hp.r-b.r;hist[z]++;tested++;best=std::min(best,z);if(z<=d){hits++;out<<i<<' '<<j<<' '<<k;if(l>=0)out<<' '<<l;out<<' '<<z<<'\n';}};
 for(int i=0;i<H;i++){Basis b1=base,h1;apply(b1,h1,one[i],{0,0,0});for(int j=i+1;j<H;j++){Basis b2=b1,h2=h1;apply(b2,h2,one[j],{1,0,0});apply(b2,h2,two[i*H+j],{0,1,0});for(int k=j+1;k<H;k++){Basis b=b2,hp=h2;apply(b,hp,one[k],{2,0,0});apply(b,hp,two[i*H+k],{0,2,0});apply(b,hp,two[j*H+k],{1,2,0});add3(b,hp,i,j,k,{0,1,2});if(helpers==3)check(b,hp,i,j,k,-1);else for(int l=k+1;l<H;l++){Basis z=b,zp=hp;apply(z,zp,one[l],{3,0,0});apply(z,zp,two[i*H+l],{0,3,0});apply(z,zp,two[j*H+l],{1,3,0});apply(z,zp,two[k*H+l],{2,3,0});add3(z,zp,i,j,l,{0,1,3});add3(z,zp,i,k,l,{0,2,3});add3(z,zp,j,k,l,{1,2,3});check(z,zp,i,j,k,l);}}}}
 std::cout<<"{\"helpers_per_subset\":"<<helpers<<",\"subsets\":"<<tested<<",\"quotient_passes\":"<<hits<<",\"minimum_quotient\":"<<best<<",\"dimension\":"<<d<<",\"histogram\":{";bool f=true;for(auto[z,n]:hist){if(!f)std::cout<<',';f=false;std::cout<<'\"'<<z<<"\":"<<n;}std::cout<<"}}\n";
}
