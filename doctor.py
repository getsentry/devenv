from __future__ import annotations

import argparse
from typing import Sequence

help = "Diagnose common issues."


def main(context: dict, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=help)
    args = parser.parse_args(argv)
    print(args)
    return 0
