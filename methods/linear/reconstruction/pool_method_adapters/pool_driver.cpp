#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <leo/leo.h>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>

using namespace leo;
using Clock = std::chrono::steady_clock;
constexpr int64_t SAFE_COEFFICIENT = std::numeric_limits<int>::max() / 2;
double seconds(Clock::time_point start) {
  return std::chrono::duration<double>(Clock::now() - start).count();
}
void require(bool condition, const std::string &message) {
  if (!condition)
    throw std::invalid_argument(message);
}

struct Input {
  size_t dimension, best;
  std::vector<std::vector<int>> targets;
  std::vector<Solution> donors;
};
Input readInput(const std::string &path) {
  std::ifstream in(path);
  require(bool(in), "Cannot read input file");
  Input x;
  size_t outputs, donors;
  in >> x.dimension >> outputs >> x.best >> donors;
  require(bool(in) && x.dimension > 0 && outputs > 0 && donors > 0,
          "Invalid input header");
  x.targets.assign(outputs, std::vector<int>(x.dimension));
  for (auto &row : x.targets)
    for (auto &value : row) {
      in >> value;
      require(bool(in) && std::abs(int64_t(value)) <= SAFE_COEFFICIENT,
              "Target lacks safe int32 arithmetic headroom");
    }
  for (size_t k = 0; k < donors; ++k) {
    Solution s;
    size_t gates, expressions;
    in >> s.dimension >> gates >> expressions;
    require(s.dimension == x.dimension, "Donor dimension mismatch");
    for (size_t j = 0; j < gates; ++j) {
      Substitution sub;
      in >> sub.i >> sub.j >> sub.ai >> sub.aj;
      require(bool(in) && sub.i < x.dimension + j && sub.j < x.dimension + j &&
                  (sub.ai == 1 || sub.ai == -1) &&
                  (sub.aj == 1 || sub.aj == -1),
              "Invalid raw parent or nonunit scalar");
      s.substitutions.push_back(sub);
    }
    for (size_t j = 0; j < expressions; ++j) {
      size_t count;
      in >> count;
      std::vector<Term> row;
      for (size_t z = 0; z < count; ++z) {
        Term t;
        in >> t.index >> t.value;
        require(bool(in) && t.index < x.dimension + gates &&
                    (t.value == 1 || t.value == -1),
                "Invalid raw expression term or nonunit scalar");
        row.push_back(t);
      }
      s.expressions.push_back(row);
    }
    require(bool(in), "Malformed donor");
    x.donors.push_back(std::move(s));
  }
  for (const auto &s : x.donors) {
    std::vector<std::vector<int64_t>> values(
        x.dimension, std::vector<int64_t>(x.dimension, 0));
    for (size_t i = 0; i < x.dimension; ++i)
      values[i][i] = 1;
    for (const auto &sub : s.substitutions) {
      std::vector<int64_t> v(x.dimension);
      bool nonzero = false;
      for (size_t j = 0; j < x.dimension; ++j) {
        v[j] = sub.ai * values[sub.i][j] + sub.aj * values[sub.j][j];
        require(std::abs(v[j]) <= SAFE_COEFFICIENT,
                "Intermediate can overflow int32 library arithmetic");
        nonzero = nonzero || v[j] != 0;
      }
      require(nonzero,
              "Zero intermediate is unsupported by upstream HelperPool");
      values.push_back(v);
    }
    for (const auto &row : s.expressions) {
      std::vector<int64_t> v(x.dimension, 0);
      for (const auto &term : row)
        for (size_t j = 0; j < x.dimension; ++j) {
          v[j] += term.value * values[term.index][j];
          require(std::abs(v[j]) <= std::numeric_limits<int>::max(),
                  "Terminal int32 accumulation overflow");
        }
    }
    require(x.best <= s.getAdditions(),
            "Best reference can underflow upstream unsigned cost subtraction");
  }
  std::string extra;
  require(!(in >> extra), "Trailing input data");
  return x;
}
void writeSolution(std::ostream &out, const Solution &s) {
  out << "{\"dimension\":" << s.dimension
      << ",\"additions\":" << s.getAdditions() << ",\"substitutions\":[";
  for (size_t i = 0; i < s.substitutions.size(); ++i) {
    if (i)
      out << ',';
    const auto &v = s.substitutions[i];
    out << "{\"i\":" << v.i << ",\"j\":" << v.j << ",\"ai\":" << v.ai
        << ",\"aj\":" << v.aj << '}';
  }
  out << "],\"expressions\":[";
  for (size_t i = 0; i < s.expressions.size(); ++i) {
    if (i)
      out << ',';
    out << '[';
    for (size_t j = 0; j < s.expressions[i].size(); ++j) {
      if (j)
        out << ',';
      auto t = s.expressions[i][j];
      out << "{\"index\":" << t.index << ",\"value\":" << t.value << '}';
    }
    out << ']';
  }
  out << "]}";
}
// Verbatim policy from master 606edc0 Reducer::getRandomSubstitutions.
std::vector<Substitution> bernoulli(const std::vector<Solution> &solutions,
                                    const std::vector<double> &weights,
                                    std::mt19937 &generator, double probability,
                                    size_t &donor) {
  std::discrete_distribution<size_t> distribution(weights.begin(),
                                                  weights.end());
  donor = distribution(generator);
  const Solution &solution = solutions[donor];
  std::uniform_real_distribution<double> uniform(0.0, 1.0);
  std::vector<bool> used(solution.substitutions.size(), true);
  std::vector<size_t> indices(solution.substitutions.size());
  std::vector<Substitution> substitutions;
  size_t dimension = solution.dimension, offset = 0;
  for (size_t index = 0; index < solution.substitutions.size(); ++index) {
    Substitution s = solution.substitutions[index];
    if (!used[index])
      continue;
    if (uniform(generator) > probability ||
        (s.i >= dimension && !used[s.i - dimension]) ||
        (s.j >= dimension && !used[s.j - dimension])) {
      used[index] = false;
      continue;
    }
    indices[index] = offset++;
    if (s.i >= dimension)
      s.i = dimension + indices[s.i - dimension];
    if (s.j >= dimension)
      s.j = dimension + indices[s.j - dimension];
    substitutions.push_back(s);
  }
  return substitutions;
}
std::vector<Substitution> readPrefix(const std::string &path, size_t expected) {
  std::ifstream in(path);
  size_t n, count;
  in >> n >> count;
  require(bool(in) && n == expected, "Invalid external prefix");
  std::vector<Substitution> result;
  std::vector<std::vector<int64_t>> values(n, std::vector<int64_t>(n, 0));
  for (size_t i = 0; i < n; ++i)
    values[i][i] = 1;
  for (size_t i = 0; i < count; ++i) {
    Substitution s;
    in >> s.i >> s.j >> s.ai >> s.aj;
    require(bool(in) && s.i < n + i && s.j < n + i &&
                (s.ai == 1 || s.ai == -1) && (s.aj == 1 || s.aj == -1),
            "Invalid external prefix parent or nonunit scalar");
    std::vector<int64_t> vector(n);
    for (size_t j = 0; j < n; ++j) {
      vector[j] = s.ai * values[s.i][j] + s.aj * values[s.j][j];
      require(std::abs(vector[j]) <= SAFE_COEFFICIENT,
              "External prefix could overflow int32 library arithmetic");
    }
    values.push_back(vector);
    result.push_back(s);
  }
  std::string extra;
  require(!(in >> extra), "Trailing prefix data");
  return result;
}
int main(int argc, char **argv) {
  try {
    std::map<std::string, std::string> args;
    bool sampleOnly = false;
    for (int i = 1; i < argc; ++i) {
      std::string k = argv[i];
      if (k == "--sample-only") {
        sampleOnly = true;
        continue;
      }
      require(i + 1 < argc, "Missing argument value");
      args[k] = argv[++i];
    }
    auto get = [&](const std::string &k, const std::string &d) {
      auto it = args.find(k);
      return it == args.end() ? d : it->second;
    };
    require(args.count("--input"), "--input is required");
    auto input = readInput(args.at("--input"));
    auto mode = get("--mode", "weighted");
    require(mode == "weighted" || mode == "uniform" || mode == "bernoulli",
            "Invalid mode");
    uint64_t seed = std::stoull(get("--seed", "1"));
    size_t draws = std::stoull(get("--draws", "1"));
    require(seed <= std::numeric_limits<uint32_t>::max() && draws > 0 &&
                draws <=
                    uint64_t(std::numeric_limits<uint32_t>::max()) - seed + 1,
            "Invalid seed/draw range");
    double T = std::stod(get("--temperature", "1")),
           eps = std::stod(get("--epsilon", "0.01")),
           retain = std::stod(get("--retention", "0.5")),
           time = std::stod(get("--seconds", "5"));
    double minRatio = std::stod(get("--min-start-ratio", "0.1")),
           maxRatio = std::stod(get("--max-start-ratio", "0.5"));
    require(std::isfinite(T) && T > 0 && std::isfinite(eps) && eps >= 0 &&
                eps <= 1 && std::isfinite(retain) && retain >= 0 &&
                retain <= 1 && std::isfinite(time) && time > 0,
            "Invalid sampler/solver parameters");
    require(std::isfinite(minRatio) && std::isfinite(maxRatio) &&
                minRatio >= 0 && minRatio <= maxRatio && maxRatio <= 1,
            "Invalid start ratios");
    long long fixedLimit = std::stoll(get("--gate-limit", "-1"));
    require(fixedLimit >= -1, "Invalid gate limit");
    size_t strategyIndex = std::stoull(get("--strategy-index", "0"));
    std::string preset = get("--preset", "distance");
    require(preset == "distance" || preset == "default" || preset == "all",
            "Invalid preset");
    ExpressionsSystem system(input.targets);
    for (const auto &d : input.donors)
      require(system.validateSolution(d),
              "Input donor does not compute target map");
    auto preparation = Clock::now();
    Reducer reducer(1);
    std::vector<double> weights;
    if (mode == "uniform")
      weights.assign(input.donors.size(), 1.0 / input.donors.size());
    else {
      size_t reference = input.best;
      if (mode == "bernoulli") {
        reference = input.donors.front().getAdditions();
        for (const auto &d : input.donors)
          reference = std::min(reference, d.getAdditions());
      }
      weights = reducer.getWeights(input.donors, reference, T, eps);
    }
    for (double w : weights)
      require(std::isfinite(w) && w >= 0,
              "Upstream donor weights are not finite");
    HelperPool pool(input.dimension);
    for (size_t i = 0; i < input.donors.size(); ++i)
      pool.addSolution(input.donors[i], weights[i]);
    double preparationSeconds = seconds(preparation);
    vector_covering::Parameters parameters;
    parameters.maxAbsValue = system.getMaxAbsValue();
    parameters.naiveFallback = false;
    parameters.removeUnused = true;
    parameters.addTargetPairs = false;
    parameters.maxTimeInSeconds = time;
    auto strategies =
        preset == "distance"  ? presets::vectorCoveringDistance(parameters)
        : preset == "default" ? presets::vectorCoveringDefault(parameters)
                              : presets::vectorCoveringAll(parameters);
    std::mt19937 strategyGenerator(1);
    auto tasks = strategies.each(1, strategyGenerator);
    require(strategyIndex < tasks.size(), "Strategy index out of range");
    std::cout << std::setprecision(17) << "{\"mode\":\"" << mode
              << "\",\"donors\":" << input.donors.size()
              << ",\"helpers\":" << pool.size()
              << ",\"best_reference\":" << input.best
              << ",\"temperature\":" << T << ",\"epsilon\":" << eps
              << ",\"preparation_seconds\":" << preparationSeconds
              << ",\"weights\":[";
    for (size_t i = 0; i < weights.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << weights[i];
    }
    std::cout << "],\"draws\":[";
    for (size_t draw = 0; draw < draws; ++draw) {
      if (draw)
        std::cout << ',';
      uint32_t drawSeed = seed + draw;
      std::mt19937 generator(drawSeed);
      auto sampling = Clock::now();
      size_t limit =
                 mode == "bernoulli"
                     ? 0
                     : (fixedLimit >= 0
                            ? size_t(fixedLimit)
                            : std::uniform_int_distribution<size_t>(
                                  size_t(input.best * minRatio),
                                  size_t(input.best * maxRatio))(generator)),
             donor = 0;
      std::vector<Substitution> prefix;
      if (args.count("--prefix-file"))
        prefix = readPrefix(args.at("--prefix-file"), input.dimension);
      else if (mode == "bernoulli")
        prefix = bernoulli(input.donors, weights, generator, retain, donor);
      else
        prefix = pool.getRandomSubstitutions(generator, limit);
      double samplingSeconds = seconds(sampling);
      Solution prefixSolution;
      prefixSolution.dimension = input.dimension;
      prefixSolution.substitutions = prefix;
      std::cout << "{\"seed\":" << drawSeed << ",\"gate_limit\":" << limit
                << ",\"prefix_gates\":" << prefix.size()
                << ",\"sampling_seconds\":" << samplingSeconds
                << ",\"selected_donor\":";
      if (mode == "bernoulli")
        std::cout << donor;
      else
        std::cout << "null";
      std::cout << ",\"prefix\":";
      writeSolution(std::cout, prefixSolution);
      if (sampleOnly)
        std::cout << ",\"status\":\"sample_only\",\"solution\":null";
      else {
        auto solver =
            tasks[strategyIndex].strategy->create(input.targets, drawSeed);
        if (args.count("--bound"))
          solver->setBound(std::stoull(args.at("--bound")));
        auto solving = Clock::now();
        auto result = solver->solve(prefix);
        double solvingSeconds = seconds(solving);
        std::cout << ",\"strategy\":\"" << tasks[strategyIndex].strategy->name
                  << "\",\"solver_seconds\":" << solvingSeconds
                  << ",\"status\":\""
                  << (result ? "complete" : "timeout_or_bound")
                  << "\",\"solution\":";
        if (result) {
          auto solution = solver->getSolution();
          for (const auto &s : solution.substitutions)
            require((s.ai == 1 || s.ai == -1) && (s.aj == 1 || s.aj == -1),
                    "Completion contains an uncharged nonunit scalar");
          for (const auto &row : solution.expressions)
            for (const auto &term : row)
              require(term.value == 1 || term.value == -1,
                      "Completion contains an uncharged terminal scalar");
          require(system.validateSolution(solution),
                  "Completed solution fails upstream exact replay");
          writeSolution(std::cout, solution);
        } else
          std::cout << "null";
      }
      std::cout << '}';
    }
    std::cout << "]}\n";
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 2;
  }
}
