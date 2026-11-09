"""Render docs/demo/progress.gif from the example's own steps.

Run from the repo root: uv run --with pillow python docs/demo/render.py

Copies example/test_pipeline.py with three apps as its inputs, advances
each app's data file one rollout stage per frame (apps start one stage
apart), runs the real progress-tests runner for each frame, and draws
its colored output. Needs macOS for the Menlo font.
"""

import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).with_name("progress.gif")
APPS = ["app-a", "app-b", "app-c"]
STAGES = [
    None,
    "version=1\ninstances=1,1,1\nhealthy=false\n",
    "version=3\ninstances=1,1,1\nhealthy=false\n",
    "version=3\ninstances=3,1,1\nhealthy=true\n",
    "version=3\ninstances=3,3,1\nhealthy=true\n",
    "version=3\ninstances=3,3,3\nhealthy=true\n",
]
FONT = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 16)
COLORS = {"0": "#d4d4d4", "32": "#6ac36a", "33": "#e5c07b", "31": "#e06c75"}
BACKGROUND = "#1e1e1e"
LINE_HEIGHT = 22
PADDING = 20
FRAME_MS = 1400
LAST_FRAME_MS = 3500
ANSI = re.compile(r"\033\[(\d+)m")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        demo = Path(tmp) / "example"
        (demo / "files").mkdir(parents=True)
        (demo / "test_pipeline.py").write_text(_with_apps_as_inputs())
        outputs = [
            _run_frame(demo, frame) for frame in range(len(STAGES) + len(APPS) - 1)
        ]
    _save_gif([_draw(output, _size(outputs)) for output in outputs])
    print(OUTPUT.relative_to(REPO))


def _with_apps_as_inputs() -> str:
    source = (REPO / "example" / "test_pipeline.py").read_text()
    inputs = ", ".join(f'{{"name": "{app}"}}' for app in APPS)
    source, count = re.subn(
        r"inputs = \[.*?\]\n", f"inputs = [{inputs}]\n", source, flags=re.S
    )
    if count != 1:
        raise SystemExit("expected exactly one inputs list in the example")
    return source


def _run_frame(demo: Path, frame: int) -> str:
    for offset, app in enumerate(APPS):
        stage = STAGES[max(0, min(frame - offset, len(STAGES) - 1))]
        path = demo / "files" / f"{app}.txt"
        path.unlink(missing_ok=True)
        if stage:
            path.write_text(stage)
    result = subprocess.run(
        ["uv", "run", "progress-tests", str(demo)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return "$ progress-tests example\n" + result.stdout.rstrip("\n")


def _size(outputs: list[str]) -> tuple[int, int]:
    lines = [line for output in outputs for line in output.splitlines()]
    columns = max(len(ANSI.sub("", line)) for line in lines)
    rows = max(len(output.splitlines()) for output in outputs)
    char_width = FONT.getlength("M")
    return int(columns * char_width) + 2 * PADDING, rows * LINE_HEIGHT + 2 * PADDING


def _draw(output: str, size: tuple[int, int]) -> Image.Image:
    image = Image.new("RGB", size, BACKGROUND)
    draw = ImageDraw.Draw(image)
    char_width = FONT.getlength("M")
    for row, line in enumerate(output.splitlines()):
        column, color = 0, COLORS["0"]
        for index, part in enumerate(ANSI.split(line)):
            if index % 2:
                color = COLORS.get(part, COLORS["0"])
                continue
            xy = (PADDING + column * char_width, PADDING + row * LINE_HEIGHT)
            draw.text(xy, part, font=FONT, fill=color)
            column += len(part)
    return image


def _save_gif(frames: list[Image.Image]) -> None:
    durations = [FRAME_MS] * (len(frames) - 1) + [LAST_FRAME_MS]
    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
    )


if __name__ == "__main__":
    main()
