"""Extract code relationships (calls, inheritance, import sources) from AST.

Uses tree-sitter relation queries defined in language_configs to find:
- Function/method calls  -> CodeRelation(type="calls")
- Class inheritance      -> CodeRelation(type="extends")
- Import source modules  -> CodeRelation(type="imports_from")

Works for all 15 supported languages.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from tree_sitter import QueryCursor

from src.indexer.language_configs import LANG_REGISTRY

logger = logging.getLogger(__name__)


@dataclass
class CodeRelation:
    """A relationship between code entities."""
    source_name: str       # caller / child class / importing file
    target_name: str       # callee / parent class / imported module
    relation_type: str     # "calls", "extends", "imports_from"
    file_path: str
    line: int
    source_scope: str | None = None  # enclosing function/class for calls


def _find_enclosing_scope(node) -> str | None:
    """Walk up AST to find enclosing function or class name."""
    current = node.parent
    while current:
        if current.type in (
            "function_definition", "function_declaration",
            "function_item", "method_declaration", "method",
            "singleton_method",
        ):
            name_node = current.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8")
            # Kotlin/Swift: first identifier child
            for child in current.children:
                if child.type in ("identifier", "simple_identifier"):
                    return child.text.decode("utf-8")
        if current.type in (
            "class_definition", "class_declaration",
            "class_specifier", "struct_specifier",
            "impl_item",
        ):
            name_node = current.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8")
            for child in current.children:
                if child.type in ("identifier", "type_identifier"):
                    return child.text.decode("utf-8")
        current = current.parent
    return None


def _clean_string(text: str) -> str:
    """Strip quotes and whitespace from captured text."""
    return text.strip().strip("'\"")


def extract_relations(file_path: str) -> list[CodeRelation]:
    """Extract code relationships from a file using tree-sitter relation queries.

    Returns empty list if language not supported or file unreadable.
    """
    ext = Path(file_path).suffix.lower()
    lang_config = LANG_REGISTRY.get(ext)
    if not lang_config:
        return []

    rel_query = lang_config.relation_query
    if rel_query is None:
        return []

    try:
        source = Path(file_path).read_bytes()
    except (OSError, IOError):
        return []

    tree = lang_config.parser.parse(source)
    cursor = QueryCursor(rel_query)
    captures = cursor.captures(tree.root_node)

    relations: list[CodeRelation] = []
    seen: set[tuple[str, str, str, int]] = set()  # dedupe

    for capture_name, nodes in captures.items():
        for node in nodes:
            text = node.text.decode("utf-8").strip()
            line = node.start_point.row + 1

            if capture_name == "call.name":
                key = ("calls", text, file_path, line)
                if key not in seen:
                    seen.add(key)
                    relations.append(CodeRelation(
                        source_name=_find_enclosing_scope(node) or "<module>",
                        target_name=text,
                        relation_type="calls",
                        file_path=file_path,
                        line=line,
                        source_scope=_find_enclosing_scope(node),
                    ))

            elif capture_name == "extends.name":
                key = ("extends", text, file_path, line)
                if key not in seen:
                    seen.add(key)
                    relations.append(CodeRelation(
                        source_name=_find_enclosing_scope(node) or "<unknown>",
                        target_name=text,
                        relation_type="extends",
                        file_path=file_path,
                        line=line,
                    ))

            elif capture_name == "import.source":
                cleaned = _clean_string(text)
                key = ("imports_from", cleaned, file_path, line)
                if key not in seen:
                    seen.add(key)
                    relations.append(CodeRelation(
                        source_name=file_path,
                        target_name=cleaned,
                        relation_type="imports_from",
                        file_path=file_path,
                        line=line,
                    ))

    return relations
