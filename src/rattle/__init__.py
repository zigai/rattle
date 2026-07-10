# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Linting framework built on LibCST, with automatic fixes."""

from rattle.__version__ import __version__
from rattle.api import print_result, rattle_bytes, rattle_file, rattle_paths
from rattle.ast import AstContext, AstParseError, AstProvider
from rattle.format import Formatter
from rattle.ftypes import (
    CodePosition,
    CodeRange,
    Config,
    FileContent,
    Invalid,
    LintViolation,
    Options,
    QualifiedRule,
    Result,
    RuleNameSelector,
    Tags,
    Valid,
)
from rattle.rule import LintRule, RuleReference, RuleSetting

__all__ = [
    "AstContext",
    "AstParseError",
    "AstProvider",
    "CodePosition",
    "CodeRange",
    "Config",
    "FileContent",
    "Formatter",
    "Invalid",
    "LintRule",
    "LintViolation",
    "Options",
    "QualifiedRule",
    "Result",
    "RuleNameSelector",
    "RuleReference",
    "RuleSetting",
    "Tags",
    "Valid",
    "__version__",
    "print_result",
    "rattle_bytes",
    "rattle_file",
    "rattle_paths",
]
