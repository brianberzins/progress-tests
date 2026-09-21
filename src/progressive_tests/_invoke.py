from ._render import color_enabled, render_table
from ._status import Status


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
    _validate_steps(steps)
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

    step_names = [s.step_name for s in steps]
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
    names = [_step_name_of(s) for s in steps]
    duplicates = {name for name in names if names.count(name) > 1}
    if duplicates:
        raise ValueError(f"duplicate step name(s): {', '.join(sorted(duplicates))}")


def _step_name_of(s):
    if not hasattr(s, "step_name"):
        raise TypeError(f"{s!r} was not decorated with @step")
    return s.step_name


def _validate_labels(labels):
    duplicates = {label for label in labels if labels.count(label) > 1}
    if duplicates:
        raise ValueError(f"duplicate input name(s): {', '.join(sorted(duplicates))}")
