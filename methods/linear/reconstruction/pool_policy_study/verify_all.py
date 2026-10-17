#!/usr/bin/env python3
"""Run bounded, read-only checks for all packaged pool-policy evidence."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--with-cpp', action='store_true')
    args = parser.parse_args()
    checks = ['verify_starts_slack.py', 'radius/verify.py',
              'radius/test_frontier.py', 'native_sizes/verify.py']
    environment = dict(os.environ)
    if args.with_cpp:
        environment['FMM_RADIUS_NATIVE_TESTS'] = '1'
    else:
        environment.pop('FMM_RADIUS_NATIVE_TESTS', None)
    results = []
    for relative in checks:
        start = time.monotonic()
        run = subprocess.run([sys.executable, '-I', '-B', str(HERE/relative)],
                             capture_output=True, text=True, timeout=120,
                             env=environment)
        record = dict(check=relative, status='PASS' if run.returncode == 0 else 'FAIL',
                      seconds=time.monotonic()-start,
                      output=(run.stdout+run.stderr).strip())
        results.append(record)
        if run.returncode:
            break
    passed = len(results) == len(checks) and all(r['status'] == 'PASS' for r in results)
    print(json.dumps(dict(status='PASS' if passed else 'FAIL',
                         native_safety_tests=args.with_cpp, timed_searches_run=False,
                         checks=results), indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
