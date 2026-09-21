import pytest

from progress_tests import Status, step


def test_step_returns_the_underlying_status_with_no_data():
    @step("ALWAYS_PASS")
    def always_pass(case):
        return Status.PASS("ok")

    assert always_pass({}) == (Status.PASS("ok"), {})


def test_step_records_its_name():
    @step("BUCKET_EXISTS")
    def bucket_exists(case):
        return Status.PASS("ok")

    assert bucket_exists.step_name == "BUCKET_EXISTS"


def test_step_turns_a_non_status_return_into_fail():
    @step("FORGOT_TO_RETURN_STATUS")
    def broken(case):
        return "pass"  # a plain string, not Status.PASS(...)

    assert broken({}) == (Status.FAIL("invalid step return value"), {})


def test_step_labels_an_invalid_return_value_with_a_short_message():
    @step("FORGOT_TO_RETURN_STATUS")
    def broken(case):
        return "pass"

    status, _ = broken({})

    assert status.message == "invalid step return value"


def test_step_turns_a_raised_exception_into_fail():
    @step("EXPLODES")
    def broken(case):
        raise RuntimeError("simulated failure for this test")

    status, data = broken({})

    assert status.message == "exception"
    assert data == {}


def test_step_labels_a_raised_exception_with_a_short_message_and_a_traceback():
    @step("EXPLODES")
    def broken(case):
        raise RuntimeError("simulated failure for this test")

    status, _ = broken({})

    assert status.message == "exception"
    assert "RuntimeError" in status.detail
    assert "simulated failure for this test" in status.detail


def test_step_labels_a_failed_assertion_distinctly_from_other_exceptions():
    @step("ASSERTS")
    def broken(case):
        assert 1 == 2, "the real condition"

    status, _ = broken({})

    assert status.message == "assert fail"
    assert "the real condition" in status.detail


def test_step_turns_an_unimplemented_check_into_fail_not_wait():
    @step("NOT_BUILT_YET")
    def not_built_yet(case):
        raise NotImplementedError

    status, _ = not_built_yet({})

    assert status.message == "exception"


def test_step_rejects_a_function_with_no_arguments_at_decoration_time():
    with pytest.raises(TypeError):

        @step("BAD_SHAPE")
        def no_args():
            return Status.PASS("ok")


def test_step_rejects_a_function_with_two_arguments_at_decoration_time():
    with pytest.raises(TypeError):

        @step("BAD_SHAPE")
        def two_args(case, extra):
            return Status.PASS("ok")


def test_step_can_return_data_alongside_its_status():
    @step("CREATE_DISTRIBUTION")
    def create_distribution(case):
        return Status.PASS("ok"), {"distribution_id": "E123"}

    assert create_distribution({}) == (
        Status.PASS("ok"),
        {"distribution_id": "E123"},
    )


def test_step_returning_a_non_dict_as_the_data_half_is_fail():
    @step("BAD_DATA")
    def bad_data(case):
        return Status.PASS("ok"), "not-a-dict"

    assert bad_data({}) == (Status.FAIL("invalid step return value"), {})


def test_step_returning_a_wrong_sized_tuple_is_fail():
    @step("BAD_SHAPE")
    def bad_shape(case):
        return (Status.PASS("ok"),)

    assert bad_shape({}) == (Status.FAIL("invalid step return value"), {})
