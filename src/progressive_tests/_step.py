import functools
import inspect

from ._status import Status


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
        params = inspect.signature(func).parameters
        if len(params) != 1:
            raise TypeError(
                f"@step({name!r}): step function must take exactly one "
                f"argument (the input), got {len(params)}"
            )

        @functools.wraps(func)
        def wrapper(case):
            try:
                result = func(case)
            except Exception:
                return Status.FAIL
            return result if isinstance(result, Status) else Status.FAIL

        wrapper.step_name = name
        return wrapper

    return decorator
