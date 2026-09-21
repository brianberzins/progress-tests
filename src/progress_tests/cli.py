import argparse
import importlib.util
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

_TEST_FILE_PATTERNS = ("test_*.py", "*_test.py")


def discover(root: Path) -> list[tuple[str, Callable[[], None]]]:
    """Find every `test_*.py`/`*_test.py` file under `root`, import it,
    and collect its top-level `test_*` functions.

    No fixtures, no parametrize, no plugin system: each function is
    called with zero arguments, and `invoke()` already raises on real
    failure, so "did it raise" is the whole pass/fail signal.
    """
    tests: list[tuple[str, Callable[[], None]]] = []
    for path in _discover_files(root):
        module = _import_file(path)
        for name, obj in vars(module).items():
            if (
                name.startswith("test_")
                and callable(obj)
                and getattr(obj, "__module__", None) == module.__name__
            ):
                tests.append((f"{path.relative_to(root)}::{name}", obj))
    return tests


def _discover_files(root: Path) -> list[Path]:
    found: set[Path] = set()
    for pattern in _TEST_FILE_PATTERNS:
        found.update(root.rglob(pattern))
    return sorted(found)


def _import_file(path: Path):
    # A unique module name per file avoids sys.modules collisions between
    # same-named test files in different directories.
    module_name = f"_progress_tests_discovered_{abs(hash(path))}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(path.parent))
    return module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="progress-tests")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        type=Path,
        help="directory to discover progressive tests under (default: cwd)",
    )
    args = parser.parse_args(argv)
    root = args.path.resolve()

    tests = discover(root)
    if not tests:
        print(f"no progressive tests found under {root}")
        return 0

    failed: list[str] = []
    for label, test in tests:
        print(label)
        try:
            test()
        except AssertionError as exc:
            failed.append(label)
            print(f"  {exc}")
        except Exception:
            failed.append(label)
            traceback.print_exc()
        print()

    passed = len(tests) - len(failed)
    if failed:
        print(f"{passed} passed, {len(failed)} failed")
        return 1
    print(f"{passed} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
