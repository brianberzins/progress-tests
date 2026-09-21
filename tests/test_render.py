from progressive_tests import Status
from progressive_tests._render import render_table


def test_render_table_header_lists_input_and_each_step_name():
    table = render_table(["BUCKET_EXISTS", "DNS_CUTOVER"], [], use_color=False)

    header = table.splitlines()[0]
    assert "INPUT" in header
    assert "BUCKET_EXISTS" in header
    assert "DNS_CUTOVER" in header


def test_render_table_shows_the_right_glyph_per_status():
    rows = [("instance-a", {"STEP": Status.PASS})]
    assert "✓" in render_table(["STEP"], rows, use_color=False)

    rows = [("instance-a", {"STEP": Status.WAIT})]
    assert "!" in render_table(["STEP"], rows, use_color=False)

    rows = [("instance-a", {"STEP": Status.FAIL})]
    assert "✗" in render_table(["STEP"], rows, use_color=False)


def test_render_table_leaves_unreached_steps_blank():
    # Only the first step was evaluated for this input (it didn't pass).
    rows = [("instance-a", {"BUCKET_EXISTS": Status.WAIT})]

    table = render_table(["BUCKET_EXISTS", "DNS_CUTOVER"], rows, use_color=False)

    row = table.splitlines()[1]
    assert "!" in row
    assert "✓" not in row
    assert "✗" not in row


def test_render_table_without_color_has_no_ansi_codes():
    rows = [("instance-a", {"STEP": Status.PASS})]
    table = render_table(["STEP"], rows, use_color=False)

    assert "\033[" not in table


def test_render_table_with_color_wraps_cells_in_ansi_codes():
    rows = [("instance-a", {"STEP": Status.PASS})]
    table = render_table(["STEP"], rows, use_color=True)

    assert "\033[" in table
