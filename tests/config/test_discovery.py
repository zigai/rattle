# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase

from rattle import config
from rattle.config.models import RawConfig


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

    def test_locate_configs(self) -> None:
        for name, path, root, expected in (
            ("top", self.tdp, None, [self.tdp / "pyproject.toml"]),
            ("top file", self.tdp / "hello.py", None, [self.tdp / "pyproject.toml"]),
            (
                "outer",
                self.outer,
                None,
                [self.outer / "pyproject.toml", self.tdp / "pyproject.toml"],
            ),
            (
                "outer file",
                self.outer / "frob.py",
                None,
                [self.outer / "pyproject.toml", self.tdp / "pyproject.toml"],
            ),
            (
                "inner",
                self.inner,
                None,
                [
                    self.inner / "pyproject.toml",
                    self.outer / "pyproject.toml",
                    self.tdp / "pyproject.toml",
                ],
            ),
            (
                "inner file",
                self.inner / "test.py",
                None,
                [
                    self.inner / "pyproject.toml",
                    self.outer / "pyproject.toml",
                    self.tdp / "pyproject.toml",
                ],
            ),
            ("outer from outer", self.outer, self.outer, [self.outer / "pyproject.toml"]),
            (
                "inner from outer",
                self.inner,
                self.outer,
                [
                    self.inner / "pyproject.toml",
                    self.outer / "pyproject.toml",
                ],
            ),
            (
                "inner from inner",
                self.inner,
                self.inner,
                [self.inner / "pyproject.toml"],
            ),
        ):
            with self.subTest(name):
                actual = config.locate_configs(path, root)
                assert expected == actual

    def test_read_configs(self) -> None:
        # in-out priority order
        inner = self.inner / "pyproject.toml"
        noise = self.noise / "pyproject.toml"
        outer = self.outer / "pyproject.toml"
        top = self.tdp / "pyproject.toml"

        for name, paths, expected in (
            (
                "inner",
                [inner, noise, outer, top],
                [
                    RawConfig(
                        inner,
                        {
                            "root": True,
                            "enable": ["fake8", "make8"],
                            "disable": ["foo.bar"],
                            "unknown": "hello",
                        },
                    )
                ],
            ),
            (
                "inner partial",
                [noise, outer, top],
                [
                    RawConfig(outer, {"enable": [".localrules"], "disable": ["modernization"]}),
                    RawConfig(
                        top,
                        {
                            "root": True,
                            "enable-root-import": True,
                            "enable": ["more.rules"],
                            "disable": ["rattle.rules.something_specific"],
                            "python-version": "3.8",
                            "overrides": [
                                {
                                    "path": "other",
                                    "enable": ["other.stuff", ".globalrules"],
                                    "disable": ["modernization"],
                                    "options": {"other.stuff:whatever": {"key": "value"}},
                                    "python-version": "3.10",
                                },
                            ],
                        },
                    ),
                ],
            ),
            (
                "outer",
                [outer, top],
                [
                    RawConfig(outer, {"enable": [".localrules"], "disable": ["modernization"]}),
                    RawConfig(
                        top,
                        {
                            "root": True,
                            "enable-root-import": True,
                            "enable": ["more.rules"],
                            "disable": ["rattle.rules.something_specific"],
                            "python-version": "3.8",
                            "overrides": [
                                {
                                    "path": "other",
                                    "enable": ["other.stuff", ".globalrules"],
                                    "disable": ["modernization"],
                                    "options": {"other.stuff:whatever": {"key": "value"}},
                                    "python-version": "3.10",
                                },
                            ],
                        },
                    ),
                ],
            ),
            (
                "top",
                [top],
                [
                    RawConfig(
                        top,
                        {
                            "root": True,
                            "enable-root-import": True,
                            "enable": ["more.rules"],
                            "disable": ["rattle.rules.something_specific"],
                            "python-version": "3.8",
                            "overrides": [
                                {
                                    "path": "other",
                                    "enable": ["other.stuff", ".globalrules"],
                                    "disable": ["modernization"],
                                    "options": {"other.stuff:whatever": {"key": "value"}},
                                    "python-version": "3.10",
                                },
                            ],
                        },
                    ),
                ],
            ),
        ):
            with self.subTest(name):
                actual = config.read_configs(paths)
                assert expected == actual
