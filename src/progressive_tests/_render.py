import os
import sys

from ._status import Status

_GLYPH = {Status.PASS: "✓", Status.WAIT: "!", Status.FAIL: "✗"}
_COLOR = {Status.PASS: "\033[32m", Status.WAIT: "\033[33m", Status.FAIL: "\033[31m"}
_RESET = "\033[0m"


def color_enabled():
    if os.environ.get("NO_COLOR") or os.environ.get("CI"):
        return False
    return sys.stdout.isatty()


def render_table(step_names, rows, use_color):
    label_width = max([len("INPUT")] + [len(label) for label, _ in rows])
    column_widths = {name: max(len(name), len("pass")) for name in step_names}

    header = f"{'INPUT':<{label_width}}"
    for name in step_names:
        header += f"  {name:<{column_widths[name]}}"
    lines = [header]

    for label, statuses in rows:
        line = f"{label:<{label_width}}"
        for name in step_names:
            width = column_widths[name]
            status = statuses.get(name)
            line += "  " + _render_cell(status, width, use_color)
        lines.append(line)

    return "\n".join(lines)


def _render_cell(status, width, use_color):
    if status is None:
        return " " * width
    text = f"{_GLYPH[status]} {status.name.lower():<{width - 2}}"
    if not use_color:
        return text
    return f"{_COLOR[status]}{text}{_RESET}"
