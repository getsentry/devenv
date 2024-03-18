from __future__ import annotations

import builtins
import os
from unittest import mock

import pytest

from devenv import doctor
from tests.utils import import_module_from_file

here = os.path.join(os.path.dirname(__file__))


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


@pytest.mark.parametrize("yes", prompts_for_fix_yes)
def test_prompt_for_fix_yes(yes: str) -> None:
    passing_check = import_module_from_file(
        f"{here}/checks/passing_check.py", "passing_check"
    )

    check = doctor.Check(passing_check)

    def fake_input(_: str) -> str:
        return yes

    with mock.patch.object(builtins, "input", fake_input):
        assert doctor.prompt_for_fix(check)


@pytest.mark.parametrize("no", prompts_for_fix_no)
def test_prompt_for_fix_no(no: str) -> None:
    passing_check = import_module_from_file(
        f"{here}/checks/passing_check.py", "passing_check"
    )

    check = doctor.Check(passing_check)

    def fake_input(_: str) -> str:
        return no

    with mock.patch.object(builtins, "input", fake_input):
        assert not doctor.prompt_for_fix(check)
