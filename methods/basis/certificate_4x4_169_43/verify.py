#!/usr/bin/env python3
"""Standard-library-only verifier for the c=32 square alternative-basis <4x4x4:48> core.

Checks: Brent identities of the ordinary 204 scheme (L,R,P); ALT_L*CoB_L = L,
ALT_R*CoB_R = R, CoB_P*ALT_P = P; every SLP computes exactly its matrix; literal operation
counts (binary +/-, non-unit scalings, explicit unary negations); canonical-vector counts;
one-level execution on random inputs and a two-level recursive 16x16 execution with
Kronecker-power changes of basis.  Run: python3 verify.py
"""
import json, random, re
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
N = 4


def read_sms(name):
    toks = (HERE / name).read_text().split()
    r, c = int(toks[0]), int(toks[1])
    M = [[F(0)] * c for _ in range(r)]
    for k in range(3, len(toks) - 2, 3):
        i, j, v = int(toks[k]), int(toks[k + 1]), toks[k + 2]
        if i == 0 and j == 0:
            break
        M[i - 1][j - 1] = F(v)
    return M


def matmul(A, B):
    return [[sum((A[i][t] * B[t][j] for t in range(len(B))), F(0)) for j in range(len(B[0]))] for i in range(len(A))]


def T(M):
    return [list(r) for r in zip(*M)]


def brent(L, R, P):
    for ci in range(N):
        for ck in range(N):
            o = N * ci + ck
            for a in range(N * N):
                for b in range(N * N):
                    s = sum((P[o][t] * L[t][a] * R[t][b] for t in range(len(L))), F(0))
                    ai, aj = divmod(a, N)
                    bj, bk = divmod(b, N)
                    if s != (1 if (ai == ci and aj == bj and bk == ck) else 0):
                        return False
    return True


TOK = re.compile(r"\s*([A-Za-z_]+[0-9]+|[0-9]+|[-+*/()])")


def parse_expr(s):
    toks, pos = [], 0
    while pos < len(s):
        m = TOK.match(s, pos)
        toks.append(m.group(1))
        pos = m.end()
    i = 0

    def peek():
        return toks[i] if i < len(toks) else None

    def expr():
        nonlocal i
        neg_lead = 0
        sign = 1
        if peek() in ("+", "-"):
            sign = -1 if toks[i] == "-" else 1
            i += 1
        lin, add, sc, ng = term()
        lin = {k: sign * v for k, v in lin.items()}
        all_neg = sign < 0
        while peek() in ("+", "-"):
            op = toks[i]
            all_neg = all_neg and op == "-"
            i += 1
            l2, a2, s2, n2 = term()
            for k, v in l2.items():
                lin[k] = lin.get(k, 0) + (v if op == "+" else -v)
            add, sc, ng = add + a2 + 1, sc + s2, ng + n2
        # strict: if every top-level term is negated, one explicit unary negation is needed
        if all_neg:
            ng += 1
        return lin, add, sc, ng

    def term():
        nonlocal i
        lin, add, sc, ng = factor()
        while peek() in ("*", "/"):
            op = toks[i]
            c = F(toks[i + 1])
            i += 2
            lin = {k: (v * c if op == "*" else v / c) for k, v in lin.items()}
            if abs(c) != 1:
                sc += 1
        return lin, add, sc, ng

    def factor():
        nonlocal i
        if peek() == "(":
            i += 1
            r = expr()
            i += 1
            return r
        v = toks[i]
        i += 1
        return {v: F(1)}, 0, 0, 0

    return expr()


