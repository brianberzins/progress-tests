import sys

from progressive_tests._render import color_enabled


def test_color_enabled_when_stdout_is_a_tty_and_no_env_override(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    assert color_enabled() is True


def test_color_disabled_when_stdout_is_not_a_tty(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)

    assert color_enabled() is False


def test_color_disabled_when_no_color_env_var_is_set(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    assert color_enabled() is False


def test_color_disabled_when_ci_env_var_is_set(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    assert color_enabled() is False
