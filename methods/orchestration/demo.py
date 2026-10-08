"""Small restart/deduplication demonstration; no persistent user files."""
import json
import tempfile
from pathlib import Path
from store import Store


def main():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)/'registry.sqlite'
        store = Store(path)
        matrix = store.matrix([[1, 1, 0], [1, 1, 1], [0, 1, -1]])
        reducers = [store.reducer(name, {}) for name in ('direct', 'signed_cse')]
        for r in reducers:
            store.request(matrix, r, 0, 'initial')
        first = store.run(2, 30)
        store.close()
        store = Store(path)
        for r in reducers:
            store.request(matrix, r, 0, 'repeated')
        again = store.run(2, 30)
        costs = [dict(row) for row in store.db.execute('SELECT additions,scalars FROM programs')]
        store.close()
        if first['finished_jobs'] != 2 or again['finished_jobs'] != 0:
            raise ValueError('cache/restart replay failed')
        print(json.dumps({'status': 'PASS', 'first_jobs': 2, 'repeated_jobs': 0,
                          'program_costs': costs, 'cost_model': 'free signs/copies'}, indent=2))


if __name__ == '__main__':
    main()
