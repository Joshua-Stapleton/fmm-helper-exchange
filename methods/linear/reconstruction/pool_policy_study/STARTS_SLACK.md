# Starting-point and plateau-slack studies

The frozen six-case study compares a single best start against two eight-start portfolios using six nominal search seconds per arm and two seeds. The cheapest circuit starts each portfolio. Cost ordering then takes seven cheapest distinct helper sets; diversity ordering greedily maximizes newly covered helpers divided by (1+cost-best), restricted to starts within eight additions of best. Generic donor embedding and both portfolio selectors are in starts/run_starts.py.

These searches use canonical exact vectors and signed wires. Original parent choices are not preserved: closure reconnects through every exact production in the common pool. Starts with the same helper set are merged. A more expensive starting circuit inherits a larger permitted plateau population size, so this compares operating policies rather than isolating diversity alone. The separate slack fork permits best+1 or best+2 helper states from the original best start; all16 recorded controls retained their incumbents.

## Verify the frozen evidence

From the public repository root:

```sh
python3 -I -B methods/linear/reconstruction/pool_policy_study/verify_starts_slack.py
```

Only Python's standard library is used. It validates exact pool relations, all102 frozen input schedules, their initial feasible closures, and every recorded emitted candidate against its ordered signed target. Repeated target_matrix and pool_selection fields were removed from candidate exports; exact gates/output signs and source-byte hashes remain. Dense targets live once in each pool. Original wall times, preparation times and nominal budgets are retained; full historical donor-generation costs are not included.

## Optional timed reruns

Each command requires a fresh output directory and a C++17 compiler. They use the frozen schedules by default and need no historical donor bank:

```sh
python3 -I -B methods/linear/reconstruction/pool_policy_study/starts/run_starts.py --case hl_5x7x7_V --seconds 6 --out /tmp/fmm-starts-replay
python3 -I -B methods/linear/reconstruction/pool_policy_study/slack/run_slack.py --case hl_5x7x7_V --seconds 6 --out /tmp/fmm-slack-replay
```

The first command gives each of three policies six seconds per seed, divided equally among its starts; it runs two seeds by default. Select --seed once for one seed. The slack command runs slack1 and2 and two seeds by default. Initial closure and process/audit overhead can exceed nominal search time. Search timing and outcomes depend on the machine and scheduling; certificates do not require rerunning timed searches. An external staged copy can locate the repository with --repo /path/to/fmm-helper-exchange.

To construct portfolios from a new supplied donor bank, use starts/run_starts.py with --pool pool.json --donors donors.json --incumbent best.json --out /tmp/fmm-custom-starts. This preserves the generic method; frozen schedules avoid needing all original donor circuits.
