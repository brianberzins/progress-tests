import functools
import inspect
import sys
import traceback
from collections.abc import Callable, Mapping
from typing import Any, Protocol

from .status import Status

Case = Mapping[str, Any]
StepResult = Status | tuple[Status, dict[str, Any]]
StepFunction = Callable[[Case], StepResult]

_POSITIONAL_KINDS = (
    inspect.Parameter.POSITIONAL_ONLY,
    inspect.Parameter.POSITIONAL_OR_KEYWORD,
    inspect.Parameter.VAR_POSITIONAL,
)


class Step(Protocol):
    """A function decorated with `@step`: callable with a read-only
    `case`, and carrying the `step_name` it was registered under."""

    step_name: str

    def __call__(self, case: Case) -> tuple[Status, dict[str, Any]]: ...


def step(name: str) -> Callable[[StepFunction], Step]:
    """Decorate a function as one progressive-test step named `name`.

    The wrapped function must take exactly one positional argument (the
    input, a read-only mapping) and is expected to return a `Status`,
    optionally paired with a `dict` of data to make available to later
    steps for this input, e.g. `return Status.PASS, {"key": value}`.
    Mutating `case` directly has no effect on later steps and is not
    how a step is meant to pass data forward — see `invoke()`.

    Any exception raised, or any return value that isn't one of those
    two shapes, is reported as `Status.FAIL` (with no data) rather than
    propagating or defaulting to anything else — an unimplemented or
    broken check is always a failure, never a silent "not done yet".
    """

    def decorator(func: StepFunction) -> Step:
        params = list(inspect.signature(func).parameters.values())
        if len(params) != 1 or params[0].kind not in _POSITIONAL_KINDS:
            raise TypeError(
                f"@step({name!r}): step function must take exactly one "
                f"positional argument (the input)"
            )

        @functools.wraps(func)
        def wrapper(case: Case) -> tuple[Status, dict[str, Any]]:
            try:
                result = func(case)
            except Exception:
                traceback.print_exc(file=sys.stderr)
                return Status.FAIL, {}
            return _normalize(result)

        wrapper.step_name = name  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator


def _normalize(result: StepResult) -> tuple[Status, dict[str, Any]]:
    if isinstance(result, Status):
        return result, {}
    if (
        isinstance(result, tuple)
        and len(result) == 2
        and isinstance(result[0], Status)
        and isinstance(result[1], dict)
    ):
        return result
    return Status.FAIL, {}
