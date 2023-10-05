from __future__ import annotations

from unittest import mock

from devenv import doctor
from devenv.tests.doctor.devenv.checks import passing_check

import builtins
import pytest  # type: ignore


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
        assert doctor.prompt_for_fix(check) == True


@pytest.mark.parametrize("no", prompts_for_fix_no)  # type: ignore
def test_prompt_for_fix_no(no: str) -> None:
    check = doctor.Check(passing_check)
    with mock.patch.object(builtins, "input", lambda _: no):
        assert doctor.prompt_for_fix(check) == False
