from enum import Enum, auto


class Status(Enum):
    """The result of evaluating one step: pass, wait, or fail."""

    PASS = auto()
    WAIT = auto()
    FAIL = auto()
