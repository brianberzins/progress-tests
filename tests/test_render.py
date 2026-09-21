from progress_tests.render import render_table
from progress_tests.status import Status


def test_render_table_aligns_columns_when_step_names_are_shorter_than_a_status_word():
    table = render_table(
        ["ABCD"],
        [("instance-a", {"ABCD": Status.WAIT("wait")})],
        use_color=False,
    )

    header, row = table.splitlines()
    assert len(header) == len(row)


def test_render_table_aligns_multiple_short_columns():
    table = render_table(
        ["ABCD", "EFG"],
        [
            ("instance-a", {"ABCD": Status.PASS("ok"), "EFG": Status.WAIT("wait")}),
            ("instance-b", {"ABCD": Status.WAIT("wait")}),
        ],
        use_color=False,
    )

    lines = table.splitlines()
    assert len({len(line) for line in lines}) == 1


def test_render_table_shows_the_message():
    table = render_table(
        ["CHECK"],
        [("instance-a", {"CHECK": Status.WAIT("waiting on backup")})],
        use_color=False,
    )

    assert "! waiting on backup" in table


def test_render_table_widens_a_column_to_fit_a_long_message():
    table = render_table(
        ["CHECK"],
        [
            ("short-row", {"CHECK": Status.PASS("ok")}),
            ("longer-row", {"CHECK": Status.WAIT("a fairly long status message")}),
        ],
        use_color=False,
    )

    lines = table.splitlines()
    assert len({len(line) for line in lines}) == 1
    assert "a fairly long status message" in table


def test_render_table_colors_a_message_the_same_as_its_status():
    table = render_table(
        ["CHECK"],
        [("instance-a", {"CHECK": Status.FAIL("boom")})],
        use_color=True,
    )

    assert "\033[31mX boom" in table
