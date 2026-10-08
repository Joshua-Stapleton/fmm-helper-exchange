# Four fixed-decomposition kernel minima

The selected 2×2×4/rank14, 2×3×3/rank15 and 2×3×4/rank20 decompositions have exact
alternative-basis signed-addition kernel minima **21**, **38** and **48**.
A different Perminov234 decomposition now attains and has minimum46; both
234 sources are included separately. Read `PROOF.md` for the precise model, finite completeness proof, and limits.

Reproduce the existing upper witnesses with Python 3's standard library:

```sh
python3 verify_upper.py
python3 verify_224.py
```

Reproduce the complete lower-bound computations with Python 3 and a C++17
compiler (no solver or third-party Python package required):

```sh
python3 verify_lower.py
```

The latter recompiles the included search programs, regenerates all coefficient
patterns and exact target relations from the source JSON, and checks every
helper class. Expect several minutes; it uses one native worker. Generated
inputs, logs, programs and results go in `replay/`. Set `CXX` to select a
compiler. No network access or installation is performed.

The source JSONs include basis conversions and ordinary-coordinate circuits,
but the proved minima concern the kernels only. The earlier 48-addition 234 witness costs another
8 additions in conversion, so its isolated ordinary multiplication does not
beat the retained 54-addition ordinary circuit merely because 48<54.

The new 46-addition 234 witness costs 12 conversion additions, hence 58 at one level. Its 46 kernel is optimal in the specified model; its boundary is not proved optimal.
