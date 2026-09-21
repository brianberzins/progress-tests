import pytest

from progressive_tests import Status, step


def test_step_returns_the_underlying_status():
    @step("ALWAYS_PASS")
    def always_pass(case):
        return Status.PASS

    assert always_pass({}) is Status.PASS


def test_step_records_its_name():
    @step("BUCKET_EXISTS")
    def bucket_exists(case):
        return Status.PASS

    assert bucket_exists.step_name == "BUCKET_EXISTS"


def test_step_turns_a_non_status_return_into_fail():
    @step("FORGOT_TO_RETURN_STATUS")
    def broken(case):
        return "pass"  # a plain string, not Status.PASS

    assert broken({}) is Status.FAIL


def test_step_turns_a_raised_exception_into_fail():
    @step("EXPLODES")
    def broken(case):
        raise RuntimeError("simulated failure for this test")

    assert broken({}) is Status.FAIL


def test_step_turns_an_unimplemented_check_into_fail_not_wait():
    @step("NOT_BUILT_YET")
    def not_built_yet(case):
        raise NotImplementedError

    assert not_built_yet({}) is Status.FAIL


def test_step_rejects_a_function_with_no_arguments_at_decoration_time():
    with pytest.raises(TypeError):

        @step("BAD_SHAPE")
        def no_args():
            return Status.PASS


def test_step_rejects_a_function_with_two_arguments_at_decoration_time():
    with pytest.raises(TypeError):

        @step("BAD_SHAPE")
        def two_args(case, extra):
            return Status.PASS
