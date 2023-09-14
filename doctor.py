from __future__ import annotations

import argparse
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pkgutil import walk_packages
from typing import Dict

help = "Diagnose common issues, and optionally try to fix them."


def main(context: Dict[str, str], argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=help)
    parser.add_argument("--tag", type=str, action="append", help="")
    parser.add_argument("--fix", action="store_true", help="Run fixers.")
    args = parser.parse_args(argv)

    match_tags = set(args.tag if args.tag else ())

    repo = context["repo"]
    if repo not in {"sentry", "getsentry"}:
        print(f"repo {repo} not supported yet!")
        return 1

    checks = []
    for module_finder, name, ispkg in walk_packages((f'{context["reporoot"]}/devenv/checks',)):
        module = module_finder.find_spec(name).loader.load_module(name)  # type: ignore
        assert isinstance(module.name, str)
        assert isinstance(module.tags, set)
        if match_tags:
            if match_tags > module.tags:
                continue
        checks.append(module)

    # We run every check on a separate thread, aggregate the results,
    # attempt any fixes, then recheck and provide a final report.
    executor = ThreadPoolExecutor(max_workers=len(checks))
    print(f"Running checks: {', '.join(f'{c.name}' for c in checks)}")

    futures = {}
    results = {}
    for check in checks:
        futures[check] = executor.submit(check.check)
    for check, future in futures.items():
        results[check] = future.result()

    retry = []
    for check, result in results.items():
        ok, msg = result
        if ok:
            print(f"✅ check: {check.name}")
            continue
        print(f"❌ check: {check.name}{msg}")
        retry.append(check)

    if not retry:
        print("\nLooks good to me.")
        executor.shutdown()
        return 0
    else:
        if not args.fix:
            return 1

    print("\nAttempting to run fixes for the checks that failed...")
    futures = {}
    results = {}
    for check in retry:
        futures[check] = executor.submit(check.fix)
    for check, future in futures.items():
        results[check] = future.result()

    for check, result in results.items():
        ok, msg = result
        if ok:
            print(f"✅ fix: {check.name}")
            continue
        print(f"❌ fix: {check.name}{msg}")

    print("\nChecking again...")
    futures = {}
    results = {}
    for check in retry:
        futures[check] = executor.submit(check.check)
    for check, future in futures.items():
        results[check] = future.result()

    executor.shutdown()

    all_ok = True
    for check, result in results.items():
        ok, msg = result
        if ok:
            print(f"✅ check {check.name}")
            continue
        print(f"❌ check {check.name}{msg}")
        all_ok = False

    if all_ok:
        print("\nLooks good to me now!")
        return 0

    print("\nSorry I couldn't fix it... ask for help in #discuss-dev-infra.")
    return 1
