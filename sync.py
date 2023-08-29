from __future__ import annotations

import argparse
from typing import Sequence

help = "Resyncs the environment."


def main(context: dict, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=help)
    parser.parse_args(argv)

    repo = context["repo"]
    if repo not in {"sentry", "getsentry"}:
        print(f"repo {repo} not supported yet!")
        return 1

    # What does it take to have one venv that sentry and getsentry can coexist in?
    # Try this. I suppose it's pretty easy since we now have requirements-getsentry.txt
    # in sentry repo.

    # If the venv doesn't exist, create it with the expected python version.
    print(context["reporoot"])
    # get_python

    # Check the python version. If mismatch, then recreate the venv.

    # Install -e . and with requirements-dev-frozen.txt.

    # TODO: frontend environment

    return 0
