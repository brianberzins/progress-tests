import functools
import inspect
import sys
import traceback

from ._status import Status

_POSITIONAL_KINDS = (
    inspect.Parameter.POSITIONAL_ONLY,
    inspect.Parameter.POSITIONAL_OR_KEYWORD,
    inspect.Parameter.VAR_POSITIONAL,
)


def step(name):
    """Decorate a function as one progressive-test step named `name`.

    The wrapped function must take exactly one positional argument (the
    input) and is expected to return a `Status`. Any exception raised,
    or any return value that isn't a `Status`, is reported as
    `Status.FAIL` rather than propagating or defaulting to anything
    else — an unimplemented or broken check is always a failure, never
    a silent "not done yet".
    """

    def decorator(func):
        params = list(inspect.signature(func).parameters.values())
        if len(params) != 1 or params[0].kind not in _POSITIONAL_KINDS:
            raise TypeError(
                f"@step({name!r}): step function must take exactly one "
                f"positional argument (the input)"
            )

        @functools.wraps(func)
        def wrapper(case):
            try:
                result = func(case)
            except Exception:
                traceback.print_exc(file=sys.stderr)
                return Status.FAIL
            return result if isinstance(result, Status) else Status.FAIL

        wrapper.step_name = name
        return wrapper

    return decorator
