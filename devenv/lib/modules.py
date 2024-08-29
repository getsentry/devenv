from __future__ import annotations

from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias
from typing import TypeGuard

from devenv.lib.context import Context
from devenv.lib.context import ContextRequiredRepo

ExitCode: TypeAlias = "str | int | None"

Action: TypeAlias = "Callable[[Context, Sequence[str] | None], ExitCode]"
ActionRequiredRepo: TypeAlias = (
    "Callable[[ContextRequiredRepo, Sequence[str] | None], ExitCode]"
)


@dataclass(frozen=True)
class DevModuleInfo:
    name: str
    command: str
    help: str
    action: Action


@dataclass(frozen=True)
class DevModuleInfoRequiredRepo:
    name: str
    command: str
    help: str
    action: ActionRequiredRepo


def context_required_repo(context: Context) -> TypeGuard[ContextRequiredRepo]:
    return context.get("repo") is not None


def require_repo(main: Action) -> ActionRequiredRepo:
    def inner(context: Context, args: Sequence[str] | None) -> ExitCode:
        if not context_required_repo(context):
            raise SystemExit("This command requires a repository")
        return main(context, args)

    return inner
