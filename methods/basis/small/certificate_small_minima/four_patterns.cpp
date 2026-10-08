#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
#include <vector>
using Row=std::array<int,4>;using Mat=std::array<Row,4>;
Row normalized(Row r){for(int x:r)if(x){if(x<0)for(int&v:r)v=-v;break;}return r;}
int type(Row r){int sum=0,nonzero=0;for(int x:r){sum+=std::abs(x);nonzero+=x!=0;}if(sum==1)return 2;if(sum==2)return 1;return 0;}
int det(Mat a){int total=0;Row p={0,1,2,3};do{int sign=1,v=1;for(int i=0;i<4;i++){v*=a[i][p[i]];for(int j=0;j<i;j++)if(p[j]>p[i])sign=-sign;}total+=sign*v;}while(std::next_permutation(p.begin(),p.end()));return total;}
uint64_t canonical(const Mat&A,const std::vector<Row>&perms){uint64_t best=UINT64_MAX;for(auto p:perms)for(int signs=0;signs<8;signs++){std::array<unsigned,4>code{};for(int i=0;i<4;i++){Row r{};for(int j=0;j<4;j++)r[j]=A[i][p[j]]*((j>0&&(signs&(1<<(j-1))))?-1:1);r=normalized(r);for(int x:r)code[i]=5*code[i]+x+2;}std::sort(code.begin(),code.end());uint64_t key=0;for(auto c:code)key=(key<<10)|c;best=std::min(best,key);}return best;}
Mat decode(uint64_t key){Mat a{};for(int i=3;i>=0;i--){int c=key&1023;key>>=10;for(int j=3;j>=0;j--){a[i][j]=c%5-2;c/=5;}}return a;}
int main(){std::set<Row>S;auto add=[&](Row r){S.insert(normalized(r));};
 for(int i=0;i<4;i++)for(int c:{1,2}){Row r{};r[i]=c;add(r);}
 for(int i=0;i<4;i++)for(int j=i+1;j<4;j++)for(int s:{-1,1}){Row r{};r[i]=1;r[j]=s;add(r);}
 for(int i=0;i<4;i++)for(int j=0;j<4;j++)if(i!=j)for(int s:{-1,1}){Row r{};r[i]=2;r[j]=s;add(r);}
 for(int i=0;i<4;i++)for(int j=i+1;j<4;j++)for(int k=j+1;k<4;k++)for(int s:{-1,1})for(int t:{-1,1}){Row r{};r[i]=1;r[j]=s;r[k]=t;add(r);}
 std::vector<Row>rows(S.begin(),S.end()),perms;Row p={0,1,2,3};do{perms.push_back(p);}while(std::next_permutation(p.begin(),p.end()));std::set<uint64_t>classes;uint64_t nonsingular=0;
 int n=rows.size();for(int i=0;i<n;i++)for(int j=i+1;j<n;j++)for(int k=j+1;k<n;k++)for(int l=k+1;l<n;l++){Mat a={rows[i],rows[j],rows[k],rows[l]};if(!det(a))continue;nonsingular++;if(!(type(a[0])||type(a[1])||type(a[2])||type(a[3])))continue;classes.insert(canonical(a,perms));}
 std::cout<<"{\"coefficient_rows\":"<<n<<",\"nonsingular_triples\":"<<nonsingular<<",\"patterns\":[";bool first=true;for(auto key:classes){if(!first)std::cout<<',';first=false;Mat a=decode(key);std::cout<<"{\"det\":"<<det(a)<<",\"types\":[";for(int i=0;i<4;i++){if(i)std::cout<<',';std::cout<<type(a[i]);}std::cout<<"],\"A\":[";for(int i=0;i<4;i++){if(i)std::cout<<',';std::cout<<'[';for(int j=0;j<4;j++){if(j)std::cout<<',';std::cout<<a[i][j];}std::cout<<']';}std::cout<<"]}";}std::cout<<"]}\n";
}
