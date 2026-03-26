"""Unit tests for src.result_formatters — pure formatting functions."""

from types import SimpleNamespace

from src.result_formatters import format_edge, format_episode, format_node

# ---------------------------------------------------------------------------
# format_edge
# ---------------------------------------------------------------------------


def test_format_edge_complete():
    edge = SimpleNamespace(
        fact="sky is blue",
        name="color_fact",
        valid_at="2024-01-01T00:00:00",
        invalid_at="2025-06-01T00:00:00",
        uuid="edge-uuid-1",
    )
    result = format_edge(edge)
    assert result == {
        "fact": "sky is blue",
        "name": "color_fact",
        "valid_at": "2024-01-01T00:00:00",
        "invalid_at": "2025-06-01T00:00:00",
        "uuid": "edge-uuid-1",
    }


def test_format_edge_null_timestamps():
    edge = SimpleNamespace(
        fact="still valid",
        name="open_fact",
        valid_at=None,
        invalid_at=None,
        uuid="edge-uuid-2",
    )
    result = format_edge(edge)
    assert result["valid_at"] is None
    assert result["invalid_at"] is None


# ---------------------------------------------------------------------------
# format_node
# ---------------------------------------------------------------------------


def test_format_node_with_summary_and_labels():
    node = SimpleNamespace(
        name="Python",
        summary="A programming language",
        labels=["Language", "Tool"],
        uuid="node-uuid-1",
    )
    result = format_node(node)
    assert result == {
        "name": "Python",
        "summary": "A programming language",
        "labels": ["Language", "Tool"],
        "uuid": "node-uuid-1",
    }


def test_format_node_without_summary():
    """Node lacking a summary attr should return summary=None."""
    node = SimpleNamespace(
        name="Mystery",
        labels=["Unknown"],
        uuid="node-uuid-2",
    )
    # Explicitly remove summary so hasattr returns False
    assert not hasattr(node, "summary")
    result = format_node(node)
    assert result["summary"] is None


# ---------------------------------------------------------------------------
# format_episode
# ---------------------------------------------------------------------------


def test_format_episode_truncates_content():
    long_content = "x" * 300
    ep = SimpleNamespace(
        name="long_episode",
        content=long_content,
        created_at="2024-06-15T12:00:00",
        uuid="ep-uuid-1",
    )
    result = format_episode(ep)
    assert len(result["content"]) == 200
    assert result["content"] == "x" * 200


def test_format_episode_empty_content():
    ep = SimpleNamespace(
        name="empty_ep",
        content="",
        created_at=None,
        uuid="ep-uuid-2",
    )
    result = format_episode(ep)
    assert result["content"] == ""
    assert result["created_at"] is None


def test_format_episode_none_content():
    ep = SimpleNamespace(
        name="none_ep",
        content=None,
        created_at="2024-01-01",
        uuid="ep-uuid-3",
    )
    result = format_episode(ep)
    assert result["content"] == ""
