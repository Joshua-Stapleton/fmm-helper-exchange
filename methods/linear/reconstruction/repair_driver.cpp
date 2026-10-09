// Adapter for an unmodified externally installed LEO library.
#include <leo/entities/solution.h>
#include <leo/formatters/json_solution_formatter.h>
#include <leo/optimization/selection/greedy_alternative_selector.h>
#include <leo/optimization/solvers/vector_covering/vector_covering_solver.h>
#include <leo/optimization/solvers/vector_covering/scorers/distance_scorer.h>
#include <leo/utils/solution_validator.h>
#include <algorithm>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
int main(int argc,char**argv){
 try{
  if(argc!=8)throw std::runtime_error("input output seed savings slack retention max_abs");
  std::ifstream file(argv[1]);size_t rows,cols,count;file>>rows>>cols>>count;
  if(!file||!rows||!cols)throw std::runtime_error("invalid partial input header");
  std::vector<std::vector<int>> target(rows,std::vector<int>(cols));
  for(auto&row:target)for(auto&value:row)file>>value;
  leo::Solution partial;partial.dimension=cols;
  for(size_t k=0;k<count;k++){
   size_t a,b;int sa,sb;file>>a>>sa>>b>>sb;
   if(!file||a>=cols+k||b>=cols+k||(sa!=1&&sa!=-1)||(sb!=1&&sb!=-1))
    throw std::runtime_error("invalid partial gate");
   partial.substitutions.push_back({a,b,sa,sb});
  }
  if(!file)throw std::runtime_error("invalid partial input body");
  double probability=std::stod(argv[6]);
  if(!(probability>=0&&probability<=1))throw std::runtime_error("invalid retention probability");
  auto scorer=std::make_shared<leo::vector_covering::DistanceScorer>(1000.,1.,std::stod(argv[4]),10.,std::stoi(argv[5]));
  auto selector=std::make_shared<leo::GreedyAlternativeSelector>();
  leo::vector_covering::Parameters parameters={std::stoi(argv[7]),false,true,false};
  leo::vector_covering::VectorCoveringSolver solver(target,parameters,scorer,selector,std::stoul(argv[3]));
  if(!solver.solve(partial,probability))throw std::runtime_error("completion reached its bound");
  auto solution=solver.getSolution();
  if(!leo::SolutionValidator().validate(target,solution))throw std::runtime_error("upstream exact verification failed");
  std::ofstream output(argv[2]);if(!output)throw std::runtime_error("cannot open output");
  leo::JsonSolutionFormatter().format(output,solution);
  std::cout<<solution.getAdditions()<<std::endl;
 }catch(const std::exception&error){std::cerr<<error.what()<<std::endl;return 1;}
}
