#!/usr/bin/env python3
"""Compile an adapter against an external, clean pinned LEO checkout."""
import argparse
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("reconstruction_common", Path(__file__).with_name("common.py"))
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--leo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="New executable path")
    parser.add_argument("--driver", choices=("repair", "population"), default="repair")
    parser.add_argument("--compiler")
    args = parser.parse_args()
    print(json.dumps(api.build(args.leo, args.out, args.driver, args.compiler), indent=2))
