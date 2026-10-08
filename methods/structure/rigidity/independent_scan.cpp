// Independent complete scanner for p=2,3; bit-plane row arithmetic.
#include <fstream>
#include <iostream>
#include <vector>
#include <array>
#include <cstdint>
#include <chrono>
using namespace std;
struct V{uint32_t one=0,two=0;};
V plus3(V a,V b,uint32_t mask){uint32_t za=mask^(a.one|a.two),zb=mask^(b.one|b.two);return {(za&b.one)|(a.one&zb)|(a.two&b.two),(za&b.two)|(a.two&zb)|(a.one&b.one)};}
int main(int argc,char**argv){if(argc!=3)return 2;ifstream f(argv[1]);ofstream out(argv[2]);int p,n,m,h;f>>p>>n>>m>>h;if(p!=2&&p!=3)return 3;uint32_t mask=(1u<<m)-1;
 vector<vector<V>> E(h,vector<V>(n));for(int k=0;k<h;k++)for(int i=0;i<n;i++)for(int j=0;j<m;j++){int x;f>>x;if(x==1)E[k][i].one|=1u<<j;if(x==2)E[k][i].two|=1u<<j;}
 uint64_t count=0,nonempty=0;vector<uint64_t> hist(m+1);auto start=chrono::steady_clock::now();
 // Generate each nonzero vector, retain the unique representative whose
 // LAST nonzero coordinate is 1 (different chart order from the first scanner).
 for(int last=0;last<n;last++){uint64_t limit=1;for(int i=0;i<last;i++)limit*=p;for(uint64_t k=0;k<limit;k++){
 array<int,32>a{};a[last]=1;uint64_t q=k;for(int i=0;i<last;i++){a[i]=q%p;q/=p;}
 array<V,32> basis{};int rk=0;
 for(auto&e:E){V row;for(int i=0;i<=last;i++)if(a[i]){V z=e[i];if(a[i]==2)swap(z.one,z.two);if(p==2)row.one^=z.one;else row=plus3(row,z,mask);}
  while(row.one|row.two){uint32_t all=row.one|row.two;int pivot=31-__builtin_clz(all);if((basis[pivot].one|basis[pivot].two)==0){if(row.two&(1u<<pivot))swap(row.one,row.two);basis[pivot]=row;rk++;break;}if(p==2)row.one^=basis[pivot].one;else{V z=basis[pivot];if(row.one&(1u<<pivot))swap(z.one,z.two);row=plus3(row,z,mask);}}
  if(rk==m)break;
 }
 count++;hist[m-rk]++;if(rk<m){nonempty++;for(int i=0;i<n;i++)out<<a[i]<<' ';out<<"| "<<m-rk<<'\n';}
 }}
 cout<<"{\"projective_first_factors\":"<<count<<",\"nonempty_first_fibers\":"<<nonempty<<",\"seconds\":"<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<",\"kernel_dimension_histogram\":[";for(int i=0;i<=m;i++){if(i)cout<<',';cout<<hist[i];}cout<<"]}\n";
}
