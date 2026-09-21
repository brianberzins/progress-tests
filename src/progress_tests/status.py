from dataclasses import dataclass, replace
from enum import Enum, auto


class _Kind(Enum):
    PASS = auto()
    WAIT = auto()
    FAIL = auto()


@dataclass(frozen=True, eq=False)
class Status:
    """The result of evaluating one step: pass, wait, or fail, with an
    optional short `message` shown in the table cell in place of the
    default word (keep it short -- it renders inline in a fixed-width
    column) and an optional longer `detail` (e.g. a traceback) printed
    once, after the whole table.

    `Status.PASS`/`WAIT`/`FAIL` are the plain, message-less values,
    unchanged from before. Call one to attach a message:
    `Status.WAIT("waiting on backup")`. Two `Status`es compare equal
    (and hash equal) whenever their kind matches, regardless of message
    or detail -- `Status.WAIT("waiting on backup") == Status.WAIT`.
    """

    kind: _Kind
    message: str | None = None
    detail: str | None = None

    def __call__(self, message: str, detail: str | None = None) -> "Status":
        return replace(self, message=message, detail=detail)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Status) and self.kind is other.kind

    def __hash__(self) -> int:
        return hash(self.kind)

    @property
    def name(self) -> str:
        return self.kind.name


Status.PASS = Status(_Kind.PASS)
Status.WAIT = Status(_Kind.WAIT)
Status.FAIL = Status(_Kind.FAIL)