def run_slp(name, n_in):
    """Return (matrix rows for outputs, counts)."""
    forms = {f"i{k}": {k: F(1)} for k in range(n_in)}
    outs, add, sc, ng = {}, 0, 0, 0
    for line in (HERE / name).read_text().splitlines():
        line = line.split("#")[0].strip()
        if ":=" not in line:
            continue
        lhs, rhs = line.rstrip(";").split(":=")
        lin, a, s, n = parse_expr(rhs.strip())
        add, sc, ng = add + a, sc + s, ng + n
        f = {}
        for v, c in lin.items():
            for k, x in forms[v].items():
                f[k] = f.get(k, 0) + c * x
        forms[lhs] = {k: x for k, x in f.items() if x != 0}
        if lhs.startswith("o"):
            outs[int(lhs[1:])] = forms[lhs]
    rows = [[outs[o].get(k, F(0)) for k in range(n_in)] for o in range(len(outs))]
    return rows, {"additions": add, "scalings": sc, "unary_negations": ng, "total": add + sc + ng}


def exec_slp(name, xs):
    env = {f"i{k}": x for k, x in enumerate(xs)}
    outs = {}
    for line in (HERE / name).read_text().splitlines():
        line = line.split("#")[0].strip()
        if ":=" not in line:
            continue
        lhs, rhs = line.rstrip(";").split(":=")
        lin = parse_expr(rhs.strip())[0]
        v = None
        for w, c in lin.items():
            term = env[w] * c if not isinstance(env[w], list) else [c * e for e in env[w]]
            v = term if v is None else (v + term if not isinstance(v, list) else [p + q for p, q in zip(v, term)])
        env[lhs] = v
        if lhs.startswith("o"):
            outs[int(lhs[1:])] = v
    return [outs[k] for k in range(len(outs))]


def canonical(v):
    return sum(1 for x in v if x != 0) == 1


