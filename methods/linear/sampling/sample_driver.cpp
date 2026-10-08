// Local sequential sampler for pinned LEO API; upstream source is unmodified.
#include <leo/leo.h>
#include <leo/utils/solution_substitution_inliner.h>
#include <iostream>
#include <fstream>
#include <map>
#include <string>
#include <stdexcept>
using namespace leo;
int main(int argc,char**argv) {
 try {
  std::map<std::string,std::string> args;
  for(int i=1;i<argc;i+=2) { if(i+1>=argc)throw std::runtime_error("all flags require values"); args[argv[i]]=argv[i+1]; }
  auto get=[&](std::string k,std::string d){return args.count(k)?args[k]:d;};
  std::string mode=get("--mode","distance"); uint32_t seed=std::stoul(get("--seed","20261007"));
  size_t preset=std::stoul(get("--preset","0")); int slack=std::stoi(get("--support-slack","2"));
  bool targetPairs=get("--target-pairs","0")=="1";
  std::ifstream input(args.at("--input")); size_t rows,cols; if(!(input>>rows>>cols))throw std::runtime_error("invalid input");
  std::vector<std::vector<int>> matrix(rows,std::vector<int>(cols));for(auto& r:matrix)for(auto&x:r)if(!(input>>x))throw std::runtime_error("invalid matrix");
  ExpressionsSystem system(matrix);std::unique_ptr<Solver> solver; std::string strategy;
  if(mode=="distance"){
   auto scorer=std::make_shared<vector_covering::DistanceScorer>(1000.0,1.0,std::stod(get("--savings",preset?"0.01":"0.0")),10.0,slack);
   vector_covering::VectorCoveringParameters p={system.getMaxAbsValue(),true,true,targetPairs};
   solver=std::make_unique<vector_covering::VectorCoveringSolver>(matrix,p,scorer,std::make_shared<GreedyAlternativeSelector>(),seed);
   strategy="vec/dst"+std::to_string(preset+1)+"/slack"+std::to_string(slack);
  }else{
   StrategyPool strategies= mode=="distance"?presets::vectorCoveringDistance(system,targetPairs):mode=="default"?presets::vectorCoveringDefault(system,targetPairs):mode=="cse"?presets::cseAll():throw std::runtime_error("unknown mode");
   std::mt19937 gen(seed);TaskPool tasks=strategies.each(1,gen); if(preset>=tasks.size())throw std::runtime_error("bad preset");
   strategy=tasks[preset].strategy->name;solver=tasks[preset].strategy->create(matrix,seed);
  }
  solver->solve();Solution solution=solver->getSolution();if(get("--inline","0")=="1")solution=SolutionSubstitutionInliner().optimize(solution);if(!system.validateSolution(solution))throw std::runtime_error("exact upstream validation failed");
  std::ofstream output(args.at("--output"));JsonSolutionFormatter().format(output,solution);
  std::cout<<strategy<<" seed="<<seed<<" additions="<<solution.getAdditions()<<" upstream_validation=PASS\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
