import pytest

from progress_tests import Status, step


def test_step_returns_the_underlying_status_with_no_data():
    @step("ALWAYS_PASS")
    def always_pass(case):
        return Status.PASS

    assert always_pass({}) == (Status.PASS, {})


def test_step_records_its_name():
    @step("BUCKET_EXISTS")
    def bucket_exists(case):
        return Status.PASS

    assert bucket_exists.step_name == "BUCKET_EXISTS"


def test_step_turns_a_non_status_return_into_fail():
    @step("FORGOT_TO_RETURN_STATUS")
    def broken(case):
        return "pass"  # a plain string, not Status.PASS

    assert broken({}) == (Status.FAIL, {})


def test_step_turns_a_raised_exception_into_fail():
    @step("EXPLODES")
    def broken(case):
        raise RuntimeError("simulated failure for this test")

    assert broken({}) == (Status.FAIL, {})


def test_step_turns_an_unimplemented_check_into_fail_not_wait():
    @step("NOT_BUILT_YET")
    def not_built_yet(case):
        raise NotImplementedError

    assert not_built_yet({}) == (Status.FAIL, {})


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


def test_step_can_return_data_alongside_its_status():
    @step("CREATE_DISTRIBUTION")
    def create_distribution(case):
        return Status.PASS, {"distribution_id": "E123"}

    assert create_distribution({}) == (Status.PASS, {"distribution_id": "E123"})


def test_step_returning_a_non_dict_as_the_data_half_is_fail():
    @step("BAD_DATA")
    def bad_data(case):
        return Status.PASS, "not-a-dict"

    assert bad_data({}) == (Status.FAIL, {})


def test_step_returning_a_wrong_sized_tuple_is_fail():
    @step("BAD_SHAPE")
    def bad_shape(case):
        return (Status.PASS,)

    assert bad_shape({}) == (Status.FAIL, {})