def main():
    import hashlib, importlib.util
    manifest = json.loads((HERE / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected, name
    spec = importlib.util.spec_from_file_location("strict_verify", HERE / "strict_verify.py")
    strict = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(strict)
    out = {}
    L, R, P = read_sms("4x4x4_48_204_L.sms"), read_sms("4x4x4_48_204_R.sms"), read_sms("4x4x4_48_204_P.sms")
    assert brent(L, R, P), "Brent identities fail"
    AL, CL = read_sms("ALT_L.sms"), read_sms("CoB_L.sms")
    AR, CR = read_sms("ALT_R.sms"), read_sms("CoB_R.sms")
    AP, CP = read_sms("ALT_P.sms"), read_sms("CoB_P.sms")
    assert matmul(AL, CL) == L and matmul(AR, CR) == R and matmul(CP, AP) == P
    out["identities"] = "Brent(L,R,P); ALT_L*CoB_L=L; ALT_R*CoB_R=R; CoB_P*ALT_P=P"
    counts = {}
    for slp, M in (("ALT_L.slp", AL), ("ALT_R.slp", AR), ("ALT_P.slp", AP), ("CoB_L.slp", CL),
                   ("CoB_R.slp", CR), ("CoB_P.slp", CP), ("published_ALT_L_13canonical.slp", read_sms("published_ALT_L_13canonical.sms"))):
        rows, c = run_slp(slp, len(M[0]))
        assert rows == M, f"{slp} does not compute its matrix"
        actual, scount, scalars = strict.replay((HERE / slp).read_text(), len(M[0]), len(M))
        assert actual == M, slp
        assert scount["negations"] == 0, slp
        assert scount["additions_subtractions"] == c["additions"], slp
        assert scount["nonunit_scalings"] == c["scalings"], slp
        assert all(s == "1/2" for s in scalars), (slp, scalars)
        counts[slp] = c
    out["counts"] = counts
    out["kernel_total"] = sum(counts[s]["total"] for s in ("ALT_L.slp", "ALT_R.slp", "ALT_P.slp"))
    out["conversion_total"] = sum(counts[s]["total"] for s in ("CoB_L.slp", "CoB_R.slp", "CoB_P.slp"))
    out["canonical_rows"] = {"ALT_L": sum(map(canonical, AL)), "ALT_R": sum(map(canonical, AR)),
                             "ALT_P_columns": sum(map(canonical, T(AP))),
                             "published_ALT_L": sum(map(canonical, read_sms("published_ALT_L_13canonical.sms")))}
    mv = lambda M, v: [sum((M[i][j] * v[j] for j in range(len(v))), F(0)) for i in range(len(M))]
    rng = random.Random(2026)
    for _ in range(25):
        a = [F(rng.randint(-9, 9)) for _ in range(16)]
        b = [F(rng.randint(-9, 9)) for _ in range(16)]
        x = exec_slp("ALT_L.slp", mv(CL, a))
        y = exec_slp("ALT_R.slp", mv(CR, b))
        c = mv(CP, exec_slp("ALT_P.slp", [p * q for p, q in zip(x, y)]))
        A = [a[4 * i:4 * i + 4] for i in range(4)]
        B = [b[4 * i:4 * i + 4] for i in range(4)]
        assert c == [e for r in matmul(A, B) for e in r]
    out["one_level_random_checks"] = 25

    def phi(M16, X):
        Y = {}
        for I in range(16):
            t = mv(M16, [X[(I, i)] for i in range(16)])
            for i in range(16):
                Y[(I, i)] = t[i]
        Z = {}
        for i in range(16):
            t = mv(M16, [Y[(I, i)] for I in range(16)])
            for I in range(16):
                Z[(I, i)] = t[I]
        return Z
    split = lambda M: {(4 * bi + bj, 4 * ii + jj): M[4 * bi + ii][4 * bj + jj]
                       for bi in range(4) for bj in range(4) for ii in range(4) for jj in range(4)}
    A = [[F(rng.randint(-5, 5)) for _ in range(16)] for _ in range(16)]
    B = [[F(rng.randint(-5, 5)) for _ in range(16)] for _ in range(16)]
    Ua, Vb = phi(CL, split(A)), phi(CR, split(B))
    u = [[Ua[(I, i)] for i in range(16)] for I in range(16)]
    v = [[Vb[(I, i)] for i in range(16)] for I in range(16)]
    x, y = exec_slp("ALT_L.slp", u), exec_slp("ALT_R.slp", v)
    prods = []
    for p, q in zip(x, y):
        xi, yi = exec_slp("ALT_L.slp", p), exec_slp("ALT_R.slp", q)
        prods.append(exec_slp("ALT_P.slp", [s * t for s, t in zip(xi, yi)]))
    Z = exec_slp("ALT_P.slp", prods)
    Cd = phi(CP, {(I, i): Z[I][i] for I in range(16) for i in range(16)})
    C = matmul(A, B)
    assert all(Cd[(4 * bi + bj, 4 * ii + jj)] == C[4 * bi + ii][4 * bj + jj]
               for bi in range(4) for bj in range(4) for ii in range(4) for jj in range(4))
    out["two_level_16x16_execution"] = "OK"
    t, n0, cc = 48, 4, out["canonical_rows"]["ALT_L"] + out["canonical_rows"]["ALT_R"]
    out["lemma_4_1_c"] = cc
    out["footprint_coeff_(2t-c)/(n0^2-1)-1"] = str(F(2 * t - cc, n0 * n0 - 1) - 1)
    out["io_write_coeff_(3t-c)/(t-n0^2)"] = str(F(3 * t - cc, t - n0 * n0))
    assert out["kernel_total"] == 169
    assert out["conversion_total"] == 43
    assert out["canonical_rows"]["ALT_L"] == out["canonical_rows"]["ALT_R"] == 16
    assert out["canonical_rows"]["ALT_P_columns"] == 16
    def rank2(M):
        A = [[int(2*x) % 2 for x in row] for row in M]
        assert all((2*x).denominator == 1 for row in M for x in row)
        r = 0
        for j in range(len(A[0])):
            p = next((i for i in range(r,len(A)) if A[i][j]),None)
            if p is None: continue
            A[r],A[p] = A[p],A[r]
            for i in range(len(A)):
                if i != r and A[i][j]: A[i] = [x^y for x,y in zip(A[i],A[r])]
            r += 1
        return r
    out["rank_of_twice_input_basis_mod2"] = [rank2(CL), rank2(CR)]
    assert out["rank_of_twice_input_basis_mod2"] == [2,2]
    out["status"] = "PASS"
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
