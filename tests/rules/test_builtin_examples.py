from rattle.config import collect_rules
from rattle.config.models import Config
from rattle.selectors import QualifiedRule
from rattle.testing import add_lint_rule_tests_to_module

add_lint_rule_tests_to_module(
    globals(),
    collect_rules(
        Config(
            enable=[
                QualifiedRule("rattle.rules.exports"),
                QualifiedRule("rattle.rules.modernization"),
                QualifiedRule("rattle.rules.legacy"),
                QualifiedRule("rattle.rules.policy"),
                QualifiedRule("rattle.rules.style"),
                QualifiedRule("rattle.rules.typing"),
            ],
            python_version=None,
        )
    ),
)
