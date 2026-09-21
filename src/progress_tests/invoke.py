from collections import Counter
from types import MappingProxyType
from typing import Any

from .render import color_enabled, render_table
from .status import Status, _Kind
from .step import Case, Step


def invoke(
    steps: list[Step],
    inputs: list[Case] | None = None,
    fail_on_wait: bool = False,
) -> None:
    step_names = _validate_steps(steps)
    if inputs is None:
        inputs = [{}]
    labels = _labels_for(inputs)
    _validate_labels(labels)

    rows: list[tuple[str, dict[str, Status]]] = []
    failing_labels: list[str] = []
    for label, case in zip(labels, inputs, strict=True):
        statuses, outcome = _evaluate(steps, case)
        rows.append((label, statuses))
        if outcome.kind == _Kind.FAIL or (outcome.kind == _Kind.WAIT and fail_on_wait):
            failing_labels.append(label)

    print(render_table(step_names, rows, use_color=color_enabled()))
    _print_details(rows)

    if failing_labels:
        raise AssertionError(
            f"{len(failing_labels)} of {len(rows)} input(s) did not pass: "
            f"{', '.join(failing_labels)} (see table above)"
        )


def _evaluate(
    steps: list[Step], original_case: Case
) -> tuple[dict[str, Status], Status]:
    case: dict[str, Any] = dict(original_case)
    statuses: dict[str, Status] = {}
    outcome = Status.PASS("no steps")
    for s in steps:
        # A step gets a read-only view of the accumulated case -- mutating
        # it directly raises (caught by @step, reported as Status.FAIL)
        # rather than silently bypassing the overwrite check in _merge.
        outcome, data = s(MappingProxyType(case))
        statuses[s.step_name] = outcome
        if outcome.kind != _Kind.PASS:
            break
        _merge(case, data, s.step_name)
    return statuses, outcome


def _print_details(rows: list[tuple[str, dict[str, Status]]]) -> None:
    # Any traceback (from an unhandled exception or a mutated-case bug --
    # see the comment in _evaluate) prints once, after the table, rather
    # than interleaved with it as it's discovered.
    for label, statuses in rows:
        for step_name, status in statuses.items():
            if status.detail:
                print(f"\n{label} / {step_name}:")
                print(status.detail, end="")


def _merge(case: dict[str, Any], data: dict[str, Any], step_name: str) -> None:
    collisions = set(case) & set(data)
    if collisions:
        raise ValueError(
            f"step {step_name!r} tried to overwrite existing data: "
            f"{', '.join(sorted(collisions))}"
        )
    case.update(data)


def _labels_for(inputs: list[Case]) -> list[str]:
    return [case.get("name", f"input[{i}]") for i, case in enumerate(inputs)]


def _validate_steps(steps: list[Step]) -> list[str]:
    names: list[str] = []
    for s in steps:
        if not hasattr(s, "step_name"):
            raise TypeError(f"{s!r} was not decorated with @step")
        names.append(s.step_name)
    _reject_duplicates(names, "step name")
    return names


def _validate_labels(labels: list[str]) -> None:
    _reject_duplicates(labels, "input name")


def _reject_duplicates(items: list[str], kind: str) -> None:
    duplicates = {item for item, count in Counter(items).items() if count > 1}
    if duplicates:
        raise ValueError(f"duplicate {kind}(s): {', '.join(sorted(duplicates))}")
