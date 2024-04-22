from __future__ import annotations

import argparse
import importlib
import inspect
import sys
from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from pkgutil import walk_packages
from types import ModuleType
from typing import List
from typing import TypeAlias

from devenv.lib import args
from devenv.lib.context import Context

ExitCode: TypeAlias = "str | int | None"
Action: TypeAlias = "Callable[[Context, Sequence[str] | None], ExitCode]"
ParserFn: TypeAlias = "Callable[[argparse.ArgumentParser], None]"


@dataclass(frozen=True)
class CommandInfo:
    name: str
    action: Action
    help: str
    arguments: Sequence[ParserFn]


@dataclass(frozen=True)
class ModuleDef:
    module_name: str
    name: str
    help: str


@dataclass(frozen=True)
class DevModuleInfo:
    module_def: ModuleDef
    commands: Sequence[CommandInfo]


class ModuleAction:
    def __init__(self, action: Action):
        self.name: str
        self.help: str

        self.action = action
        self.argument_parsers: List[ParserFn] = []

    def __call__(
        self, context: Context, args: Sequence[str] | None
    ) -> ExitCode:
        return self.action(context, args)

    def add_argparser(self, fn: ParserFn) -> None:
        self.argument_parsers.append(fn)

    def command_info(self) -> CommandInfo:
        return CommandInfo(
            self.name, self.action, self.help, arguments=self.argument_parsers
        )


def command(name: str, help: str) -> Callable[[Action], Action]:
    def wrap(main: Action | ModuleAction) -> Action:
        if isinstance(main, ModuleAction):
            module_action = main
        else:
            module_action = ModuleAction(main)

        module_action.name = name
        module_action.help = help

        return module_action

    return wrap


def argument(spec: str | ParserFn) -> Callable[[Action], Action]:
    fn: ParserFn
    if isinstance(spec, str):
        ak = args.generate(spec)

        def add_args(argparse: argparse.ArgumentParser) -> None:
            argparse.add_argument(*ak[0], **ak[1])

        fn = add_args
    else:
        fn = spec

    def wrap(main: Action) -> Action:
        if isinstance(main, ModuleAction):
            module_action = main
        else:
            module_action = ModuleAction(main)

        module_action.add_argparser(fn)
        return module_action

    return wrap


def require(var: str, message: str) -> Callable[[Action], Action]:
    def outer(main: Action) -> Action:
        def inner(context: Context, args: Sequence[str] | None) -> ExitCode:
            if context.get(var) is None:
                raise SystemExit(message)
            return main(context, args)

        return inner

    return outer


require_repo = require("repo", "This command requires a repository")


def command_info(module: ModuleType) -> Sequence[CommandInfo]:
    return [
        action.command_info()
        for name, action in inspect.getmembers(
            module, lambda m: isinstance(m, ModuleAction)
        )
    ]


def module_info(module: ModuleType) -> DevModuleInfo:
    info = module.module_info
    return DevModuleInfo(module_def=info, commands=command_info(module))


def load_modules(path: str, package: str) -> Sequence[ModuleType]:
    all_modules = []
    for module_finder, module_name, _ in walk_packages(
        (path,), prefix=f"{package}."
    ):
        module_spec = module_finder.find_spec(module_name, None)

        # it "should be" impossible to fail these:
        assert module_spec is not None, module_name
        assert module_spec.loader is not None, module_name

        module = importlib.util.module_from_spec(module_spec)

        if module_name not in sys.modules:
            # load if not already loaded
            sys.modules[module_name] = module
            module.__loader__.exec_module(module)  # type: ignore

        if hasattr(module, "module_info"):
            all_modules.append(module)

    return all_modules
