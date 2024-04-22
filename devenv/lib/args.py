from __future__ import annotations

from collections.abc import Sequence
from typing import List
from typing import NotRequired
from typing import Tuple
from typing import TypedDict


class ParseError(SystemExit):
    pass


class Parser:
    def __init__(self, spec: str):
        self.spec = spec.strip(" ")
        self.pos = 0

        self.args: List[str] = []
        self.help = ""
        self.meta = ""
        self.required = True
        self.choices: List[str] = []
        self.type: str

    def start(self) -> None:
        """Start parsing -- potential next states are either to parse a flag or a named arg"""
        if self.spec[self.pos] == "-":
            self.option()
        elif self.spec[self.pos].isalpha():
            self.positional()
        elif self.spec[self.pos] == "[":
            self.optional()
        else:
            self.unexpected_char()

        if not self.eof():
            self.help = self.spec[self.pos :]

    def eof(self) -> bool:
        return self.pos >= len(self.spec)

    def loc(self, name: str = "", pos: int | None = None) -> str:
        where = pos if pos is not None else self.pos
        return f"{self.spec}\n{' ' * where}^ {name}"

    def print_loc(self, name: str = "") -> None:
        print(self.loc(name))

    def unexpected_char(self, expected: str | None = None) -> None:
        if expected is not None:
            details = self.loc(f"expected {expected}")
        else:
            details = self.loc("unexpected")

        raise ParseError(
            f"Unexpected character '{self.spec[self.pos]}' in arg spec at {self.pos}\n{details}"
        )

    def unexpected_eof(self, expected: str, pos: int) -> None:
        details = self.loc(f"missing {expected}", pos=pos)
        raise ParseError(f"Unexpected end of string in arg spec\n{details}")

    def consume_ws(self) -> None:
        while not self.eof() and self.spec[self.pos].isspace():
            self.pos += 1

    def get_bracketed(self, start_token: str, end_token: str) -> str:
        if self.spec[self.pos] != start_token:
            self.unexpected_char("<")
        self.pos += 1
        start_pos = self.pos
        while self.spec[self.pos] != end_token:
            self.pos += 1
            if self.eof():
                self.unexpected_eof(expected=end_token, pos=start_pos)
        value = self.spec[start_pos : self.pos]
        self.pos += 1
        return value

    def positional(self) -> None:
        self.type = "positional"
        start_pos = self.pos
        while not self.eof() and (
            self.spec[self.pos].isalpha() or self.spec[self.pos] == "-"
        ):
            self.pos += 1

        arg = self.spec[start_pos : self.pos]
        self.args = [arg]
        if self.eof():
            return

        if self.spec[self.pos] == ":":
            self.pos += 1
            if self.eof():
                self.unexpected_eof("choice list", pos=self.pos - 1)
            self.choices = self.get_bracketed("(", ")").split("|")

        self.consume_ws()
        return

    def optional(self) -> None:
        if self.spec[self.pos] != "[":
            self.unexpected_char("[")

        self.required = False

        start_pos = self.pos

        self.pos += 1  # consume [

        self.option()
        self.consume_ws()
        if self.eof():
            self.unexpected_eof("]", pos=start_pos)
        if self.spec[self.pos] != "]":
            self.unexpected_char("]")
        self.pos += 1

    def option(self) -> None:
        self.type = "option"
        self.option_alias()

        if self.eof():
            return

        # check for alias option
        if self.spec[self.pos] == ",":
            self.pos += 1
            self.consume_ws()
            self.option_alias()

        if self.eof():
            return

        if self.spec[self.pos] == "<":
            self.meta = self.get_bracketed("<", ">")
        elif self.spec[self.pos] == "(":
            self.choices = self.get_bracketed("(", ")").split("|")

        self.consume_ws()

    def option_alias(self) -> None:
        if self.spec[self.pos] != "-":
            self.unexpected_char(expected="-")

        self.pos += 1  # consume '-'

        if self.spec[self.pos] == "-":
            t, name = self.long_option()
        elif self.spec[self.pos].isalpha():
            t, name = self.short_option()
        else:
            self.unexpected_char()

        if t == "short":
            self.args = [f"-{name}"] + self.args
        else:
            self.args = self.args + [f"--{name}"]

        self.consume_ws()

    def short_option(self) -> Tuple[str, str]:
        name = self.spec[self.pos]
        self.pos += 1
        return "short", name

    def long_option(self) -> Tuple[str, str]:
        self.pos += 1
        start_pos = self.pos
        if not self.spec[self.pos].isalpha():
            self.unexpected_char()

        while not self.eof() and (
            self.spec[self.pos].isalpha() or self.spec[self.pos] == "-"
        ):
            self.pos += 1

        name = self.spec[start_pos : self.pos]

        return "long", name


class ArgArgs(TypedDict):
    required: NotRequired[bool]
    metavar: NotRequired[str]
    help: NotRequired[str]
    choices: NotRequired[List[str]]
    action: NotRequired[str]


def generate(spec: str) -> Tuple[Sequence[str], ArgArgs]:
    spec = spec.strip(" ")
    parser = Parser(spec)

    parser.start()

    kwargs = ArgArgs()

    if parser.type == "option":
        kwargs["required"] = parser.required

        if parser.meta:
            kwargs["metavar"] = parser.meta
        if parser.choices:
            kwargs["choices"] = parser.choices

        if not (parser.meta or parser.choices):
            kwargs["action"] = "store_true"

        if parser.help:
            kwargs["help"] = parser.help
        else:
            if parser.choices:
                kwargs["help"] = f"must be one of {parser.choices}"
    else:
        name = parser.meta or parser.args[0]
        kwargs["metavar"] = name

        if parser.choices:
            kwargs["choices"] = parser.choices
        if parser.help:
            kwargs["help"] = parser.help
        else:
            if parser.choices:
                kwargs["help"] = f"{name} must be one of {parser.choices}"

    return parser.args, kwargs
