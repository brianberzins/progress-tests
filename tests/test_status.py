from progress_tests import Status


def test_status_has_three_distinct_values():
    assert len({Status.PASS, Status.WAIT, Status.FAIL}) == 3


def test_status_has_no_message_by_default():
    assert Status.PASS.message is None
    assert Status.WAIT.message is None
    assert Status.FAIL.message is None


def test_status_is_callable_to_attach_a_message():
    waiting = Status.WAIT("waiting on backup")

    assert waiting.message == "waiting on backup"


def test_status_with_a_message_still_equals_the_plain_status_of_the_same_kind():
    assert Status.WAIT("waiting on backup") == Status.WAIT
    assert Status.WAIT("waiting on backup") != Status.PASS


def test_status_with_a_message_still_hashes_like_the_plain_status():
    assert hash(Status.WAIT("waiting on backup")) == hash(Status.WAIT)


def test_status_has_no_detail_by_default():
    assert Status.FAIL.message is None
    assert Status.FAIL.detail is None


def test_status_can_attach_a_detail_alongside_a_message():
    failed = Status.FAIL("bucket missing", detail="full diagnostic dump")

    assert failed.message == "bucket missing"
    assert failed.detail == "full diagnostic dump"
