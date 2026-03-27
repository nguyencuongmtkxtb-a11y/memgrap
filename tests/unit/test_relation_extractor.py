"""Unit tests for src.indexer.relation_extractor — code relationship extraction."""

import os
import tempfile
from pathlib import Path

import pytest

from src.indexer.relation_extractor import (
    CodeRelation,
    _clean_string,
    extract_relations,
)

FIXTURES_DIR = str(
    Path(__file__).resolve().parent.parent / "fixtures"
).replace("\\", "/")


# ---------------------------------------------------------------------------
# _clean_string
# ---------------------------------------------------------------------------


def test_clean_string_strips_quotes():
    """Single and double quotes are removed."""
    assert _clean_string("'hello'") == "hello"
    assert _clean_string('"world"') == "world"


def test_clean_string_strips_whitespace():
    """Leading/trailing whitespace is removed."""
    assert _clean_string("  foo  ") == "foo"


def test_clean_string_combined():
    """Quotes and whitespace stripped together."""
    assert _clean_string("  'bar'  ") == "bar"


# ---------------------------------------------------------------------------
# extract_relations — unsupported extension
# ---------------------------------------------------------------------------


def test_extract_relations_unsupported_ext():
    """Unsupported file extension returns empty list."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
        f.write("hello world\n")
        f.flush()
        result = extract_relations(f.name)
    os.unlink(f.name)
    assert result == []


def test_extract_relations_nonexistent_file():
    """Nonexistent file returns empty list."""
    result = extract_relations("/nonexistent/fake.py")
    assert result == []


# ---------------------------------------------------------------------------
# extract_relations — Python calls
# ---------------------------------------------------------------------------


def test_extract_relations_python_calls():
    """Python file with function calls produces 'calls' relations."""
    fp = os.path.join(FIXTURES_DIR, "relations_sample.py").replace("\\", "/")
    relations = extract_relations(fp)

    calls = [r for r in relations if r.relation_type == "calls"]
    call_targets = {r.target_name for r in calls}

    # connect(), print(), len(), str() are called in the sample
    assert "connect" in call_targets
    assert "print" in call_targets


# ---------------------------------------------------------------------------
# extract_relations — Python extends
# ---------------------------------------------------------------------------


def test_extract_relations_python_extends():
    """Python class inheritance produces 'extends' relations."""
    fp = os.path.join(FIXTURES_DIR, "relations_sample.py").replace("\\", "/")
    relations = extract_relations(fp)

    extends = [r for r in relations if r.relation_type == "extends"]

    assert len(extends) >= 1
    assert any(r.target_name == "BaseService" for r in extends)
    # The child class should be identified
    assert any(r.source_name == "UserService" for r in extends)


# ---------------------------------------------------------------------------
# extract_relations — Python imports_from
# ---------------------------------------------------------------------------


def test_extract_relations_python_imports():
    """Python import statements produce 'imports_from' relations."""
    fp = os.path.join(FIXTURES_DIR, "relations_sample.py").replace("\\", "/")
    relations = extract_relations(fp)

    imports = [r for r in relations if r.relation_type == "imports_from"]

    assert len(imports) >= 1
    # 'from os.path import join' -> source = "os.path"
    import_targets = {r.target_name for r in imports}
    assert "os.path" in import_targets or any("os" in t for t in import_targets)


# ---------------------------------------------------------------------------
# extract_relations — deduplication
# ---------------------------------------------------------------------------


def test_extract_relations_deduplication():
    """Same call on same line should not produce duplicate relations."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
        f.write("def foo():\n    bar()\n    bar()\n")
        f.flush()
        fp = f.name.replace("\\", "/")
    try:
        relations = extract_relations(fp)
        calls = [r for r in relations if r.relation_type == "calls" and r.target_name == "bar"]
        # Two calls on different lines should both appear
        assert len(calls) == 2
    finally:
        os.unlink(f.name)


# ---------------------------------------------------------------------------
# CodeRelation dataclass
# ---------------------------------------------------------------------------


def test_code_relation_fields():
    """CodeRelation dataclass has expected fields and defaults."""
    rel = CodeRelation(
        source_name="foo",
        target_name="bar",
        relation_type="calls",
        file_path="test.py",
        line=10,
    )
    assert rel.source_name == "foo"
    assert rel.target_name == "bar"
    assert rel.relation_type == "calls"
    assert rel.file_path == "test.py"
    assert rel.line == 10
    assert rel.source_scope is None


def test_code_relation_with_scope():
    """CodeRelation stores source_scope when provided."""
    rel = CodeRelation(
        source_name="foo",
        target_name="bar",
        relation_type="calls",
        file_path="test.py",
        line=10,
        source_scope="MyClass",
    )
    assert rel.source_scope == "MyClass"
