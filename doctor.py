from __future__ import annotations

import argparse
import subprocess
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor

from devenv.lib import brew_packages

help = "Diagnose and attempt to fix common issues."


class CheckBrewPackages:
    def __init__(self, packages: Sequence[str], reporoot: str):
        self.packages = packages
        self.reporoot = reporoot

    def __repr__(self) -> str:
        return "brew packages"

    def check(self) -> tuple[bool, str]:
        ok = True
        message = ""
        packages = brew_packages()
        for p in self.packages:
            if p not in packages:
                message += f"\nbrew package {p} not installed!"
                ok = False
        return ok, message

    def fix(self) -> tuple[bool, str]:
        try:
            subprocess.run(("brew", "bundle"), cwd=self.reporoot, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            return (
                False,
                f"""
`{e.cmd}` returned code {e.returncode}
stdout:
{e.stdout.decode()}
stderr:
{e.stderr.decode()}
""",
            )
        return True, ""


def main(context: dict, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=help)
    parser.parse_args(argv)

    repo = context["repo"]
    if repo not in {"sentry", "getsentry"}:
        print(f"repo {repo} not supported yet!")
        return 1

    checks = {
        "sentry": (
            CheckBrewPackages(
                (
                    "docker",
                    "chromedriver",
                    # required for yarn test -u
                    "watchman",
                ),
                context["reporoot"],
            ),
        ),
        "getsentry": (),
    }

    # We run every check on a separate thread, aggregate the results,
    # attempt any fixes, then recheck and provide a final report.
    executor = ThreadPoolExecutor(max_workers=len(checks[repo]))
    print("Running checks...")

    futures = {}
    results = {}
    for check in checks[repo]:
        futures[check] = executor.submit(check.check)
    for check, future in futures.items():
        results[check] = future.result()

    retry = []
    for check, result in results.items():
        ok, msg = result
        if ok:
            print(f"✅ check {check}")
            continue
        print(f"❌ check {check}{msg}")
        retry.append(check)

    if not retry:
        print("\nLooks good to me.")
        executor.shutdown()
        return 0

    print("\nAttempting to run autofixes (if any) for the checks that failed...")
    futures = {}
    results = {}
    for check in retry:
        futures[check] = executor.submit(check.fix)
    for check, future in futures.items():
        results[check] = future.result()

    for check, result in results.items():
        ok, msg = result
        if ok:
            print(f"✅ fix {check}")
            continue
        print(f"❌ fix {check}{msg}")

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
            print(f"✅ check {check}")
            continue
        print(f"❌ check {check}{msg}")
        all_ok = False

    if all_ok:
        print("\nLooks good to me now!")
        return 0

    print("\nSorry I couldn't fix it... ask for help in #discuss-dev-infra.")
    return 1
