# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from rattle.config import collect_rules
from rattle.ftypes import Config, QualifiedRule
from rattle.testing import add_lint_rule_tests_to_module
from rattle.tests.cli import CliTest
from rattle.tests.config import ConfigTest
from rattle.tests.engine import EngineTest
from rattle.tests.ftypes import TypesTest
from rattle.tests.rule import RuleTest, RunnerTest
from rattle.tests.smoke import SmokeTest

add_lint_rule_tests_to_module(
    globals(),
    collect_rules(
        Config(
            enable=[
                QualifiedRule("rattle.rules.exports"),
                QualifiedRule("rattle.rules.fixit"),
                QualifiedRule("rattle.rules.fixit_extra"),
                QualifiedRule("rattle.rules.policy"),
                QualifiedRule("rattle.rules.style"),
                QualifiedRule("rattle.rules.typing"),
            ],
            python_version=None,
        )
    ),
)
