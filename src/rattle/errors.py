class RattleError(Exception):
    """Base exception for safe Rattle runtime failures."""


class RattleExecutionError(RattleError):
    """Sanitized failure from an operation that cannot expose exception details."""

    def __init__(self, operation: str, error_type: str) -> None:
        self.operation = operation
        self.error_type = error_type
        super().__init__(f"{operation} failed ({error_type})")


class RattleFormatterError(RattleError):
    """Raised when an installed formatter cannot process source code."""


class RattleRuleExecutionError(RattleError):
    """Sanitized failure raised by a custom lint rule."""

    def __init__(self, error_type: str) -> None:
        self.error_type = error_type
        super().__init__(f"Lint rule failed ({error_type})")


__all__ = [
    "RattleError",
    "RattleExecutionError",
    "RattleFormatterError",
    "RattleRuleExecutionError",
]
