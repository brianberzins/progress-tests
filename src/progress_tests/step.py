import functools
import inspect
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
    step_name: str

    def __call__(self, case: Case) -> tuple[Status, dict[str, Any]]: ...


def step(name: str) -> Callable[[StepFunction], Step]:
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
            except AssertionError:
                return Status.FAIL("assert fail", detail=traceback.format_exc()), {}
            except Exception:
                return Status.FAIL("exception", detail=traceback.format_exc()), {}
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
    return Status.FAIL("invalid step return value"), {}
