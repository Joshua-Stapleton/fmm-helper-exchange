# Why a three-for-two exchange need not split into pair improvements

No: a joint three-helper replacement can be valid even when every possible
first two-helper/one-helper replacement is invalid. Each intermediate circuit
must still compute every output. Merely splitting the removed and inserted
sets does not establish that condition. Equal-cost or temporarily larger
circuits are a different neighborhood and are not ruled out here.

For four independent inputs `a,b,c,d`, compute these four outputs:

```
y1 = b + d
y2 = b - d
y3 = a - b - c + d
y4 = a - b + c
```

Here is a seven-addition circuit, counting subtraction as one addition:

```
y1 = b + d
y2 = b - d
p  = a + d
q  = y1 - c
r  = b + c
y3 = p - r
y4 = p - q
```

Replace the three helpers `p,q,r` jointly with the two helpers `u,v`:

```
y1 = b + d
y2 = b - d
u  = c - d
v  = a - y2
y3 = v - c
y4 = v + u
```

This circuit has six additions and exactly the same ordered outputs, with no
basis change or sign-repair cost. However, no deletion of one old helper is
valid, and no deletion of two old helpers can be repaired with one new helper.
The standalone verifier checks every old pair and every possible one-gate
integer replacement, including doubling. Thus the example is stronger than
restricting the replacement to the saved pool's `u` and `v`.

Run the standard-library-only verifier:

```
python3 -I -B verify_small.py
```

Why the enumeration is complete: remove an old pair, then compute the closure
of the inputs, mandatory output forms and retained old helper using all exact
binary addition/subtraction identities among those forms. Before the sole new
helper's defining gate, only forms in that closure can be ready. Therefore its
value must be a signed sum or difference of two ready forms. The verifier
enumerates every such form, including repeated operands, and checks exact
closure again. Sign aliases are canonicalized; zero cannot help repair an
unreachable nonzero output. The three pair tests examine 34, 34 and 36 genuinely
new canonical forms, respectively, and find no repair.

This is a local exchange counterexample, not a proof that six is the globally
optimal addition count. If intermediate circuits may have the same or a higher
cost, the joint replacement can be approached by a different sequence: for
example, insert `u,v` first and remove `p,q,r` afterwards. That sequence is not
two valid strictly improving two-for-one moves.

The earlier published study also retains larger examples with exactly this
distinction: the saved 6x6 W-transpose circuit has 156 signed-wire additions;
all 171 old-helper pairs fail, while replacing three helpers by two gives 155.
Those historical cases are retained in the earlier pool-policy study's radius
module. They are existing results, not new count discoveries.
