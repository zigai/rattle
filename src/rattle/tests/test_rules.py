# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from rattle.config import collect_rules
from rattle.ftypes import Config, QualifiedRule
from rattle.testing import generate_lint_rule_test_cases

for generated_case in generate_lint_rule_test_cases(
    collect_rules(
        Config(
            enable=[
                QualifiedRule("rattle.rules.exports"),
                QualifiedRule("rattle.rules.fixit"),
                QualifiedRule("rattle.rules.fixit_extra"),
                QualifiedRule("rattle.rules.policy"),
                QualifiedRule("rattle.rules.style"),
            ],
            python_version=None,
        )
    )
):
    globals()[f"Test{generated_case.__name__}"] = generated_case

if "generated_case" in globals():
    del globals()["generated_case"]
