from progress_tests import Status
from progress_tests.status import _Kind


def test_status_has_three_distinct_kinds():
    assert len({_Kind.PASS, _Kind.WAIT, _Kind.FAIL}) == 3


def test_status_can_carry_a_message():
    assert Status.PASS("ok").message == "ok"
    assert Status.WAIT("waiting").message == "waiting"
    assert Status.FAIL("boom").message == "boom"


def test_status_message_defaults_to_empty():
    assert Status.PASS().message == ""
    assert Status.WAIT().message == ""
    assert Status.FAIL().message == ""


def test_status_has_no_detail_by_default():
    assert Status.FAIL("boom").detail is None


def test_status_can_attach_a_detail_alongside_a_message():
    failed = Status.FAIL("bucket missing", detail="full diagnostic dump")

    assert failed.message == "bucket missing"
    assert failed.detail == "full diagnostic dump"


def test_two_statuses_of_the_same_kind_and_message_are_equal():
    assert Status.WAIT("waiting on backup") == Status.WAIT("waiting on backup")


def test_two_statuses_with_different_messages_are_not_equal():
    assert Status.WAIT("waiting on backup") != Status.WAIT("waiting on restore")
