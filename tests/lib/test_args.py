from __future__ import annotations

import argparse
from argparse import ArgumentError

import pytest

from devenv.lib import args
from devenv.lib.args import ArgArgs


def test_parse_simple() -> None:
    assert args.generate("-d") == (
        ["-d"],
        ArgArgs({"action": "store_true", "required": True}),
    )


def test_parse_long() -> None:
    assert args.generate("--dog-food") == (
        ["--dog-food"],
        ArgArgs({"action": "store_true", "required": True}),
    )


def test_parse_alias() -> None:
    assert args.generate("-d , --dog-food") == (
        ["-d", "--dog-food"],
        ArgArgs({"action": "store_true", "required": True}),
    )
    assert args.generate("--dog-food , -d") == (
        ["-d", "--dog-food"],
        ArgArgs({"action": "store_true", "required": True}),
    )
    assert args.generate("--dog-food,-d") == (
        ["-d", "--dog-food"],
        ArgArgs({"action": "store_true", "required": True}),
    )


def test_parse_metavar() -> None:
    assert args.generate("--dog-food <flavor>") == (
        ["--dog-food"],
        ArgArgs({"metavar": "flavor", "required": True}),
    )


def test_parse_optional() -> None:
    params = args.generate("[--dog-food <flavor>]")

    assert params == (["--dog-food"], {"metavar": "flavor", "required": False})

    parser = argparse.ArgumentParser(exit_on_error=False)
    parser.add_argument(*params[0], **params[1])

    parser.parse_args([])

    assert parser.parse_args(["--dog-food", "flavor"]).dog_food == "flavor"

    parser.parse_args([])

    with pytest.raises(ArgumentError):
        parser.parse_args(["--dog-food"])


def test_parse_choices() -> None:
    assert args.generate("--dog-food (beef|lamb)") == (
        ["--dog-food"],
        ArgArgs(
            {
                "choices": ["beef", "lamb"],
                "required": True,
                "help": "must be one of ['beef', 'lamb']",
            }
        ),
    )


def test_parse_positional() -> None:
    assert args.generate("food") == (["food"], {"metavar": "food"})


def test_parse_positional_choices() -> None:
    assert args.generate("food:(beef|lamb)") == (
        ["food"],
        ArgArgs(
            {
                "choices": ["beef", "lamb"],
                "metavar": "food",
                "help": "food must be one of ['beef', 'lamb']",
            }
        ),
    )


def test_parse_help() -> None:
    assert args.generate("-d  Selects the d option") == (
        ["-d"],
        ArgArgs(
            {
                "help": "Selects the d option",
                "action": "store_true",
                "required": True,
            }
        ),
    )
    assert args.generate("-d , --dog-food   Selects the d option") == (
        ["-d", "--dog-food"],
        ArgArgs(
            {
                "help": "Selects the d option",
                "action": "store_true",
                "required": True,
            }
        ),
    )
    assert args.generate("--dog-food (beef|lamb)    Selects the d option") == (
        ["--dog-food"],
        ArgArgs(
            {
                "choices": ["beef", "lamb"],
                "help": "Selects the d option",
                "required": True,
            }
        ),
    )
    assert args.generate("food:(beef|lamb) there is no chicken") == (
        ["food"],
        ArgArgs(
            {
                "choices": ["beef", "lamb"],
                "metavar": "food",
                "help": "there is no chicken",
            }
        ),
    )
