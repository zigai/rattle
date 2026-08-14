# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from unittest import TestCase

from rattle import selectors
from rattle.rule import parse_lint_ignore_comment


class SelectorTest(TestCase):
    def test_rule_option_value(self) -> None:
        for value in (
            "hello",
            1,
            1.5,
            True,
            ["TODO", "FIXME"],
            [1, 2],
            [False, True],
            {"symbol": "typing.cast", "message": "Do not call cast."},
            [{"symbol": "typing.cast"}, {"symbol": "typing_extensions.cast"}],
            {"groups": [{"name": "alpha", "enabled": True}]},
        ):
            with self.subTest(value):
                assert selectors.is_rule_option_value(value)

        for value in ({1: "value"}, [object()], {"nested": object()}):
            with self.subTest(value):
                assert not selectors.is_rule_option_value(value)

    def test_ignore_comment_regex(self) -> None:
        for value, expected_names in (
            ("# rattle: ignore", None),
            ("# rattle: ignore[fake-rule]", "fake-rule"),
            ("#rattle:ignore[fake,another-rule]", "fake,another-rule"),
            ("# rattle: ignore [fake, another, rule-name]", "fake, another, rule-name"),
        ):
            with self.subTest("match " + value):
                directive = parse_lint_ignore_comment(value)
                assert directive is not None, "value did not match rattle ignore regex"
                assert expected_names == directive.names, "regex captured unexpected names"

        for value in (
            "# something else",
            "# noqa",
            "# rattle-ignore",
            "# rattle: disable[fake-rule]",
            "# rattle: ignore FakeRule",
            "# rattle: ignore[FakeRule]",
            "# this is not a rattle ignore",
            "# rattle: fixme[fake-rule]",
        ):
            with self.subTest("no match " + value):
                assert parse_lint_ignore_comment(value) is None, (
                    "value unexpectedly matches rattle ignore regex"
                )

    def test_qualified_rule(self) -> None:
        valid: set[selectors.QualifiedRule] = set()

        for value, expected in (
            ("", None),
            ("foo-bar", None),
            ("foo/bar", None),
            ("foo", {"local": None, "module": "foo", "name": None}),
            ("foo.bar", {"local": None, "module": "foo.bar", "name": None}),
            ("foo.bar:baz-rule", {"local": None, "module": "foo.bar", "name": "baz-rule"}),
            (".foo", {"local": ".", "module": ".foo", "name": None}),
            (".foo.bar", {"local": ".", "module": ".foo.bar", "name": None}),
            (".foo.bar:baz-rule", {"local": ".", "module": ".foo.bar", "name": "baz-rule"}),
            ("..foo", None),
        ):
            with self.subTest(value):
                match = selectors.QUALIFIED_RULE_REGEX.match(value)
                if expected is not None:
                    if match is None:
                        self.fail(f"{value!r} should match QualifiedRule")
                    assert expected == match.groupdict()

                    groups = match.groupdict()
                    rule = selectors.QualifiedRule(
                        module=groups["module"],
                        name=groups["name"],
                        local=groups["local"],
                    )
                    assert expected["local"] == rule.local
                    assert expected["module"] == rule.module
                    assert expected["name"] == rule.name

                    valid.add(rule)

                else:
                    assert match is None, f"{value!r} should not match QualifiedRule"

        assert {
            selectors.QualifiedRule("foo"),
            selectors.QualifiedRule("foo.bar"),
            selectors.QualifiedRule("foo.bar", "baz-rule"),
            selectors.QualifiedRule(".foo", local="."),
            selectors.QualifiedRule(".foo.bar", local="."),
            selectors.QualifiedRule(".foo.bar", "baz-rule", local="."),
        } == valid

    def test_rule_name_selector_type(self) -> None:
        selector = selectors.RuleNameSelector("use-f-string")

        assert str(selector) == "use-f-string"
        assert selectors.RULE_NAME_SELECTOR_REGEX.fullmatch(selector.value)

    def test_tags_parser(self) -> None:
        Tags = selectors.Tags

        for value, expected in (
            (None, Tags()),
            ("", Tags()),
            ("foo", Tags(("foo",))),
            ("foo, bar", Tags(("bar", "foo"))),
            ("foo, !bar", Tags(("foo",), ("bar",))),
            ("foo, -bar, foo, glob", Tags(("foo", "glob"), ("bar",))),
            ("foo,", Tags(("foo",))),
            ("foo,,bar", Tags(("bar", "foo"))),
            (",", Tags()),
        ):
            with self.subTest(value):
                result = Tags.parse(value)
                assert expected == result

    def test_tags_bool(self) -> None:
        Tags = selectors.Tags
        for tags in (
            "hello",
            "!hello",
            "hello,world",
            "hello,^world",
        ):
            assert Tags.parse(tags)

        for tags in (
            None,
            "",
        ):
            assert not Tags.parse(tags)

    def test_tags_contains(self) -> None:
        Tags = selectors.Tags

        for value, tags in (
            ("", ""),
            ("", "!hello"),
            ("hello", ""),
            ("hello", "hello"),
            ("hello", "!world"),
            ("hello", "hello, ^world"),
            ([], ""),
            ([], "!hello"),
            (["hello", "world"], ""),
            (["hello", "world"], "hello"),
            (["hello", "world"], "world"),
            (["hello", "world"], "hello, world, blue"),
            (["hello", "world"], "hello, world, !blue"),
        ):
            with self.subTest(f"{value!r} in {tags!r}"):
                assert value in Tags.parse(tags)

        for value, tags in (
            (None, ""),
            (37, ""),
            (object(), ""),
            ("", "hello"),
            ("hello", "^hello"),
            ("hello", "!hello, world"),
            ("hello", "something, -world"),
            ([], "hello"),
            (["hello", "world"], "!hello"),
            (["hello", "world"], "!world"),
            (["hello", "world"], "!hello, world, blue"),
            (["hello", "world"], "hello, !world, blue"),
        ):
            with self.subTest(f"{value!r} not in {tags!r}"):
                assert value not in Tags.parse(tags)
