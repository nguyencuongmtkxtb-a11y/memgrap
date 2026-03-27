"""Unit tests for src.indexer.import_resolver — import source resolution."""

import pytest

from src.indexer.import_resolver import resolve_import, _generate_candidates


# ---------------------------------------------------------------------------
# Edge cases — empty inputs
# ---------------------------------------------------------------------------


def test_resolve_import_empty_source():
    """Empty import source returns None."""
    result = resolve_import("", "src/main.py", {"src/utils.py"})
    assert result is None


def test_resolve_import_empty_indexed_paths():
    """Empty indexed_paths set returns None."""
    result = resolve_import("src.utils", "src/main.py", set())
    assert result is None


def test_resolve_import_none_source():
    """None import source returns None."""
    result = resolve_import(None, "src/main.py", {"src/utils.py"})
    assert result is None


# ---------------------------------------------------------------------------
# Python — dotted module resolution
# ---------------------------------------------------------------------------


def test_resolve_python_dotted_module():
    """Python dotted module 'src.utils' resolves to 'src/utils.py'."""
    indexed = {"src/utils.py", "src/main.py"}
    result = resolve_import("src.utils", "src/main.py", indexed)
    assert result == "src/utils.py"


def test_resolve_python_init_package():
    """Python package resolves to __init__.py."""
    indexed = {"src/indexer/__init__.py", "src/main.py"}
    result = resolve_import("src.indexer", "src/main.py", indexed)
    assert result == "src/indexer/__init__.py"


def test_resolve_python_with_project_root():
    """Python dotted module resolves with project_root prefix."""
    indexed = {"D:/project/src/utils.py"}
    result = resolve_import("src.utils", "D:/project/src/main.py", indexed, project_root="D:/project")
    assert result == "D:/project/src/utils.py"


def test_resolve_python_no_match():
    """Python import with no matching indexed path returns None."""
    indexed = {"src/other.py"}
    result = resolve_import("src.missing", "src/main.py", indexed)
    assert result is None


# ---------------------------------------------------------------------------
# JS/TS — relative imports
# ---------------------------------------------------------------------------


def test_resolve_js_relative_import():
    """JS relative import './utils' resolves to utils.js."""
    indexed = {"src/utils.js", "src/main.js"}
    result = resolve_import("./utils", "src/main.js", indexed)
    assert result == "src/utils.js"


def test_resolve_ts_relative_import():
    """TS relative import './service' resolves to service.ts."""
    indexed = {"src/service.ts", "src/app.ts"}
    result = resolve_import("./service", "src/app.ts", indexed)
    assert result == "src/service.ts"


def test_resolve_js_bare_specifier():
    """JS bare specifier (e.g. 'react') returns None — external module."""
    indexed = {"src/main.js"}
    result = resolve_import("react", "src/main.js", indexed)
    assert result is None


# ---------------------------------------------------------------------------
# Go — package path
# ---------------------------------------------------------------------------


def test_generate_candidates_go():
    """Go import generates last segment as candidate."""
    candidates = _generate_candidates('"fmt"', ".go", "src", "")
    assert "fmt" in candidates


# ---------------------------------------------------------------------------
# Rust — crate paths
# ---------------------------------------------------------------------------


def test_generate_candidates_rust():
    """Rust crate::foo::bar generates src/foo/bar.rs and src/foo/bar/mod.rs."""
    candidates = _generate_candidates("crate::foo::bar", ".rs", "src", "")
    assert "src/foo/bar.rs" in candidates
    assert "src/foo/bar/mod.rs" in candidates


# ---------------------------------------------------------------------------
# Java/Kotlin — dotted class paths
# ---------------------------------------------------------------------------


def test_generate_candidates_java():
    """Java com.example.Foo generates com/example/Foo.java."""
    candidates = _generate_candidates("com.example.Foo", ".java", "src", "")
    assert "com/example/Foo.java" in candidates


def test_generate_candidates_kotlin():
    """Kotlin com.example.Bar generates both .java and .kt candidates."""
    candidates = _generate_candidates("com.example.Bar", ".kt", "src", "")
    assert "com/example/Bar.kt" in candidates
    assert "com/example/Bar.java" in candidates


# ---------------------------------------------------------------------------
# C/C++ — include paths
# ---------------------------------------------------------------------------


def test_generate_candidates_c_header():
    """C #include 'utils.h' generates candidates."""
    candidates = _generate_candidates('"utils.h"', ".c", "src/lib", "")
    assert "utils.h" in candidates
    assert "src/lib/utils.h" in candidates


def test_generate_candidates_c_system_include():
    """C system include <stdio.h> generates candidate."""
    candidates = _generate_candidates("<stdio.h>", ".c", "src", "")
    assert "stdio.h" in candidates


# ---------------------------------------------------------------------------
# C# — using Namespace
# ---------------------------------------------------------------------------


def test_generate_candidates_csharp():
    """C# using Foo.Bar generates Foo/Bar.cs."""
    candidates = _generate_candidates("Foo.Bar", ".cs", "src", "")
    assert "Foo/Bar.cs" in candidates


# ---------------------------------------------------------------------------
# Ruby — require
# ---------------------------------------------------------------------------


def test_generate_candidates_ruby():
    """Ruby require 'foo' generates foo.rb and lib/foo.rb."""
    candidates = _generate_candidates("'foo'", ".rb", "src", "")
    assert "foo.rb" in candidates
    assert "lib/foo.rb" in candidates


# ---------------------------------------------------------------------------
# PHP — use Namespace
# ---------------------------------------------------------------------------


def test_generate_candidates_php():
    """PHP use Foo\\Bar generates Foo/Bar.php."""
    candidates = _generate_candidates("Foo\\Bar", ".php", "src", "")
    assert "Foo/Bar.php" in candidates


# ---------------------------------------------------------------------------
# Swift — external imports
# ---------------------------------------------------------------------------


def test_generate_candidates_swift_empty():
    """Swift imports are external frameworks — no candidates generated."""
    candidates = _generate_candidates("Foundation", ".swift", "src", "")
    assert candidates == []


# ---------------------------------------------------------------------------
# Suffix match resolution
# ---------------------------------------------------------------------------


def test_resolve_suffix_match():
    """Import resolution matches on path suffix when full path differs."""
    indexed = {"D:/project/src/utils.py"}
    result = resolve_import("src.utils", "D:/project/src/main.py", indexed)
    # src/utils.py is a suffix of D:/project/src/utils.py
    assert result == "D:/project/src/utils.py"
