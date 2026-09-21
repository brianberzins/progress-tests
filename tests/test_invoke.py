import sys

import pytest

from progressive_tests import Status, invoke, step


def test_invoke_does_not_raise_when_the_only_step_passes():
    @step("EXISTS")
    def exists(case):
        return Status.PASS

    invoke([exists], [{"name": "instance-a"}])


def test_invoke_does_not_raise_on_wait_by_default():
    @step("EXISTS")
    def exists(case):
        return Status.WAIT

    invoke([exists], [{"name": "instance-a"}])


def test_invoke_raises_on_fail():
    @step("EXISTS")
    def exists(case):
        return Status.FAIL

    with pytest.raises(AssertionError):
        invoke([exists], [{"name": "instance-a"}])


def test_invoke_raises_on_wait_when_fail_on_wait_is_set():
    @step("EXISTS")
    def exists(case):
        return Status.WAIT

    with pytest.raises(AssertionError):
        invoke([exists], [{"name": "instance-a"}], fail_on_wait=True)


def test_invoke_defaults_to_a_single_implicit_input_when_none_given():
    seen = []

    @step("EXISTS")
    def exists(case):
        seen.append(case)
        return Status.PASS

    invoke([exists])

    assert seen == [{}]


def test_invoke_stops_at_the_first_non_passing_step_for_that_input():
    calls = []

    @step("BUCKET_EXISTS")
    def bucket_exists(case):
        calls.append("BUCKET_EXISTS")
        return Status.WAIT

    @step("DNS_CUTOVER")
    def dns_cutover(case):
        calls.append("DNS_CUTOVER")
        return Status.PASS

    invoke([bucket_exists, dns_cutover], [{"name": "instance-a"}])

    assert calls == ["BUCKET_EXISTS"]


def test_invoke_continues_past_a_passing_step_to_the_next_one():
    calls = []

    @step("BUCKET_EXISTS")
    def bucket_exists(case):
        calls.append("BUCKET_EXISTS")
        return Status.PASS

    @step("DNS_CUTOVER")
    def dns_cutover(case):
        calls.append("DNS_CUTOVER")
        return Status.WAIT

    invoke([bucket_exists, dns_cutover], [{"name": "instance-a"}])

    assert calls == ["BUCKET_EXISTS", "DNS_CUTOVER"]


def test_invoke_evaluates_each_input_independently():
    @step("READY")
    def ready(case):
        return Status.PASS if case["ready"] else Status.WAIT

    # Neither input's evaluation should affect the other's.
    invoke(
        [ready],
        [
            {"name": "instance-a", "ready": True},
            {"name": "instance-b", "ready": False},
        ],
    )


def test_invoke_raises_if_any_input_fails_even_if_others_pass():
    @step("READY")
    def ready(case):
        return Status.PASS if case["ready"] else Status.FAIL

    with pytest.raises(AssertionError, match="instance-b"):
        invoke(
            [ready],
            [
                {"name": "instance-a", "ready": True},
                {"name": "instance-b", "ready": False},
            ],
        )


def test_invoke_rejects_duplicate_step_names():
    @step("SAME_NAME")
    def first(case):
        return Status.PASS

    @step("SAME_NAME")
    def second(case):
        return Status.PASS

    with pytest.raises(ValueError, match="SAME_NAME"):
        invoke([first, second], [{"name": "instance-a"}])


def test_invoke_rejects_duplicate_input_names():
    @step("EXISTS")
    def exists(case):
        return Status.PASS

    with pytest.raises(ValueError, match="instance-a"):
        invoke(
            [exists],
            [{"name": "instance-a"}, {"name": "instance-a"}],
        )


def test_invoke_rejects_a_step_that_was_not_decorated():
    def undecorated(case):
        return Status.PASS

    with pytest.raises(TypeError):
        invoke([undecorated], [{"name": "instance-a"}])


def test_invoke_falls_back_to_positional_label_when_name_is_absent(capsys):
    @step("EXISTS")
    def exists(case):
        return Status.PASS

    invoke([exists], [{}])

    out = capsys.readouterr().out
    assert "input[0]" in out


def test_invoke_a_three_step_migration_across_inputs_at_different_stages(capsys):
    """A worked, multistage example: three inputs, each further along a
    three-step migration than the last, mirroring what a real progressive
    table test looks like once it's running in CI.
    """

    @step("BUCKET_EXISTS")
    def bucket_exists(case):
        return Status.PASS if case["stage"] >= 1 else Status.WAIT

    @step("DATA_COPIED")
    def data_copied(case):
        return Status.PASS if case["stage"] >= 2 else Status.WAIT

    @step("DNS_CUTOVER")
    def dns_cutover(case):
        return Status.PASS if case["stage"] >= 3 else Status.WAIT

    steps = [bucket_exists, data_copied, dns_cutover]
    inputs = [
        {"name": "not-started", "stage": 0},
        {"name": "in-progress", "stage": 1},
        {"name": "fully-migrated", "stage": 3},
    ]

    # No input has failed outright, only some are still waiting -- this
    # should pass by default.
    invoke(steps, inputs)

    out = capsys.readouterr().out
    lines = {line.split()[0]: line for line in out.splitlines()[1:]}
    assert lines["not-started"].count("!") == 1
    assert lines["in-progress"].count("!") == 1
    assert lines["fully-migrated"].count("+") == 3


