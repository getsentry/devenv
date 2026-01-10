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

import devenv.checks
from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo
from devenv.lib.repository import Repository
from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer


class Check:
    """
    A check is a module with the following attributes:
    - name: str
    - tags: set[str]
    - check: Callable[[], tuple[bool, str]]
    - fix: Callable[[], tuple[bool, str]]

    The check function should return a tuple of (ok, msg).
    The fix function should return a tuple of (ok, msg).

    The check and fix functions are wrapped with the checker and fixer decorators.
    """

    name: str
    tags: set[str]
    check: Callable[[], tuple[bool, str]]
    fix: Callable[[], tuple[bool, str]]

    def __init__(self, module: ModuleType):
        # Check that the module has the required attributes.
        if not hasattr(module, "name"):
            raise ValueError("missing the `name` attribute")
        if not isinstance(module.name, str):
            raise ValueError("the `name` attribute should be a str")
        self.name = module.name

        if not hasattr(module, "tags"):
            raise ValueError("missing the `tags` attribute")
        if not isinstance(module.tags, set):
            raise ValueError("the `tags` attribute should be a set")
        self.tags = module.tags

        # Check that the module has the check and fix functions.
        if not hasattr(module, "check"):
            raise ValueError("must have a `check` function")
        if not callable(module.check):
            raise ValueError("the `check` attribute must be a function")
        check_hints = typing.get_type_hints(module.check)
        if not (check_hints["return"] == tuple[bool, str]):
            raise ValueError(
                "`check(...)` should return a tuple of (bool, str)"
            )
        self.check = checker(module.check)

        if not hasattr(module, "fix"):
            raise ValueError("must have a `fix` function")
        if not callable(module.fix):
            raise ValueError("the `fix` attribute should be a function")
        fix_hints = typing.get_type_hints(module.fix)
        if not (fix_hints["return"] == tuple[bool, str]):
            raise ValueError("`fix(...)` should return a tuple of (bool, str)")
        self.fix = fixer(module.fix)

        super().__init__()


def load_checks(repo: Repository, match_tags: set[str]) -> List[Check]:
    """
    Load all checks from the checks directory.
    Optionally filter by tags.
    If a check doesn't have the required attributes, skip it.
    """
    checks: list[Check] = []

    for module_finder, module_name, _ in walk_packages(
        (f"{repo.config_path}/checks",)
    ):
        module_spec = module_finder.find_spec(module_name, None)

        # it "should be" impossible to fail these:
        assert module_spec is not None, module_name
        assert module_spec.loader is not None, module_name

        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        try:
            check = Check(module)
        except ValueError as e:
            print(f"⚠️ Skipping {module_name}: {e}")
            continue
        if match_tags and not check.tags.issuperset(match_tags):
            continue
        checks.append(check)
    return checks


def load_builtin_checks(match_tags: set[str]) -> List[Check]:
    """
    Loads builtin checks.
    Optionally filter by tags.
    If a check doesn't have the required attributes, skip it.
    """
    checks: list[Check] = []
    match_tags.add("builtin")

    for _, module_name, _ in walk_packages(devenv.checks.__path__):
        module = __import__(f"devenv.checks.{module_name}", fromlist=["_trash"])
        try:
            check = Check(module)
        except ValueError as e:
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
) -> Dict[Check, tuple[bool, str]]:
    """
    Run checks in parallel, and return a dict of results.
    Results are a tuple of (ok, msg).
    """
    futures: dict[Check, Future[tuple[bool, str]]] = {}
    results: dict[Check, tuple[bool, str]] = {}
    for check in checks:
        if check in skip:
            print(f"   ⏭️  Skipped {check.name}")
            continue
        futures[check] = executor.submit(check.check)
    for check, future in futures.items():
        try:
            results[check] = future.result()
        except Exception as e:
            results[check] = (False, f"Check threw a runtime exception: {e}")
    return results


def filter_failing_checks(
    results: Dict[Check, tuple[bool, str]]
) -> List[Check]:
    """Print a report of the results, and return a list of failing checks."""
    failing_checks: list[Check] = []
    for check, result in results.items():
        ok, msg = result
        if ok:
            print(f"   ✅ check: {check.name}")
            continue
        print(f"   ❌ check: {check.name}\n   {msg}")
        failing_checks.append(check)
    return failing_checks


def prompt_for_fix(check: Check) -> bool:
    """Prompt the user to attempt a fix."""
    return input(
        f"   Do you want to attempt to fix {check.name}? (Y/n): "
    ).lower() in {"y", "yes", ""}


def attempt_fix(check: Check, executor: ThreadPoolExecutor) -> tuple[bool, str]:
    """Attempt to fix a check, and return a tuple of (ok, msg)."""
    future = executor.submit(check.fix)
    try:
        return future.result()
    except Exception as e:
        return False, f"Fix threw a runtime exception: {e}"


def main(context: Context, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
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

    # First, we load builtin checks. These are not repo specific.
    checks = load_builtin_checks(match_tags)

    # Then we load any repo specific checks if any.
    repo = context.get("repo")
    if repo is not None:
        checks.extend(load_checks(repo, match_tags))

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

    skip: list[Check] = []
    print("\nLet's go through the failures one by one.")
    for check in failing_checks:
        print(f"❌ {check.name}")
        # Prompt for fixes one by one, so the user can decide to skip a fix.
        if prompt_for_fix(check):
            ok, msg = attempt_fix(check, executor)
            if ok:
                print(f"✅ fix: {check.name}")
            else:
                print(f"❌ fix: {check.name}{msg}")
        else:
            print(f"   ⏭️  Skipping {check.name}")
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


module_info = DevModuleInfo(
    action=main,
    name=__name__,
    command="doctor",
    help="Diagnose common issues, and optionally try to fix them.",
)
