#include <fstream>
#include <iostream>
#include <vector>
#include <array>
#include <cstdint>
#include <chrono>
using namespace std;
struct Entry {int i,j,v;};
int main(int argc,char**argv){
 if(argc!=3)return 2; ifstream in(argv[1]);ofstream out(argv[2]);int p,n,m,h;in>>p>>n>>m>>h;
 vector<vector<Entry>> eq(h);for(int k=0;k<h;k++)for(int i=0;i<n;i++)for(int j=0;j<m;j++){int z;in>>z;if(z)eq[k].push_back({i,j,z});}
 vector<int> inv(p);for(int a=1;a<p;a++)for(int b=1;b<p;b++)if(a*b%p==1)inv[a]=b;
 uint64_t tested=0,hits=0,nonempty=0;vector<uint64_t> hist(m+1);auto start=chrono::steady_clock::now();
 for(int first=0;first<n;first++){
 uint64_t lim=1;for(int j=first+1;j<n;j++)lim*=p;
 for(uint64_t k=0;k<lim;k++){
  array<int,32>a{};a[first]=1;uint64_t kk=k;for(int j=first+1;j<n;j++){a[j]=kk%p;kk/=p;}
  array<array<int,32>,32>B{};array<bool,32>used{};int rank=0;
  for(auto &equation:eq){array<int,32>r{};for(auto&e:equation)r[e.j]+=a[e.i]*e.v;for(int j=0;j<m;j++)r[j]%=p;
   for(int j=0;j<m;j++)if(r[j]){if(used[j]){int z=r[j];for(int c=j;c<m;c++)r[c]=(r[c]+p-z*B[j][c]%p)%p;}else{int z=inv[r[j]];for(int c=j;c<m;c++)B[j][c]=r[c]*z%p;used[j]=true;rank++;break;}}
   if(rank==m)break;
  }
  tested++;hist[m-rank]++;if(rank==m)continue;nonempty++;
  vector<array<int,32>> basis;for(int free=0;free<m;free++)if(!used[free]){array<int,32>b{};b[free]=1;for(int j=m-1;j>=0;j--)if(used[j]){int s=0;for(int c=j+1;c<m;c++)s+=B[j][c]*b[c];b[j]=(p-s%p)%p;}basis.push_back(b);}
  int d=basis.size();for(int fb=0;fb<d;fb++){uint64_t blim=1;for(int c=fb+1;c<d;c++)blim*=p;for(uint64_t v=0;v<blim;v++){array<int,32>b=basis[fb];uint64_t vv=v;for(int c=fb+1;c<d;c++){int z=vv%p;vv/=p;for(int j=0;j<m;j++)b[j]=(b[j]+z*basis[c][j])%p;}int z=0;for(int j=0;j<m;j++)if(b[j]){z=inv[b[j]];break;}for(int j=0;j<m;j++)b[j]=b[j]*z%p;
   for(int i=0;i<n;i++)out<<a[i]<<' ';out<<'|';for(int j=0;j<m;j++)out<<' '<<b[j];out<<'\n';hits++;}}
 }
 }
 double sec=chrono::duration<double>(chrono::steady_clock::now()-start).count();cout<<"{\"tested_projective_first_factors\":"<<tested<<",\"rank_one_points\":"<<hits<<",\"nonempty_first_fibers\":"<<nonempty<<",\"elapsed_seconds\":"<<sec<<",\"kernel_dimension_histogram\":[";for(int i=0;i<=m;i++){if(i)cout<<',';cout<<hist[i];}cout<<"]}\n";
}
