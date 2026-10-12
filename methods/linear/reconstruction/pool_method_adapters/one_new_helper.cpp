#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <queue>
#include <stdexcept>
#include <unordered_map>
#include <vector>

using V = std::vector<int>;
struct Rule {
  int out, a, sa, b, sb;
};
struct Candidate {
  V v;
  std::vector<Rule> incoming;
};
struct Hash {
  size_t operator()(const V &v) const {
    size_t h = 1469598103934665603ULL;
    for (int x : v) {
      h ^= size_t(x + 17);
      h *= 1099511628211ULL;
    }
    return h;
  }
};
using Clock = std::chrono::steady_clock;
double elapsed(Clock::time_point start) {
  return std::chrono::duration<double>(Clock::now() - start).count();
}
int canon(V &v) {
  int s = 0;
  for (int x : v)
    if (x) {
      s = x > 0 ? 1 : -1;
      break;
    }
  if (s < 0)
    for (int &x : v)
      x = -x;
  return s;
}

struct Graph {
  int N, n;
  std::vector<Rule> rules;
  std::vector<std::vector<int>> uses;
  Graph(int N, int n, const std::vector<Rule> &r)
      : N(N), n(n), rules(r), uses(N) {
    for (size_t i = 0; i < rules.size(); ++i) {
      uses[rules[i].a].push_back(i);
      if (rules[i].a != rules[i].b)
        uses[rules[i].b].push_back(i);
    }
  }
  bool closure(int removedA, int removedB, const std::vector<int> &targets,
               std::vector<Rule> &selected) const {
    std::vector<unsigned char> remaining(rules.size(), 0),
        enabled(rules.size(), 0), ready(N, 0);
    std::vector<int> producer(N, -1), order;
    order.reserve(N);
    for (size_t i = 0; i < rules.size(); ++i) {
      const auto &r = rules[i];
      if (r.out == removedA || r.out == removedB || r.a == removedA ||
          r.a == removedB || r.b == removedA || r.b == removedB)
        continue;
      enabled[i] = 1;
      remaining[i] = r.a == r.b ? 1 : 2;
    }
    std::vector<int> queue;
    queue.reserve(N);
    for (int i = 0; i < n; ++i) {
      ready[i] = 1;
      queue.push_back(i);
    }
    for (size_t p = 0; p < queue.size(); ++p) {
      int v = queue[p];
      for (int ri : uses[v]) {
        if (!enabled[ri])
          continue;
        const auto &r = rules[ri];
        if (ready[r.out])
          continue;
        if (--remaining[ri] == 0) {
          ready[r.out] = 1;
          producer[r.out] = ri;
          queue.push_back(r.out);
          order.push_back(r.out);
        }
      }
    }
    for (int target : targets)
      if (!ready[target])
        return false;
    std::vector<unsigned char> needed(N, 0);
    std::vector<int> stack = targets;
    while (!stack.empty()) {
      int v = stack.back();
      stack.pop_back();
      if (v < n || needed[v])
        continue;
      needed[v] = 1;
      int ri = producer[v];
      if (ri < 0)
        throw std::logic_error("Missing producer");
      stack.push_back(rules[ri].a);
      stack.push_back(rules[ri].b);
    }
    selected.clear();
    for (int v : order)
      if (needed[v])
        selected.push_back(rules[producer[v]]);
    return true;
  }
};
void witness(const std::vector<Rule> &selected, int candidate, int a, int b,
             double seconds) {
  std::cout << "{\"status\":\"FOUND\",\"candidate_index\":" << candidate
            << ",\"removed\":[";
  if (a >= 0)
    std::cout << a;
  if (b >= 0)
    std::cout << ',' << b;
  std::cout << "],\"gate_count\":" << selected.size()
            << ",\"seconds\":" << seconds << ",\"selected\":[";
  for (size_t i = 0; i < selected.size(); ++i) {
    if (i)
      std::cout << ',';
    auto r = selected[i];
    std::cout << '[' << r.out << ',' << r.a << ',' << r.sa << ',' << r.b << ','
              << r.sb << ']';
  }
  std::cout << "]}\n";
}
int main(int argc, char **argv) {
  try {
    if (argc != 3)
      throw std::invalid_argument("Usage: one_new_helper input seconds");
    std::ifstream in(argv[1]);
    int N, n, R, T, A, C;
    in >> N >> n >> R >> T >> A >> C;
    if (!in || N <= n || n <= 0 || A < 2 || T < 0 || R < 0 || C < 0)
      throw std::invalid_argument("Invalid header");
    const int baseline = T + A;
    std::vector<V> forms(N, V(n));
    for (auto &v : forms)
      for (int &x : v)
        in >> x;
    std::vector<Rule> base(R);
    for (auto &r : base)
      in >> r.out >> r.a >> r.sa >> r.b >> r.sb;
    std::vector<int> targets(T), aux(A);
    for (int &x : targets)
      in >> x;
    for (int &x : aux)
      in >> x;
    std::vector<Candidate> candidates(C);
    for (auto &c : candidates) {
      c.v.resize(n);
      for (int &x : c.v)
        in >> x;
      int count;
      in >> count;
      c.incoming.resize(count);
      for (auto &r : c.incoming) {
        r.out = N;
        in >> r.a >> r.sa >> r.b >> r.sb;
      }
    }
    if (!in)
      throw std::invalid_argument("Malformed payload");
    std::unordered_map<V, int, Hash> ids;
    for (int i = 0; i < N; ++i)
      ids.emplace(forms[i], i);
    std::vector<unsigned char> available(N + 1, 0);
    for (int i = 0; i < n; ++i)
      available[i] = 1;
    for (int t : targets)
      available[t] = 1;
    for (int a : aux)
      available[a] = 1;
    available[N] = 1;
    std::vector<Rule> potential;
    for (auto &r : base)
      if (available[r.out] && available[r.a] && available[r.b])
        potential.push_back(r);
    Graph old(N + 1, n, potential);
    std::vector<Rule> selected;
    auto start = Clock::now();
    double budget = std::stod(argv[2]);
    if (!std::isfinite(budget) || budget <= 0 || budget > 60)
      throw std::invalid_argument("Invalid time limit");
    if (!old.closure(-1, -1, targets, selected))
      throw std::logic_error("Baseline cannot be built");
    if (selected.size() < size_t(baseline)) {
      witness(selected, -1, -1, -1, elapsed(start));
      return 0;
    }
    size_t deletionTests = 0;
    for (int a : aux) {
      ++deletionTests;
      if (old.closure(a, -1, targets, selected)) {
        witness(selected, -1, a, -1, elapsed(start));
        return 0;
      }
    }
    std::vector<std::pair<int, int>> pairs;
    for (int i = 0; i < A; ++i)
      for (int j = i + 1; j < A; ++j) {
        pairs.emplace_back(aux[i], aux[j]);
        ++deletionTests;
        if (old.closure(aux[i], aux[j], targets, selected)) {
          witness(selected, -1, aux[i], aux[j], elapsed(start));
          return 0;
        }
      }
    size_t processed = 0, eligible = 0, logicalPairs = 0, closures = 0,
           skippedIncoming = 0;
    V value(n);
    for (int ci = 0; ci < C; ++ci) {
      if (elapsed(start) > budget)
        break;
      std::vector<Rule> extra;
      for (auto r : candidates[ci].incoming)
        if (available[r.a] && available[r.b])
          extra.push_back(r);
      if (extra.empty()) {
        ++processed;
        logicalPairs += pairs.size();
        ++skippedIncoming;
        continue;
      }
      ++eligible;
      for (int j = 0; j < N; ++j)
        if (available[j])
          for (int sign : {-1, 1}) {
            for (int k = 0; k < n; ++k)
              value[k] = candidates[ci].v[k] + sign * forms[j][k];
            int s = canon(value);
            if (!s)
              continue;
            auto it = ids.find(value);
            if (it != ids.end() && it->second >= n && it->second != j &&
                available[it->second])
              extra.push_back({it->second, N, s, j, s * sign});
          }
      std::vector<Rule> all = potential;
      all.insert(all.end(), extra.begin(), extra.end());
      Graph graph(N + 1, n, all);
      bool finished = true;
      for (auto pair : pairs) {
        if (elapsed(start) > budget) {
          finished = false;
          break;
        }
        ++logicalPairs;
        bool canBuildNew = false;
        for (auto &r : extra)
          if (r.out == N && r.a != pair.first && r.a != pair.second &&
              r.b != pair.first && r.b != pair.second) {
            canBuildNew = true;
            break;
          }
        if (!canBuildNew)
          continue;
        ++closures;
        if (graph.closure(pair.first, pair.second, targets, selected)) {
          witness(selected, ci, pair.first, pair.second, elapsed(start));
          return 0;
        }
      }
      if (finished)
        ++processed;
      else
        break;
    }
    std::cout << "{\"status\":\""
              << (processed == size_t(C) ? "EXHAUSTED_RESTRICTED_2_FOR_1"
                                         : "TIME_LIMIT")
              << "\",\"seconds\":" << elapsed(start)
              << ",\"candidates_total\":" << C
              << ",\"candidates_processed\":" << processed
              << ",\"eligible_candidates\":" << eligible
              << ",\"skipped_no_incoming\":" << skippedIncoming
              << ",\"logical_pairs_tested\":" << logicalPairs
              << ",\"closures_run\":" << closures
              << ",\"deletion_pretests\":" << deletionTests
              << ",\"old_rules\":" << R
              << ",\"old_allowed_rules\":" << potential.size() << "}\n";
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 2;
  }
}
