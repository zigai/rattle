# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase

from packaging.version import Version

from rattle import config
from rattle.config.models import Config, RawConfig
from rattle.selectors import RuleNameSelector


class ConfigTest(TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.td = TemporaryDirectory()
        self.tdp = Path(self.td.name).resolve()

        self.noise = self.tdp / "noise"
        self.outer = self.tdp / "outer"
        self.inner = self.tdp / "outer" / "inner"
        self.noise.mkdir()
        self.inner.mkdir(parents=True)

        (self.tdp / "pyproject.toml").write_text(
            dedent(
                """
                [tool.rattle]
                root = true
                enable-root-import = true
                enable = ["more.rules"]
                disable = ["rattle.rules.something_specific"]
                python-version = "3.8"

                [[tool.rattle.overrides]]
                path = "other"
                enable = ["other.stuff", ".globalrules"]
                disable = ["modernization"]
                options = {"other.stuff:whatever"={key="value"}}
                python-version = "3.10"
                """
            )
        )
        (self.outer / "pyproject.toml").write_text(
            dedent(
                """
                [tool.rattle]
                enable = [".localrules"]
                disable = ["modernization"]
                """
            )
        )
        (self.noise / "pyproject.toml").write_text(
            dedent(
                """
                [tool.fuzzball]
                something = "whatever"
                """
            )
        )
        (self.inner / "pyproject.toml").write_text(
            dedent(
                """
                [tool.rattle]
                root = true
                enable = ["fake8", "make8"]
                disable = ["foo.bar"]
                unknown = "hello"
                """
            )
        )

    def tearDown(self) -> None:
        self.td.cleanup()

    def test_config_merger(self) -> None:
        root = self.tdp
        target = root / "a" / "b" / "c" / "foo.py"

        params: Sequence[tuple[str, list[RawConfig], Config]] = (
            (
                "empty",
                [],
                Config(
                    path=target,
                    root=Path(target.anchor),
                ),
            ),
            (
                "single",
                [
                    RawConfig(
                        (root / "pyproject.toml"),
                        {
                            "enable": ["foo", "bar"],
                            "disable": ["bar"],
                        },
                    ),
                ],
                Config(
                    path=target,
                    root=root,
                    enable=[RuleNameSelector("foo")],
                    disable=[RuleNameSelector("bar")],
                ),
            ),
            (
                "without root",
                [
                    RawConfig(
                        (root / "a/b/c/pyproject.toml"),
                        {"enable": ["foo"], "python-version": "3.10"},
                    ),
                    RawConfig(
                        (root / "a/b/pyproject.toml"),
                        {"enable": ["bar"], "disable": ["foo"]},
                    ),
                    RawConfig(
                        (root / "a/pyproject.toml"),
                        {"enable": ["foo"], "python-version": "3.8"},
                    ),
                ],
                Config(
                    path=target,
                    root=(root / "a"),
                    enable=[
                        RuleNameSelector("bar"),
                        RuleNameSelector("foo"),
                    ],
                    python_version=Version("3.10"),
                ),
            ),
            (
                "with root",
                [
                    RawConfig(
                        (root / "a/b/c/pyproject.toml"),
                        {"enable": ["foo"], "root": True},
                    ),
                    RawConfig(
                        (root / "a/b/pyproject.toml"),
                        {},
                    ),
                    RawConfig(
                        (root / "a/pyproject.toml"),
                        {},
                    ),
                ],
                Config(
                    path=target,
                    root=(root / "a/b/c"),
                    enable=[RuleNameSelector("foo")],
                ),
            ),
            (
                "option merge",
                [
                    RawConfig(
                        (root / "a/b/c/pyproject.toml"),
                        {
                            "options": {
                                "rattle.rules.legacy:use-f-string": {
                                    "allowed_prefixes": ["TODO", "FIXME"],
                                    "structured_entries": [
                                        {"symbol": "typing.cast", "message": "Avoid cast."}
                                    ],
                                }
                            }
                        },
                    ),
                    RawConfig(
                        (root / "a/b/pyproject.toml"),
                        {
                            "options": {
                                "rattle.rules.legacy:use-f-string": {
                                    "simple_expression_max_length": 60
                                }
                            }
                        },
                    ),
                    RawConfig(
                        (root / "a/pyproject.toml"),
                        {
                            "options": {
                                "rattle.rules.legacy:use-f-string": {
                                    "simple_expression_max_length": 30,
                                    "allow_dot_format": False,
                                }
                            }
                        },
                    ),
                ],
                Config(
                    path=target,
                    root=(root / "a"),
                    options={
                        "rattle.rules.legacy:use-f-string": {
                            "simple_expression_max_length": 60,
                            "allow_dot_format": False,
                            "allowed_prefixes": ["TODO", "FIXME"],
                            "structured_entries": [
                                {"symbol": "typing.cast", "message": "Avoid cast."}
                            ],
                        }
                    },
                ),
            ),
        )
        for name, raw_configs, expected in params:
            with self.subTest(name):
                actual = config.ConfigMerger(target, raw_configs).merge()
                assert expected == actual

        with self.subTest("per-file rule toggles"):
            target = root / "tests" / "unit" / "special.py"
            raw_configs = [
                RawConfig(
                    (root / "pyproject.toml"),
                    {
                        "enable": ["bar"],
                        "overrides": [{"path": "tests", "disable": ["bar", "foo"]}],
                        "per-file-enable": {"tests/unit/special.py": ["foo"]},
                        "per-file-disable": {"tests/**/*.py": ["bar"]},
                    },
                )
            ]

            actual = config.ConfigMerger(target, raw_configs).merge()

            assert actual == Config(
                path=target,
                root=root,
                enable=[RuleNameSelector("foo")],
                disable=[RuleNameSelector("bar")],
            )

        with self.subTest("rule name selectors"):
            raw_configs = [
                RawConfig(
                    (root / "pyproject.toml"),
                    {
                        "enable": ["use-f-string"],
                        "disable": ["no-static-if-condition"],
                    },
                )
            ]

            actual = config.ConfigMerger(target, raw_configs).merge()

            assert actual == Config(
                path=target,
                root=root,
                enable=[RuleNameSelector("use-f-string")],
                disable=[RuleNameSelector("no-static-if-condition")],
            )
