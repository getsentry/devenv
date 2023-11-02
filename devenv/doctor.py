from __future__ import annotations

import argparse
import importlib.util
import typing
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Sequence
from concurrent.futures import Future
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
    """
    A check is a module with the following attributes:
    - name: str
    - tags: Set[str]
    - check: Callable[[], Tuple[bool, str]]
    - fix: Callable[[], Tuple[bool, str]]

    The check function should return a tuple of (ok, msg).
    The fix function should return a tuple of (ok, msg).

    The check and fix functions are wrapped with the checker and fixer decorators.
    """

    name: str
    tags: Set[str]
    check: Callable[[], Tuple[bool, str]]
    fix: Callable[[], Tuple[bool, str]]

    def __init__(self, module: ModuleType):
        # Check that the module has the required attributes.
        assert hasattr(module, "name"), "missing the `name` attribute"
        assert isinstance(
            module.name, str
        ), "the `name` attribute should be a str"
        self.name = module.name

        assert hasattr(module, "tags"), "missing the `tags` attribute"
        assert isinstance(
            module.tags, set
        ), "the `tags` attribute should be a set"
        self.tags = module.tags

        # Check that the module has the check and fix functions.
        assert hasattr(module, "check"), "must have a `check` function"
        assert callable(
            module.check
        ), "the `check` attribute must be a function"
        check_hints = typing.get_type_hints(module.check)
        assert (
            check_hints["return"] == Tuple[bool, str]
        ), "`check(...)` should return a tuple of (bool, str)"
        self.check = checker(module.check)

        assert hasattr(module, "fix"), "must have a `fix` function"
        assert callable(module.fix), "the `fix` attribute should be a function"
        fix_hints = typing.get_type_hints(module.fix)
        assert (
            fix_hints["return"] == Tuple[bool, str]
        ), "`fix(...)` should return a tuple of (bool, str)"
        self.fix = fixer(module.fix)

        super().__init__()


def load_checks(context: Dict[str, str], match_tags: Set[str]) -> List[Check]:
    """
    Load all checks from the checks directory.
    Optionally filter by tags.
    If a check doesn't have the required attributes, skip it.
    """
    checks: list[Check] = []
    for module_finder, module_name, _ in walk_packages(
        (f'{context["reporoot"]}/devenv/checks',)
    ):
        module_spec = module_finder.find_spec(module_name, None)

        # it "should be" impossible to fail these:
        assert module_spec is not None, module_name
        assert module_spec.loader is not None, module_name

        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        try:
            check = Check(module)
        except AssertionError as e:
            print(f"⚠️ Skipping {module_name}: {e}")
            continue
        if match_tags and not check.tags.issuperset(match_tags):
            continue
        checks.append(check)
    return checks


def run_checks(
    checks: List[Check],
    executor: ThreadPoolExecutor,
    skip: Iterable[Check] = (),
) -> Dict[Check, Tuple[bool, str]]:
    """
    Run checks in parallel, and return a dict of results.
    Results are a tuple of (ok, msg).
    """
    futures: dict[Check, Future[tuple[bool, str]]] = {}
    results: dict[Check, tuple[bool, str]] = {}
    for check in checks:
        if check in skip:
            print(f"\t⏭️  Skipped {check.name}".expandtabs(4))
            continue
        futures[check] = executor.submit(check.check)
    for check, future in futures.items():
        try:
            results[check] = future.result()
        except Exception as e:
            results[check] = (False, f"Check threw a runtime exception: {e}")
    return results


def filter_failing_checks(
    results: Dict[Check, Tuple[bool, str]]
) -> List[Check]:
    """Print a report of the results, and return a list of failing checks."""
    failing_checks: list[Check] = []
    for check, result in results.items():
        ok, msg = result
        if ok:
            print(f"\t✅ check: {check.name}".expandtabs(4))
            continue
        print(f"\t❌ check: {check.name}{msg}".expandtabs(4))
        failing_checks.append(check)
    return failing_checks


def prompt_for_fix(check: Check) -> bool:
    """Prompt the user to attempt a fix."""
    return input(
        f"\t\tDo you want to attempt to fix {check.name}? (Y/n): ".expandtabs(4)
    ).lower() in {"y", "yes", ""}


def attempt_fix(check: Check, executor: ThreadPoolExecutor) -> Tuple[bool, str]:
    """Attempt to fix a check, and return a tuple of (ok, msg)."""
    future = executor.submit(check.fix)
    try:
        return future.result()
    except Exception as e:
        return False, f"Fix threw a runtime exception: {e}"


def main(context: Dict[str, str], argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=help)
    parser.add_argument(
        "--tag",
        type=str,
        action="append",
        help="Used to match a subset of checks.",
    )
    parser.add_argument(
        "--check-only", action="store_true", help="Do not run fixers."
    )
    args = parser.parse_args(argv)

    match_tags: set[str] = set(args.tag if args.tag else ())

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
    skip: list[Check] = []
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
