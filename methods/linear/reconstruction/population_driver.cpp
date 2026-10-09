// Public-API instrumentation: export complete LEO restart-round populations.
#include <leo/leo.h>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <random>
#include <stdexcept>
using namespace leo;
int main(int argc,char**argv){
 try{
  std::map<std::string,std::string> arguments;
  for(int i=1;i<argc;i+=2){if(i+1>=argc)throw std::runtime_error("flag needs value");arguments[argv[i]]=argv[i+1];}
  auto get=[&](std::string key,std::string value){return arguments.count(key)?arguments[key]:value;};
  std::ifstream input(arguments.at("--input"));size_t rows,columns;
  if(!(input>>rows>>columns)||!rows||!columns)throw std::runtime_error("invalid matrix header");
  std::vector<std::vector<int>> matrix(rows,std::vector<int>(columns));
  for(auto&row:matrix)for(auto&value:row)if(!(input>>value))throw std::runtime_error("invalid matrix body");
  ExpressionsSystem system(matrix);Reducer reducer(1);reducer.addGroup(system);
  std::mt19937 generator(std::stoul(get("--seed","20261009")));
  vector_covering::Parameters parameters={system.getMaxAbsValue(),false,true,false};
  auto preset=get("--preset","distance");
  if(preset!="distance"&&preset!="default")throw std::runtime_error("unknown preset");
  StrategyPool strategies=preset=="default"?presets::vectorCoveringDefault(parameters):presets::vectorCoveringDistance(parameters);
  auto output=std::filesystem::path(arguments.at("--out"));std::filesystem::create_directories(output);
  size_t rounds=std::stoul(get("--rounds","6")),iterations=std::stoul(get("--iterations","4"));
  size_t initialCse=std::stoul(get("--first-cse","10"));
  long long gap=std::stoll(get("--export-gap","-1"));
  size_t exported=0;auto start=std::chrono::steady_clock::now();
  for(size_t round=0;round<rounds;round++){
   TaskPool tasks=strategies.sample(iterations,generator);
   if(round==0&&initialCse)tasks.add(presets::cseAll().sample(initialCse,generator));
   reducer.reduce({tasks},false,true);
   auto dump=[&](const Solution&source,std::string name){
    auto solution=SolutionSubstitutionInliner().optimize(source);
    if(!system.validateSolution(solution))throw std::runtime_error("invalid population solution");
    std::ofstream stream(output/name);if(!stream)throw std::runtime_error("cannot open population output");
    JsonSolutionFormatter().format(stream,solution);
   };
   dump(reducer.getSolution(0),"best.json");
   for(const auto&solution:reducer.getSolutions(0))
    if(gap<0||solution.getAdditions()<=reducer.getAdditions(0)+static_cast<size_t>(gap))
     dump(solution,"donor_"+std::to_string(exported++)+".json");
   std::cout<<"round="<<round+1<<" best="<<reducer.getAdditions(0)<<" exported="<<exported
            <<" seconds="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<std::endl;
  }
 }catch(const std::exception&error){std::cerr<<error.what()<<std::endl;return 1;}
}
