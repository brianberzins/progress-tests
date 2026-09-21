from progressive_tests import Status


def test_status_has_three_values():
    assert {Status.PASS, Status.WAIT, Status.FAIL} == set(Status)
