import textwrap
from pathlib import Path

from progress_tests.cli import discover, main


def _write(path: Path, source: str) -> None:
    path.write_text(textwrap.dedent(source))


def test_discover_finds_test_prefixed_files(tmp_path):
    _write(
        tmp_path / "test_one.py",
        """
        def test_a():
            pass
        """,
    )

    tests = discover(tmp_path)

    assert [label for label, _ in tests] == ["test_one.py::test_a"]


def test_discover_finds_test_suffixed_files(tmp_path):
    _write(
        tmp_path / "pipeline_test.py",
        """
        def test_a():
            pass
        """,
    )

    tests = discover(tmp_path)

    assert [label for label, _ in tests] == ["pipeline_test.py::test_a"]


def test_discover_walks_subdirectories(tmp_path):
    nested = tmp_path / "sub"
    nested.mkdir()
    _write(
        nested / "test_nested.py",
        """
        def test_a():
            pass
        """,
    )

    tests = discover(tmp_path)

    assert [label for label, _ in tests] == ["sub/test_nested.py::test_a"]


def test_discover_only_collects_test_prefixed_functions(tmp_path):
    _write(
        tmp_path / "test_one.py",
        """
        def helper():
            pass

        def test_a():
            pass
        """,
    )

    tests = discover(tmp_path)

    assert [label for label, _ in tests] == ["test_one.py::test_a"]


def test_discover_ignores_functions_imported_from_elsewhere(tmp_path):
    _write(
        tmp_path / "helpers.py",
        """
        def test_imported():
            pass
        """,
    )
    _write(
        tmp_path / "test_one.py",
        """
        import sys
        sys.path.insert(0, ".")
        from helpers import test_imported

        def test_a():
            pass
        """,
    )

    tests = discover(tmp_path)

    assert [label for label, _ in tests] == ["test_one.py::test_a"]


def test_main_reports_no_tests_found(tmp_path, capsys):
    exit_code = main([str(tmp_path)])

    assert exit_code == 0
    assert "no progressive tests found" in capsys.readouterr().out


def test_main_runs_discovered_tests_and_exits_zero_when_all_pass(tmp_path, capsys):
    _write(
        tmp_path / "test_one.py",
        """
        def test_a():
            print("ran test_a")
        """,
    )

    exit_code = main([str(tmp_path)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "test_one.py::test_a" in out
    assert "ran test_a" in out
    assert "1 passed" in out


def test_main_exits_nonzero_when_a_test_raises_assertion_error(tmp_path, capsys):
    _write(
        tmp_path / "test_one.py",
        """
        def test_a():
            raise AssertionError("2 of 3 inputs did not pass")
        """,
    )

    exit_code = main([str(tmp_path)])

    out = capsys.readouterr().out
    assert exit_code == 1
    assert "2 of 3 inputs did not pass" in out
    assert "0 passed, 1 failed" in out


def test_main_continues_past_a_failing_test_to_run_the_rest(tmp_path, capsys):
    _write(
        tmp_path / "test_one.py",
        """
        def test_a():
            raise AssertionError("boom")
        """,
    )
    _write(
        tmp_path / "test_two.py",
        """
        def test_b():
            print("ran test_b")
        """,
    )

    exit_code = main([str(tmp_path)])

    out = capsys.readouterr().out
    assert exit_code == 1
    assert "ran test_b" in out
    assert "1 passed, 1 failed" in out


def test_main_reports_an_unexpected_exception_as_a_failure(tmp_path, capsys):
    _write(
        tmp_path / "test_one.py",
        """
        def test_a():
            raise ValueError("not an AssertionError")
        """,
    )

    exit_code = main([str(tmp_path)])

    out = capsys.readouterr().out
    assert exit_code == 1
    assert "0 passed, 1 failed" in out


def test_main_defaults_to_the_current_directory(tmp_path, capsys, monkeypatch):
    _write(
        tmp_path / "test_one.py",
        """
        def test_a():
            pass
        """,
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main([])

    assert exit_code == 0
    assert "1 passed" in capsys.readouterr().out
