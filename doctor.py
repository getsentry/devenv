from __future__ import annotations

import argparse
from collections.abc import Callable
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pkgutil import walk_packages
from types import ModuleType
from typing import Dict
from typing import List
from typing import Set
from typing import Tuple

from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

help = "Diagnose common issues, and optionally try to fix them."


class Check:
    name: str
    tags: Set[str]
    check: Callable[[], Tuple[bool, str]]
    fix: Callable[[], Tuple[bool, str]]

    def __init__(
        self,
        module: ModuleType,
    ):
        # Check that the module has the required attributes.
        assert hasattr(module, "name")
        assert isinstance(module.name, str)
        self.name = module.name

        assert hasattr(module, "tags")
        assert isinstance(module.tags, set)
        self.tags = module.tags

        # Check that the module has the check and fix functions.
        assert hasattr(module, "check")
        assert callable(module.check)
        self.check = checker(module.check)

        assert hasattr(module, "fix")
        assert callable(module.fix)
        self.fix = fixer(module.fix)


def load_checks(context: Dict[str, str], match_tags: Set[str]) -> List[Check]:
    checks = []
    for module_finder, name, ispkg in walk_packages((f'{context["reporoot"]}/devenv/checks',)):
        module = module_finder.find_spec(name).loader.load_module(name)  # type: ignore
        try:
            check = Check(module)
        except AssertionError:
            print(f"⚠️ Skipping {name} because it doesn't have the required attributes.")
            continue
        if match_tags and not check.tags.issuperset(match_tags):
            continue
        checks.append(check)
    return checks


def run_checks(
    checks: List[Check], executor: ThreadPoolExecutor, skip: List[Check] = []
) -> Dict[Check, Tuple[bool, str]]:
    futures = {}
    results = {}
    for check in checks:
        if check in skip:
            print(f"\t⏭️  Skipped {check.name}".expandtabs(4))
            continue
        futures[check] = executor.submit(check.check)
    for check, future in futures.items():
        results[check] = future.result()
    return results


def filter_failing_checks(results: Dict[Check, Tuple[bool, str]]) -> List[Check]:
    failing_checks = []
    for check, result in results.items():
        ok, msg = result
        if ok:
            print(f"\t✅ check: {check.name}".expandtabs(4))
            continue
        print(f"\t❌ check: {check.name}{msg}".expandtabs(4))
        failing_checks.append(check)
    return failing_checks


def prompt_for_fix(check: Check) -> bool:
    return input(
        f"\t\tDo you want to attempt to fix {check.name}? (Y/n): ".expandtabs(4)
    ).lower() in {
        "y",
        "yes",
        "",
    }


def attempt_fix(check: Check, executor: ThreadPoolExecutor) -> Tuple[bool, str]:
    future = executor.submit(check.fix)
    return future.result()


def main(context: Dict[str, str], argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=help)
    parser.add_argument(
        "--tag", type=str, action="append", help="Used to match a subset of checks."
    )
    parser.add_argument("--check-only", action="store_true", help="Do not run fixers.")
    args = parser.parse_args(argv)

    match_tags = set(args.tag if args.tag else ())

    repo = context["repo"]
    if repo not in {"sentry", "getsentry", "devenv"}:
        print(f"repo {repo} not supported yet!")
        return 1

    checks = load_checks(context, match_tags)

    if not checks:
        print(f"No checks found for tags: {args.tag}")
        return 1

    # We run every check on a separate thread, aggregate the results,
    # attempt any fixes, then recheck and provide a final report.
    executor = ThreadPoolExecutor(max_workers=len(checks))
    print(f"Running checks: {', '.join(f'{c.name}' for c in checks)}")

    results = run_checks(checks, executor)

    failing_checks = filter_failing_checks(results)

    if not failing_checks:
        print("\nLooks good to me.")
        executor.shutdown()
        return 0
    else:
        if args.check_only:
            return 1

    print("\nThe following problems have been identified:")
    skip = []
    for check in failing_checks:
        print(f"\t❌ {check.name}".expandtabs(4))
        # Prompt for fixes one by one, so the user can decide to skip a fix.
        if prompt_for_fix(check):
            ok, msg = attempt_fix(check, executor)
            if ok:
                print(f"\t\t✅ fix: {check.name}".expandtabs(4))
            else:
                print(f"\t\t❌ fix: {check.name}{msg}".expandtabs(4))
        else:
            print(f"\t\t⏭️  Skipping {check.name}".expandtabs(4))
            skip.append(check)

    print("\nChecking that fixes worked as expected...")
    results = run_checks(failing_checks, executor, skip=skip)

    executor.shutdown()

    all_ok = len(filter_failing_checks(results)) == 0

    if all_ok:
        print("\nLooks good to me now!")
        return 0

    print("\nSorry I couldn't fix it... ask for help in #discuss-dev-infra.")
    return 1
