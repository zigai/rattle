# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Linting framework built on LibCST, with automatic fixes."""

from rattle.__version__ import __version__
from rattle.api import print_result, rattle_bytes, rattle_file, rattle_paths
from rattle.ast import AstContext, AstParseError, AstProvider
from rattle.config.models import Config, Options
from rattle.diagnostics import CodePosition, CodeRange, FileContent, LintViolation, Result
from rattle.formatting import Formatter
from rattle.rule import Invalid, LintRule, RuleReference, RuleSetting, Valid
from rattle.selectors import QualifiedRule, RuleNameSelector, Tags

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
