# Pool search policies and exact final-replacement filtering

This study keeps three questions separate:

1. **Which complete circuits should start the search?** Six frozen pools compare
   the best start with cost-ordered and diverse portfolios of eight helper sets.
   A separate uphill-state control retains the best while permitting one or two
   extra helper forms. See [start and slack methods](STARTS_SLACK.md).
2. **Is explicit removal of three helpers worth trying?** Exact single/pair
   scans, bounded triple scans and historical separation witnesses are under
   [radius](radius/README.md). Its dependency-boundary filter removes irrelevant
   candidates only when one insertion remains, preserving successful final
   replacements. Four safety tests cover cycles and joint insertions.
3. **How many optional vector hints should native restarts omit?**
   [Native size controls](native_sizes/README.md) compare two, three, one through
   three, and one through eight omissions. Completed native circuits then enter
   a separately controlled pool experiment. The unchanged native solver is
   credited to Perminov; its source pin and license are retained.

The current literal certificates improve 5x7x7 V 204 to 203, 4x4x16 V 220 to 219,
5x5x12 V 230 to 229 and 6x7x8 V 280 to 279. The complete schemes use 694, 633, 721, 952
additions with unchanged ranks and ordinary bases. Search evidence here uses
signed wires; the separate [four-scheme certificates](../../../../certificates/pool_policies_20261017/README.md)
verify physical additions/subtractions and all original output signs.

## Verify without running searches

From the repository root:

```sh
python3 -I -B methods/linear/reconstruction/pool_policy_study/verify_all.py
```

Only Python's standard library is needed. This checks the frozen pools,
schedules, recorded exact circuits, native donor samples, historical witnesses
and safety properties. It does not rerun the timed searches or infer global
optimality from their failures. Full local native raw dumps are omitted; the
packaged report distinguishes their observed audit from replayable samples.

To additionally compile and run the native/Python frontier comparison:

```sh
python3 -I -B methods/linear/reconstruction/pool_policy_study/verify_all.py --with-cpp
```

This requires a C++17 compiler. Timed reruns require explicit runner arguments
and fresh output directories; the module READMEs document their budgets.
Frozen inputs and archived outcomes permit inspection without spending those
budgets. Search timing depends on the machine; exact arithmetic does not.

The [experiment report](../../../../docs/pool-policies-20261017.md) separates
matched comparisons from later controls, reports unsuccessful approaches and
attributes the 279 gain to old-bank search rather than the new native donors.
Earlier source artifacts and source-byte hashes remain identified separately
from compacted portable data.
