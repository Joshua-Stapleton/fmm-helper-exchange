"""Share the repository's exact pool validator without changing sys.path."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("helper_exchange_core", ROOT / "run.py")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def closure(data, prods, helpers, grant=()):
    """First-production exact closure; mandatory targets must still be produced."""
    n = data["inputs"]
    targets = {o for o, _ in data["outputs"]}
    active = set(range(n)) | targets | set(helpers) | set(grant)
    ready = set(range(n)) | set(grant)
    chosen = {}
    while True:
        progress = False
        for out in sorted(prods):
            if out not in active or out in ready:
                continue
            for a, sa, b, sb in prods[out]:
                if a in ready and b in ready:
                    ready.add(out)
                    chosen[out] = (a, sa, b, sb)
                    progress = True
                    break
        if not progress:
            return ready, chosen


def frontier(ready, prods):
    return {o for o, rows in prods.items() if o not in ready
            and any(a in ready and b in ready for a, _, b, _ in rows)}
