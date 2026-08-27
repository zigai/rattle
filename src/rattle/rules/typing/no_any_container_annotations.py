from rattle.rule import Invalid, Valid
from rattle.rules.typing import _container_annotations


class NoAnyContainerAnnotations(_container_annotations.ContainerAnnotationRule):
    """Disallow ``Any`` in the semantic type arguments of standard containers."""

    MESSAGE = (
        "Replace `Any` in this container annotation with concrete element, key, or value types."
    )
    TARGET = "typing.Any"

    VALID = [
        Valid(
            """
            from typing import Any

            class Envelope:
                pass

            payload: Envelope[Any]
            rows: list[dict[str, int]]
            """
        ),
        Valid(
            """
            class Any:
                pass

            values: list[Any]
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            from typing import Any

            values: list[Any]
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            import typing as t

            rows: t.Mapping[str, t.Sequence[t.Any]]
            """,
            expected_message=MESSAGE,
        ),
    ]