def test_invoke_prints_a_header_naming_input_and_each_step(capsys):
    @step("BUCKET_EXISTS")
    def bucket_exists(case):
        return Status.PASS

    @step("DNS_CUTOVER")
    def dns_cutover(case):
        return Status.PASS

    invoke([bucket_exists, dns_cutover], [{"name": "instance-a"}])

    header = capsys.readouterr().out.splitlines()[0]
    assert "NAME" in header
    assert "BUCKET_EXISTS" in header
    assert "DNS_CUTOVER" in header


def test_invoke_shows_the_fail_glyph_for_a_failed_step(capsys):
    @step("CHECK")
    def check(case):
        return Status.FAIL

    with pytest.raises(AssertionError):
        invoke([check], [{"name": "instance-a"}])

    assert "X" in capsys.readouterr().out


def test_invoke_leaves_unreached_steps_blank_not_passing_or_failing(capsys):
    @step("BUCKET_EXISTS")
    def bucket_exists(case):
        return Status.WAIT

    @step("DNS_CUTOVER")
    def dns_cutover(case):
        return Status.PASS

    invoke([bucket_exists, dns_cutover], [{"name": "instance-a"}])

    row = capsys.readouterr().out.splitlines()[1]
    assert "!" in row
    assert "+" not in row
    assert "X" not in row


def test_invoke_output_has_no_ansi_codes_when_stdout_is_not_a_tty(capsys, monkeypatch):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)

    @step("EXISTS")
    def exists(case):
        return Status.PASS

    invoke([exists], [{"name": "instance-a"}])

    assert "\033[" not in capsys.readouterr().out


def test_invoke_output_has_ansi_codes_when_color_is_enabled(capsys, monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    @step("EXISTS")
    def exists(case):
        return Status.PASS

    invoke([exists], [{"name": "instance-a"}])

    assert "\033[" in capsys.readouterr().out


def test_invoke_output_has_no_ansi_codes_when_no_color_is_set(capsys, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    @step("EXISTS")
    def exists(case):
        return Status.PASS

    invoke([exists], [{"name": "instance-a"}])

    assert "\033[" not in capsys.readouterr().out


def test_invoke_output_has_no_ansi_codes_when_ci_env_var_is_set(capsys, monkeypatch):
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    @step("EXISTS")
    def exists(case):
        return Status.PASS

    invoke([exists], [{"name": "instance-a"}])

    assert "\033[" not in capsys.readouterr().out


def test_invoke_passes_data_from_one_step_to_the_next():
    seen_ids = []

    @step("CREATE_DISTRIBUTION")
    def create_distribution(case):
        return Status.PASS, {"distribution_id": "E123"}

    @step("VERIFY_DEPLOYED")
    def verify_deployed(case):
        seen_ids.append(case["distribution_id"])
        return Status.PASS

    invoke([create_distribution, verify_deployed], [{"name": "instance-a"}])

    assert seen_ids == ["E123"]


def test_invoke_does_not_mutate_the_original_input_dict():
    @step("CREATE_DISTRIBUTION")
    def create_distribution(case):
        return Status.PASS, {"distribution_id": "E123"}

    original = {"name": "instance-a"}
    invoke([create_distribution], [original])

    assert original == {"name": "instance-a"}


def test_invoke_raises_when_a_step_tries_to_overwrite_an_input_field():
    @step("RENAME")
    def rename(case):
        return Status.PASS, {"name": "something-else"}

    with pytest.raises(ValueError, match="name"):
        invoke([rename], [{"name": "instance-a"}])


def test_invoke_raises_when_two_steps_both_set_the_same_key():
    @step("FIRST")
    def first(case):
        return Status.PASS, {"key": "value-from-first"}

    @step("SECOND")
    def second(case):
        return Status.PASS, {"key": "value-from-second"}

    with pytest.raises(ValueError, match="key"):
        invoke([first, second], [{"name": "instance-a"}])


def test_invoke_reports_fail_when_a_step_mutates_case_directly(capsys):
    """A step is only meant to pass data forward via its return value,
    checked by _merge for collisions. Mutating the case it was given
    bypasses that check entirely -- this must not silently succeed."""

    @step("SNEAKY")
    def sneaky(case):
        case["key"] = "mutated directly, not returned"
        return Status.PASS

    with pytest.raises(AssertionError):
        invoke([sneaky], [{"name": "instance-a"}])

    assert "X" in capsys.readouterr().out
