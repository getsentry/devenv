from __future__ import annotations

from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

from devenv.lib.context import Context

ExitCode: TypeAlias = "str | int | None"

Action: TypeAlias = "Callable[[Context, Sequence[str] | None], ExitCode]"


@dataclass(frozen=True)
class DevModuleInfo:
    name: str
    command: str
    help: str
    action: Action


def require(var: str, message: str) -> Callable[[Action], Action]:
    def outer(main: Action) -> Action:
        def inner(context: Context, args: Sequence[str] | None) -> ExitCode:
            if context.get(var) is None:
                raise SystemExit(message)
            return main(context, args)

        return inner

    return outer


require_repo = require("repo", "This command requires a repository")
