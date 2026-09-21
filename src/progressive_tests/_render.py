import os
import sys

from ._status import Status

_GLYPH = {Status.PASS: "✓", Status.WAIT: "!", Status.FAIL: "✗"}
_COLOR = {Status.PASS: "\033[32m", Status.WAIT: "\033[33m", Status.FAIL: "\033[31m"}
_RESET = "\033[0m"
_GUTTER = "  "
_CELL_PREFIX_WIDTH = len("✓ ")  # every cell is one glyph, then a space, then the word


def color_enabled():
    if os.environ.get("NO_COLOR") or os.environ.get("CI"):
        return False
    return sys.stdout.isatty()


def render_table(step_names, rows, use_color):
    status_word_width = max(len(s.name) for s in Status)
    label_width = max((len(label) for label, _ in rows), default=len("INPUT"))
    column_widths = {name: max(len(name), status_word_width) for name in step_names}

    header = f"{'INPUT':<{label_width}}"
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


def _render_cell(status, width, use_color):
    if status is None:
        return " " * width
    text = f"{_GLYPH[status]} {status.name.lower():<{width - _CELL_PREFIX_WIDTH}}"
    if not use_color:
        return text
    return f"{_COLOR[status]}{text}{_RESET}"
