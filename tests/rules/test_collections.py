# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from rattle.config import collect_rules
from rattle.config.models import Config
from rattle.selectors import QualifiedRule


def test_builtin_collections_resolve_rules() -> None:
    for collection in [
        "rattle.rules.exports",
        "rattle.rules.modernization",
        "rattle.rules.legacy",
        "rattle.rules.policy",
        "rattle.rules.style",
        "rattle.rules.typing",
    ]:
        rules = collect_rules(Config(enable=[QualifiedRule(collection)], python_version=None))
        assert len(rules) > 0, f"Collection {collection} resolved 0 rules"
