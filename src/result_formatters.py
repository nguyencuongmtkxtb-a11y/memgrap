"""Format Graphiti query results into serializable dicts for MCP responses."""


def format_edge(e) -> dict:
    """Format an EntityEdge (fact) into a dict."""
    return {
        "fact": e.fact,
        "name": e.name,
        "valid_at": str(e.valid_at) if e.valid_at else None,
        "invalid_at": str(e.invalid_at) if e.invalid_at else None,
        "uuid": e.uuid,
    }


def format_node(n) -> dict:
    """Format an EntityNode into a dict."""
    return {
        "name": n.name,
        "summary": n.summary if hasattr(n, "summary") else None,
        "labels": list(n.labels) if hasattr(n, "labels") else [],
        "uuid": n.uuid,
    }


def format_episode(ep) -> dict:
    """Format an EpisodicNode into a dict."""
    return {
        "name": ep.name,
        "content": ep.content[:200] if ep.content else "",
        "created_at": str(ep.created_at) if ep.created_at else None,
        "uuid": ep.uuid,
    }
