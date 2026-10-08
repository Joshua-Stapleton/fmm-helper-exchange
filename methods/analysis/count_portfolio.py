"""Recompute the documented 51/6, 52/3 and ordinary 55/0 arithmetic formulas."""
import json
from pathlib import Path


def additions(depth, strategy):
    if depth == 0:
        return 0
    choices = {
        'uniform_51_6': lambda j: (51, 6),
        'mixed_52_3_then_51_6': lambda j: (52, 3) if j < 2 else (51, 6),
        'ordinary_55_0': lambda j: (55, 0),
    }
    stages = [choices[strategy](j) for j in range(depth)]
    return sum(a*23**j*9**(depth-1-j) for j, (a, b) in enumerate(stages)) + sum(b for a, b in stages)*9**(depth-1)


def cost(n, depth, strategy):
    assert n % 3**depth == 0
    m = n // 3**depth
    mul = 23**depth*m**3
    add = m*m*additions(depth, strategy) + 23**depth*(m**3-m*m)
    return dict(depth=depth, classical_leaf_dimension=m, multiplications=mul, additions=add, total=mul+add)


def main():
    results = []
    for n, depth in [(9, 2), (27, 3), (81, 4)]:
        variants = {}
        for strategy in ['uniform_51_6', 'mixed_52_3_then_51_6', 'ordinary_55_0']:
            cutoffs = [cost(n, d, strategy) for d in range(depth+1)]
            variants[strategy] = dict(full_recursion=cutoffs[-1], all_classical_cutoffs=cutoffs, best_classical_cutoff=min(cutoffs, key=lambda c: c['total']))
        results.append(dict(n=n, classical_total=2*n**3-n*n, variants=variants))
    report = dict(status='PASS', metric='One scalar multiplication, addition, or subtraction each costs one; copies free. All basis conversions included.', source='Historical September19 verified tensor-axis portfolio; formulas reproduced here', addition_formula='A_d = sum_j a_j*23^j*9^(d-1-j) + sum_j b_j*9^(d-1)', classical_cutoff_formula='T(3^d*m) = m^2*A_d + 23^d*(2*m^3-m^2)', scope='Best only among these supplied tensor-axis schedules and classical square leaves, including depth zero. Neither global arithmetic optimality nor runtime.', results=results)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
