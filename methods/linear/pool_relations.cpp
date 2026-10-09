// Exact sum/difference lookup for sign-canonical integer forms.
// The Python adapter bounds coefficients before invoking this int64 backend.
#include <cstdint>
#include <iostream>
#include <unordered_map>
#include <vector>
using Row=std::vector<std::int64_t>;
struct Hash {std::size_t operator()(const Row& v) const {
    std::uint64_t h=1469598103934665603ULL;
    for(auto x:v){h^=std::uint64_t(x);h*=1099511628211ULL;}return h;
}};
int main(){
    std::size_t count,width,roots;
    if(!(std::cin>>count>>width>>roots)||!width||roots>count)return 2;
    std::vector<Row> rows(count,Row(width));std::unordered_map<Row,std::size_t,Hash> ids;
    for(std::size_t i=0;i<count;i++){
        for(auto& x:rows[i])if(!(std::cin>>x))return 2;
        if(!ids.emplace(rows[i],i).second)return 2;
    }
    Row value(width);
    for(std::size_t a=0;a<count;a++)for(std::size_t b=a;b<count;b++)for(int sb:{1,-1}){
        int sign=0;
        for(std::size_t j=0;j<width;j++){
            value[j]=rows[a][j]+sb*rows[b][j];
            if(!sign&&value[j])sign=value[j]>0?1:-1;
        }
        if(!sign)continue;
        if(sign<0)for(auto& x:value)x=-x;
        auto found=ids.find(value);
        if(found!=ids.end()&&found->second>=roots&&found->second!=a&&found->second!=b)
            std::cout<<found->second<<' '<<a<<' '<<sign<<' '<<b<<' '<<sign*sb<<'\n';
    }
}
