import pytest

from rattle.rule import LintRule
from rattle.rules.modernization.explicit_frozen_dataclass import ExplicitFrozenDataclass
from rattle.rules.modernization.no_named_tuple import NoNamedTuple
from rattle.rules.typing.use_types_from_typing import UseTypesFromTyping
from rattle.rules.typing.variadic_callable_syntax import VariadicCallableSyntax
from tests.support import run_rule


@pytest.mark.parametrize(
    ("rule", "source"),
    [
        (
            ExplicitFrozenDataclass(),
            "from dataclasses import dataclass\n(alias,) = (dataclass,)\n@alias\nclass C: pass\n",
        ),
        (
            NoNamedTuple(),
            "from typing import NamedTuple\n(alias,) = (NamedTuple,)\nclass C(alias): pass\n",
        ),
        (
            VariadicCallableSyntax(),
            "from typing import Callable\n(alias,) = (Callable,)\nx: alias[[...], int]\n",
        ),
        (
            UseTypesFromTyping(),
            "from builtins import list as ListType\n(alias,) = (ListType,)\nx: alias[str]\n",
        ),
    ],
)
def test_assignment_alias_tracker_supports_destructuring(rule: LintRule, source: str) -> None:
    _runner, reports = run_rule(rule, source)

    assert len(reports) == 1
