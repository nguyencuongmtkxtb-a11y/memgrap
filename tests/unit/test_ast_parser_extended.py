"""Extended unit tests for src.indexer.ast_parser — ignore dirs, parse edge cases."""

import os
import tempfile

import pytest

from src.indexer.ast_parser import (
    DEFAULT_IGNORE_DIRS,
    parse_directory,
    parse_file,
)


# ---------------------------------------------------------------------------
# DEFAULT_IGNORE_DIRS — 'gen' should NOT be in the ignore list
# ---------------------------------------------------------------------------


def test_default_ignore_dirs_excludes_gen():
    """'gen' directory should NOT be in DEFAULT_IGNORE_DIRS."""
    assert "gen" not in DEFAULT_IGNORE_DIRS


def test_default_ignore_dirs_includes_expected():
    """Key directories are present in DEFAULT_IGNORE_DIRS."""
    expected = {"__pycache__", "node_modules", ".git", ".venv", "venv", "dist", "build"}
    assert expected.issubset(DEFAULT_IGNORE_DIRS)


def test_default_ignore_dirs_is_set():
    """DEFAULT_IGNORE_DIRS is a set (not list) for O(1) lookups."""
    assert isinstance(DEFAULT_IGNORE_DIRS, set)


# ---------------------------------------------------------------------------
# parse_directory — custom extensions filter
# ---------------------------------------------------------------------------


def test_parse_directory_custom_extensions(tmp_path):
    """parse_directory with extensions={'.py'} skips .js files."""
    (tmp_path / "app.py").write_text("def app_func(): pass\n")
    (tmp_path / "util.js").write_text("function jsFunc() {}\n")

    symbols = parse_directory(str(tmp_path), extensions={".py"})
    names = {s.name for s in symbols}

    assert "app_func" in names
    assert "jsFunc" not in names


def test_parse_directory_multiple_extensions(tmp_path):
    """parse_directory with multiple extensions finds both."""
    (tmp_path / "app.py").write_text("def py_func(): pass\n")
    (tmp_path / "util.js").write_text("function js_func() {}\n")

    symbols = parse_directory(str(tmp_path), extensions={".py", ".js"})
    names = {s.name for s in symbols}

    assert "py_func" in names
    assert "js_func" in names


# ---------------------------------------------------------------------------
# parse_directory — custom ignore_dirs
# ---------------------------------------------------------------------------


def test_parse_directory_custom_ignore_dirs(tmp_path):
    """parse_directory with custom ignore_dirs skips specified directories."""
    (tmp_path / "main.py").write_text("def visible(): pass\n")

    custom_dir = tmp_path / "myvendor"
    custom_dir.mkdir()
    (custom_dir / "hidden.py").write_text("def hidden_func(): pass\n")

    symbols = parse_directory(str(tmp_path), ignore_dirs={"myvendor"})
    names = {s.name for s in symbols}

    assert "visible" in names
    assert "hidden_func" not in names


# ---------------------------------------------------------------------------
# parse_directory — nested subdirectories
# ---------------------------------------------------------------------------


def test_parse_directory_nested(tmp_path):
    """parse_directory recurses into non-ignored subdirectories."""
    sub = tmp_path / "sub" / "deep"
    sub.mkdir(parents=True)
    (sub / "nested.py").write_text("def nested_func(): pass\n")

    symbols = parse_directory(str(tmp_path), extensions={".py"})
    names = {s.name for s in symbols}

    assert "nested_func" in names


# ---------------------------------------------------------------------------
# parse_directory — empty directory
# ---------------------------------------------------------------------------


def test_parse_directory_empty(tmp_path):
    """parse_directory on empty directory returns empty list."""
    symbols = parse_directory(str(tmp_path))
    assert symbols == []


# ---------------------------------------------------------------------------
# parse_directory — gen directory NOT ignored
# ---------------------------------------------------------------------------


def test_parse_directory_gen_not_ignored(tmp_path):
    """Files in 'gen/' directory are parsed (not in ignore list)."""
    gen_dir = tmp_path / "gen"
    gen_dir.mkdir()
    (gen_dir / "generated.py").write_text("def gen_func(): pass\n")

    symbols = parse_directory(str(tmp_path), extensions={".py"})
    names = {s.name for s in symbols}

    assert "gen_func" in names


# ---------------------------------------------------------------------------
# parse_file — empty file
# ---------------------------------------------------------------------------


def test_parse_file_empty():
    """Parsing an empty Python file returns empty list."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
        f.write("")
        f.flush()
        result = parse_file(f.name)
    os.unlink(f.name)
    assert result == []


# ---------------------------------------------------------------------------
# parse_file — forward slash normalization
# ---------------------------------------------------------------------------


def test_parse_directory_normalizes_paths(tmp_path):
    """parse_directory normalizes paths to use forward slashes."""
    (tmp_path / "test.py").write_text("def slash_test(): pass\n")

    symbols = parse_directory(str(tmp_path), extensions={".py"})

    for s in symbols:
        assert "\\" not in s.file_path, f"Path contains backslash: {s.file_path}"


# ---------------------------------------------------------------------------
# parse_file — multiple classes
# ---------------------------------------------------------------------------


def test_parse_file_multiple_classes():
    """Parsing a file with multiple classes finds all of them."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
        f.write("class Alpha:\n    pass\n\nclass Beta:\n    pass\n\nclass Gamma:\n    pass\n")
        f.flush()
        fp = f.name.replace("\\", "/")
    try:
        symbols = parse_file(fp)
        class_names = {s.name for s in symbols if s.kind == "class"}
        assert class_names == {"Alpha", "Beta", "Gamma"}
    finally:
        os.unlink(f.name)


# ---------------------------------------------------------------------------
# parse_directory — default extensions uses LANG_REGISTRY
# ---------------------------------------------------------------------------


def test_parse_directory_default_extensions(tmp_path):
    """When extensions=None, parse_directory uses all registered extensions."""
    (tmp_path / "app.py").write_text("def default_ext(): pass\n")

    symbols = parse_directory(str(tmp_path))  # No extensions param
    names = {s.name for s in symbols}

    assert "default_ext" in names
