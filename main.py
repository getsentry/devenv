from __future__ import annotations

import argparse
from typing import Sequence

from devenv import doctor


class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(
            f"""commands:
doctor - {doctor.help}
"""
        )
        raise SystemExit(1)


def main(argv: Sequence[str] | None = None) -> int:
    parser = CustomArgumentParser()
    parser.add_argument(
        "command",
        choices={
            "doctor",
        },
    )
    args, remainder = parser.parse_known_args(argv)

    # self_update()

    # TODO: autodetection of repository based on pwd
    context = {
        "repo": "sentry",
    }

    if args.command == "doctor":
        doctor.main(context, remainder)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
