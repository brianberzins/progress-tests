import os
import sys

from .status import Status, _Kind

_GLYPH: dict[_Kind, str] = {_Kind.PASS: "+", _Kind.WAIT: "!", _Kind.FAIL: "X"}
_COLOR: dict[_Kind, str] = {
    _Kind.PASS: "\033[32m",
    _Kind.WAIT: "\033[33m",
    _Kind.FAIL: "\033[31m",
}
_RESET = "\033[0m"
_GUTTER = "  "


def color_enabled() -> bool:
    if os.environ.get("NO_COLOR") or os.environ.get("CI"):
        return False
    return sys.stdout.isatty()


def render_table(
    step_names: list[str],
    rows: list[tuple[str, dict[str, Status]]],
    use_color: bool,
) -> str:
    label_width = max((len(label) for label, _ in rows), default=len("NAME"))
    column_widths = {name: len(name) for name in step_names}
    for _, statuses in rows:
        for name in step_names:
            status = statuses.get(name)
            if status is not None:
                column_widths[name] = max(column_widths[name], len(_cell_text(status)))

    header = f"{'NAME':<{label_width}}"
    for name in step_names:
        header += _GUTTER + f"{name:<{column_widths[name]}}"
    lines = [header]

    for label, statuses in rows:
        line = f"{label:<{label_width}}"
        for name in step_names:
            width = column_widths[name]
            status = statuses.get(name)
            line += _GUTTER + _render_cell(status, width, use_color)
        lines.append(line)

    return "\n".join(lines)


def _cell_text(status: Status) -> str:
    if not status.message:
        return _GLYPH[status.kind]
    return f"{_GLYPH[status.kind]} {status.message}"


def _render_cell(status: Status | None, width: int, use_color: bool) -> str:
    if status is None:
        return " " * width
    text = f"{_cell_text(status):<{width}}"
    if not use_color:
        return text
    return f"{_COLOR[status.kind]}{text}{_RESET}"
