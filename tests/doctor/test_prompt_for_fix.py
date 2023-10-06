from __future__ import annotations

import builtins
from unittest import mock

import pytest  # type: ignore

from devenv import doctor
from devenv.tests.doctor.devenv.checks import passing_check


prompts_for_fix_yes: list[str] = [
    "y",
    "Y",
    "yes",
    "Yes",
    "yEs",
    "yeS",
    "YEs",
    "yES",
    "YES",
    "",
]

prompts_for_fix_no: list[str] = [
    "n",
    "N",
    "no",
    "No",
    "nO",
    "NO",
    "any other string",
]


@pytest.mark.parametrize("yes", prompts_for_fix_yes)  # type: ignore
def test_prompt_for_fix_yes(yes: str) -> None:
    check = doctor.Check(passing_check)
    with mock.patch.object(builtins, "input", lambda _: yes):
        assert doctor.prompt_for_fix(check)


@pytest.mark.parametrize("no", prompts_for_fix_no)  # type: ignore
def test_prompt_for_fix_no(no: str) -> None:
    check = doctor.Check(passing_check)
    with mock.patch.object(builtins, "input", lambda _: no):
        assert not doctor.prompt_for_fix(check)
