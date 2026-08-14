# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase

import pytest

from rattle import config


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

    def test_invalid_config(self) -> None:
        with self.subTest("inner enable-root-import"):
            (self.tdp / "pyproject.toml").write_text("[tool.rattle]\nroot = true\n")
            (self.tdp / "outer" / "pyproject.toml").write_text(
                "[tool.rattle]\nenable-root-import = true\n"
            )

            with pytest.raises(config.ConfigError, match="enable-root-import"):
                config.generate_config(self.tdp / "outer" / "foo.py")

        with self.subTest("inner output-format"):
            (self.tdp / "pyproject.toml").write_text("[tool.rattle]\nroot = true\n")
            (self.tdp / "outer" / "pyproject.toml").write_text(
                "[tool.rattle]\noutput-format = 'this is some weird format'\n"
            )

            with pytest.raises(
                config.ConfigError,
                match=r"unknown value 'this is some weird format'",
            ):
                config.generate_config(self.tdp / "outer" / "foo.py")

        with self.subTest("options require concrete rule"):
            (self.tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    root = true

                    [tool.rattle.options]
                    "rattle.rules" = {foo = 1}
                    """
                )
            )

            with pytest.raises(config.ConfigError, match="module:rule-name"):
                config.generate_config(self.tdp / "foo.py")

        with self.subTest("options support structured values"):
            (self.tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    root = true

                    [tool.rattle.options]
                    "rattle.rules.legacy:use-f-string" = { structured_entries = [{symbol = "typing.cast", message = "Avoid cast."}] }
                    """
                )
            )

            actual = config.generate_config(self.tdp / "foo.py")
            assert actual.options["rattle.rules.legacy:use-f-string"]["structured_entries"] == [
                {"symbol": "typing.cast", "message": "Avoid cast."}
            ]

        with self.subTest("options value must be TOML-shaped"):
            (self.tdp / "pyproject.toml").write_text(
                dedent(
                    """
                    [tool.rattle]
                    root = true

                    [tool.rattle.options]
                    "rattle.rules.legacy:use-f-string" = { simple_expression_max_length = 1979-05-27 }
                    """
                )
            )

            with pytest.raises(config.ConfigError, match="TOML scalar, array, or table"):
                config.generate_config(self.tdp / "foo.py")

    def test_validate_config(self) -> None:
        with self.subTest("validate-config valid"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                    [tool.rattle]
                    disable = ["modernization"]
                    root = true
                    """
            )

            results = config.validate_config(path)

            assert results == []

        with self.subTest("validate-config valid with options"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                    [tool.rattle]
                    root = true

                    [tool.rattle.options]
                    "rattle.rules.legacy.use_fstring:use-f-string" = {simple_expression_max_length = 42}
                    """
            )

            results = config.validate_config(path)

            assert results == []

        with (
            self.subTest("validate-config valid with structured options"),
            TemporaryDirectory() as td,
        ):
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            (tdp / "structured_rule.py").write_text(
                dedent(
                    """
                from rattle import LintRule, RuleSetting

                class StructuredRule(LintRule):
                    SETTINGS = {
                        "entries": RuleSetting(list[dict[str, str]], default=[]),
                    }
                """
                )
            )
            path.write_text(
                """
                [tool.rattle]
                root = true
                enable = [".structured_rule:structured-rule"]

                [tool.rattle.options.".structured_rule:structured-rule"]
                entries = [
                    {symbol = "typing.cast", message = "Avoid cast."},
                    {symbol = "typing_extensions.cast", message = "Avoid cast."},
                ]
                """
            )

            results = config.validate_config(path)

            assert results == []

        with self.subTest("validate-config valid with rule names"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true
                enable = ["use-f-string"]
                disable = ["no-static-if-condition"]
                per-file-enable = {"tests/**/*.py" = ["use-f-string"]}

                [tool.rattle.options]
                "use-f-string" = {simple_expression_max_length = 64}
                """
            )

            results = config.validate_config(path)

            assert results == []

        with self.subTest("validate-config invalid options key"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true

                [tool.rattle.options]
                "rattle.rules" = {simple_expression_max_length = 42}
                """
            )

            results = config.validate_config(path)

            assert any("Failed to parse options for global options" in result for result in results)

        with (
            self.subTest("validate-config invalid options unknown rule name"),
            TemporaryDirectory() as td,
        ):
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true

                [tool.rattle.options]
                "definitely-missing-rule" = {simple_expression_max_length = 42}
                """
            )

            results = config.validate_config(path)

            assert any(
                "could not find rule definitely-missing-rule" in result for result in results
            )

        with self.subTest("validate-config invalid options value"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true

                [tool.rattle.options]
                "rattle.rules.legacy.use_fstring:use-f-string" = {simple_expression_max_length = "long"}
                """
            )

            results = config.validate_config(path)

            assert any(
                "Failed to validate options for `rattle.rules.legacy.use_fstring:use-f-string`"
                in result
                for result in results
            )

        with self.subTest("validate-config invalid unknown rule name"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true
                enable = ["definitely-missing-rule"]
                """
            )

            results = config.validate_config(path)

            assert results == [
                "Failed to import rule `definitely-missing-rule` for global enable: CollectionError: could not find rule definitely-missing-rule"
            ]

        with self.subTest("validate-config valid with per-file tables"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true
                per-file-enable = {"tests/**/*.py" = ["rattle.rules.legacy:use-f-string"]}
                per-file-disable = {"tests/generated.py" = ["rattle.rules.legacy:use-f-string"]}
                """
            )

            results = config.validate_config(path)

            assert results == []

        with self.subTest("validate-config invalid per-file table"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true
                per-file-enable = {"tests/**/*.py" = "rattle.rules.legacy:use-f-string"}
                """
            )

            results = config.validate_config(path)

            assert results == [
                (
                    "Invalid config: ConfigError: Invalid 'tool.rattle' configuration: "
                    "Expected `array`, got `str` - at `$.per-file-enable[...]`"
                )
            ]

        with self.subTest("validate-config invalid inherit-ruff-files"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true
                inherit-ruff-files = "yes"
                """
            )

            results = config.validate_config(path)

            assert results == [
                (
                    "Invalid config: ConfigError: Invalid 'tool.rattle' configuration: "
                    "Expected `bool`, got `str` - at `$.inherit-ruff-files`"
                )
            ]

        with self.subTest("validate-config invalid exclude"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true
                exclude = "build"
                """
            )

            results = config.validate_config(path)

            assert results == [
                (
                    "Invalid config: ConfigError: Invalid 'tool.rattle' configuration: "
                    "Expected `array`, got `str` - at `$.exclude`"
                )
            ]

        with self.subTest("validate-config invalid output template"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true
                output-template = 42
                """
            )

            results = config.validate_config(path)

            assert results == [
                (
                    "Invalid config: ConfigError: Invalid 'tool.rattle' configuration: "
                    "Expected `str | null`, got `int` - at `$.output-template`"
                )
            ]

    def test_validate_config_with_override(self) -> None:
        with self.subTest("validate-config valid with overrides"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            (tdp / "rule/ruledir").mkdir(parents=True, exist_ok=True)

            (tdp / "rule/rule.py").write_text("# Rule")
            (tdp / "rule/ruledir/rule.py").write_text("# Rule")
            path.write_text(
                """
                [tool.rattle]
                disable = ["modernization"]
                root = true

                [[tool.rattle.overrides]]
                path = "SUPER_REAL_PATH"
                enable = [".rule.rule"]

                [[tool.rattle.overrides]]
                path = "SUPER_REAL_PATH/BUT_ACTUALLY_REAL"
                enable = [".rule.ruledir.rule"]
                """
            )

            results = config.validate_config(path)

            assert results == []

        with self.subTest("validate-config valid override options"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true

                [[tool.rattle.overrides]]
                path = "SUPER_REAL_PATH"

                [tool.rattle.overrides.options."rattle.rules.legacy.use_fstring:use-f-string"]
                simple_expression_max_length = 52
                """
            )

            results = config.validate_config(path)

            assert results == []

        with (
            self.subTest("validate-config valid override options legacy table"),
            TemporaryDirectory() as td,
        ):
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                root = true

                [[tool.rattle.overrides]]
                path = "SUPER_REAL_PATH"

                [[tool.rattle.overrides.options]]
                "rattle.rules.legacy.use_fstring:use-f-string" = {simple_expression_max_length = 52}
                """
            )

            results = config.validate_config(path)

            assert results == []

        with self.subTest("validate-config invalid config"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            path = tdp / "pyproject.toml"
            path.write_text(
                """
                [tool.rattle]
                enable = ["rattle/rules:use-collections-abc"]
                disable = ["modernization"]
                root = true
                """
            )

            results = config.validate_config(path)

            assert results == [
                "Failed to parse rule `rattle/rules:use-collections-abc` for global enable: ConfigError: invalid rule name 'rattle/rules:use-collections-abc'"
            ]

        with self.subTest("validate-config multiple errors"), TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            config_path = tdp / "pyproject.toml"
            config_path.write_text(
                """
                [tool.rattle]
                enable = ["rattle/rules:use-collections-abc"]
                disable = ["modernization"]
                root = true

                [[tool.rattle.overrides]]
                path = "SUPER_REAL_PATH"
                enable = ["rattle.rules.legacy:use-collections-abc-super-real"]
                """
            )

            path = tdp / "file.py"
            path.write_text("error")

            results = config.validate_config(config_path)

            assert results == [
                "Failed to parse rule `rattle/rules:use-collections-abc` for global enable: ConfigError: invalid rule name 'rattle/rules:use-collections-abc'",
                "Failed to import rule `rattle.rules.legacy:use-collections-abc-super-real` for override enable: `SUPER_REAL_PATH`: CollectionError: could not find rule rattle.rules.legacy:use-collections-abc-super-real",
            ]
