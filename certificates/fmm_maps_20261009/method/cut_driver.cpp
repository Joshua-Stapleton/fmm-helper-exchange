// Local driver for an unmodified LEO checkout. The input is an exact partial SLP.
#include <leo/entities/solution.h>
#include <leo/entities/substitution.h>
#include <leo/formatters/json_solution_formatter.h>
#include <leo/optimization/selection/greedy_alternative_selector.h>
#include <leo/optimization/solvers/vector_covering/vector_covering_solver.h>
#include <leo/optimization/solvers/vector_covering/scorers/distance_scorer.h>
#include <leo/utils/solution_validator.h>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
int main(int argc,char**argv){
 try{
  if(argc!=6&&argc!=7)throw std::runtime_error("input output seed savings slack [retention=1]");
  std::ifstream f(argv[1]);size_t rows,cols,gates;f>>rows>>cols>>gates;
  if(!f)throw std::runtime_error("bad header");
  std::vector<std::vector<int>> target(rows,std::vector<int>(cols));
  for(auto&r:target)for(auto&v:r)f>>v;
  leo::Solution partial;partial.dimension=cols;
  for(size_t k=0;k<gates;++k){size_t a,b;int sa,sb;f>>a>>sa>>b>>sb;
   if(a>=cols+k||b>=cols+k||(sa!=1&&sa!=-1)||(sb!=1&&sb!=-1))throw std::runtime_error("invalid partial gate");
   partial.substitutions.push_back({a,b,sa,sb});
  }
  if(!f)throw std::runtime_error("bad partial body");
  auto scorer=std::make_shared<leo::vector_covering::DistanceScorer>(1000.,1.,std::stod(argv[4]),10.,std::stoi(argv[5]));
  auto selector=std::make_shared<leo::GreedyAlternativeSelector>();
  leo::vector_covering::Parameters p={1,false,true,false};
  leo::vector_covering::VectorCoveringSolver solver(target,p,scorer,selector,std::stoul(argv[3]));
  double retention=argc==7?std::stod(argv[6]):1.0;
  if(!(retention>=0&&retention<=1))throw std::runtime_error("invalid retention probability");
  auto result=solver.solve(partial,retention);
  if(!result)throw std::runtime_error("bound prevented completion");
  auto solution=solver.getSolution();
  if(!leo::SolutionValidator().validate(target,solution))throw std::runtime_error("upstream exact verification failed");
  std::ofstream out(argv[2]);leo::JsonSolutionFormatter().format(out,solution);
  std::cout<<solution.getAdditions()<<"\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
