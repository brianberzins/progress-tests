from dataclasses import dataclass
from enum import Enum, auto


class _Kind(Enum):
    PASS = auto()
    WAIT = auto()
    FAIL = auto()


@dataclass(frozen=True)
class Status:
    kind: _Kind
    message: str
    detail: str | None = None

    @classmethod
    def PASS(cls, message: str, detail: str | None = None) -> "Status":
        return cls(_Kind.PASS, message, detail)

    @classmethod
    def WAIT(cls, message: str, detail: str | None = None) -> "Status":
        return cls(_Kind.WAIT, message, detail)

    @classmethod
    def FAIL(cls, message: str, detail: str | None = None) -> "Status":
        return cls(_Kind.FAIL, message, detail)
