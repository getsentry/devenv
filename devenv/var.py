from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo


def _vars(context: Context) -> dict[str, str]:
    return {
        "coderoot": context["code_root"],
    }


def main(context: Context, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "name",
        nargs="?",
        type=str,
        help="variable name to look up",
    )
    args = parser.parse_args(argv)

    vs = _vars(context)

    if args.name is None:
        print(f"available variables:")
        for name in sorted(vs):
            print(name)
        return 0

    if args.name not in vs:
        print(f"unknown variable: {args.name}", file=sys.stderr)
        return 1

    print(vs[args.name])
    return 0


module_info = DevModuleInfo(
    action=main,
    name=__name__,
    command="var",
    help="Print the value of a devenv variable (coderoot).",
)
