from collections import Counter

from .render import color_enabled, render_table
from .status import Status


def invoke(steps, inputs=None, fail_on_wait=False):
    """Run `steps`, in order, against each input in `inputs`.

    Each input is evaluated independently: steps run in order until one
    doesn't return `Status.PASS` (that input's frontier step), and any
    steps after it are left blank for that input rather than evaluated.

    Renders a single color-coded table (one row per input, one column
    per step) to stdout, then raises `AssertionError` if any input's
    frontier step is `Status.FAIL`, or `Status.WAIT` when
    `fail_on_wait=True`.
    """
    step_names = _validate_steps(steps)
    if inputs is None:
        inputs = [{}]
    labels = _labels_for(inputs)
    _validate_labels(labels)

    rows = []
    failing_labels = []
    for label, case in zip(labels, inputs, strict=True):
        statuses, frontier = _evaluate(steps, case)
        rows.append((label, statuses))
        if frontier is Status.FAIL or (frontier is Status.WAIT and fail_on_wait):
            failing_labels.append(label)

    print(render_table(step_names, rows, use_color=color_enabled()))

    if failing_labels:
        raise AssertionError(
            f"{len(failing_labels)} of {len(rows)} input(s) did not pass: "
            f"{', '.join(failing_labels)} (see table above)"
        )


def _evaluate(steps, case):
    statuses = {}
    frontier = Status.PASS
    for s in steps:
        frontier = s(case)
        statuses[s.step_name] = frontier
        if frontier is not Status.PASS:
            break
    return statuses, frontier


def _labels_for(inputs):
    return [case.get("name", f"input[{i}]") for i, case in enumerate(inputs)]


def _validate_steps(steps):
    names = []
    for s in steps:
        if not hasattr(s, "step_name"):
            raise TypeError(f"{s!r} was not decorated with @step")
        names.append(s.step_name)
    _reject_duplicates(names, "step name")
    return names


def _validate_labels(labels):
    _reject_duplicates(labels, "input name")


def _reject_duplicates(items, kind):
    duplicates = {item for item, count in Counter(items).items() if count > 1}
    if duplicates:
        raise ValueError(f"duplicate {kind}(s): {', '.join(sorted(duplicates))}")
