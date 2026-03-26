"""AST parser using tree-sitter — extracts code symbols from source files.

Produces a flat list of CodeSymbol objects with name, kind, line, parent scope.
Uses tree-sitter query API (S-expressions) for fast C-level extraction.

Supported languages: Python, JS, TS, JSX, TSX (required), plus Go, Rust, Java,
C, C++, C#, Ruby, PHP (optional — installed via tree-sitter-* packages).
"""

import os
from dataclasses import dataclass
from pathlib import Path

from tree_sitter import Node, QueryCursor

from src.indexer.language_configs import LANG_REGISTRY

# --- Data model ---

@dataclass
class CodeSymbol:
    """A code entity extracted from AST."""
    name: str
    kind: str  # "function", "class", "import"
    line: int
    file_path: str
    parent: str | None = None  # enclosing class/function name


# Directories to always skip
DEFAULT_IGNORE_DIRS = {
    "__pycache__", "node_modules", ".git", ".venv", "venv",
    "dist", "build", ".next", ".cache", ".tox", "egg-info",
    "obj", "bin", "target", "vendor", "gen",
}


# --- Parser functions ---

def _find_parent_scope(node: Node) -> str | None:
    """Walk up AST to find enclosing class or function name.

    Starts from the node's grandparent to skip the definition node itself.
    """
    # Skip: node (identifier) -> parent (func/class_definition) -> grandparent
    current = node.parent
    if current:
        current = current.parent
    while current:
        if current.type in (
            "class_definition", "class_declaration",
            "class_specifier", "struct_specifier",
            "impl_item", "trait_item",
        ):
            name_node = current.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8")
        if current.type in (
            "function_definition", "function_declaration",
            "function_item", "method_declaration",
        ):
            name_node = current.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8")
        current = current.parent
    return None


def _extract_import_name(node: Node) -> str:
    """Extract a readable import name from an import statement node."""
    text = node.text.decode("utf-8").strip()
    # Truncate long imports
    if len(text) > 100:
        text = text[:97] + "..."
    return text


def parse_file(file_path: str) -> list[CodeSymbol]:
    """Parse a single file and return extracted code symbols.

    Returns empty list if file extension not supported or file unreadable.
    """
    ext = Path(file_path).suffix.lower()
    lang_config = LANG_REGISTRY.get(ext)
    if not lang_config:
        return []

    try:
        source = Path(file_path).read_bytes()
    except (OSError, IOError):
        return []

    tree = lang_config.parser.parse(source)
    cursor = QueryCursor(lang_config.query)
    captures = cursor.captures(tree.root_node)

    symbols: list[CodeSymbol] = []
    seen_imports: set[int] = set()  # dedupe import lines

    for capture_name, nodes in captures.items():
        for node in nodes:
            if capture_name == "func.name":
                symbols.append(CodeSymbol(
                    name=node.text.decode("utf-8"),
                    kind="function",
                    line=node.start_point.row + 1,
                    file_path=file_path,
                    parent=_find_parent_scope(node),
                ))
            elif capture_name == "class.name":
                symbols.append(CodeSymbol(
                    name=node.text.decode("utf-8"),
                    kind="class",
                    line=node.start_point.row + 1,
                    file_path=file_path,
                    parent=_find_parent_scope(node),
                ))
            elif capture_name in ("import.stmt", "import.from"):
                line_no = node.start_point.row + 1
                if line_no not in seen_imports:
                    seen_imports.add(line_no)
                    symbols.append(CodeSymbol(
                        name=_extract_import_name(node),
                        kind="import",
                        line=line_no,
                        file_path=file_path,
                    ))
            elif capture_name == "import.module":
                # Python "from X import ..." — capture module name
                line_no = node.start_point.row + 1
                if line_no not in seen_imports:
                    seen_imports.add(line_no)
                    parent_node = node.parent
                    symbols.append(CodeSymbol(
                        name=_extract_import_name(parent_node) if parent_node else node.text.decode("utf-8"),
                        kind="import",
                        line=line_no,
                        file_path=file_path,
                    ))

    return symbols


def parse_directory(
    path: str,
    extensions: set[str] | None = None,
    ignore_dirs: set[str] | None = None,
) -> list[CodeSymbol]:
    """Walk directory tree, parse supported files, return all symbols.

    Args:
        path: Root directory to scan
        extensions: File extensions to include (default: all supported)
        ignore_dirs: Directory names to skip (default: DEFAULT_IGNORE_DIRS)
    """
    if extensions is None:
        extensions = set(LANG_REGISTRY.keys())
    if ignore_dirs is None:
        ignore_dirs = DEFAULT_IGNORE_DIRS

    all_symbols: list[CodeSymbol] = []

    for dirpath, dirnames, filenames in os.walk(path):
        # Prune ignored directories in-place
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext in extensions:
                full_path = os.path.join(dirpath, fname)
                # Normalize path separators
                full_path = full_path.replace("\\", "/")
                all_symbols.extend(parse_file(full_path))

    return all_symbols
