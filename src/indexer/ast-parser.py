"""AST parser using tree-sitter — extracts code symbols from Python/JS/TS files.

Produces a flat list of CodeSymbol objects with name, kind, line, parent scope.
Uses tree-sitter query API (S-expressions) for fast C-level extraction.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from tree_sitter import Language, Parser, Query, QueryCursor, Node

import tree_sitter_python as ts_python
import tree_sitter_javascript as ts_javascript
import tree_sitter_typescript as ts_typescript

# --- Data model ---

@dataclass
class CodeSymbol:
    """A code entity extracted from AST."""
    name: str
    kind: str  # "function", "class", "import"
    line: int
    file_path: str
    parent: str | None = None  # enclosing class/function name


# --- Language registry ---

# S-expression queries per language for extracting symbols
_PYTHON_QUERY = """
(function_definition name: (identifier) @func.name) @func.def
(class_definition name: (identifier) @class.name) @class.def
(import_statement) @import.stmt
(import_from_statement module_name: (dotted_name) @import.module) @import.from
"""

_JS_QUERY = """
(function_declaration name: (identifier) @func.name) @func.def
(class_declaration name: (identifier) @class.name) @class.def
(import_statement) @import.stmt
(export_statement declaration: (function_declaration name: (identifier) @func.name)) @export.func
(export_statement declaration: (class_declaration name: (identifier) @class.name)) @export.class
"""

# TS uses same grammar as JS + type annotations (queries compatible)
_TS_QUERY = _JS_QUERY


@dataclass
class _LangConfig:
    """tree-sitter language + query config."""
    language: Language
    query_src: str
    _parser: Parser = field(default=None, init=False, repr=False)
    _query: object = field(default=None, init=False, repr=False)

    @property
    def parser(self) -> Parser:
        if self._parser is None:
            self._parser = Parser(self.language)
        return self._parser

    @property
    def query(self) -> Query:
        if self._query is None:
            self._query = Query(self.language, self.query_src)
        return self._query


# Map file extensions to language configs (lazy-init parsers)
_PY_LANG = Language(ts_python.language())
_JS_LANG = Language(ts_javascript.language())
_TS_LANG = Language(ts_typescript.language_typescript())
_TSX_LANG = Language(ts_typescript.language_tsx())

LANG_REGISTRY: dict[str, _LangConfig] = {
    ".py": _LangConfig(_PY_LANG, _PYTHON_QUERY),
    ".js": _LangConfig(_JS_LANG, _JS_QUERY),
    ".jsx": _LangConfig(_JS_LANG, _JS_QUERY),
    ".ts": _LangConfig(_TS_LANG, _TS_QUERY),
    ".tsx": _LangConfig(_TSX_LANG, _TS_QUERY),
}

# Directories to always skip
DEFAULT_IGNORE_DIRS = {
    "__pycache__", "node_modules", ".git", ".venv", "venv",
    "dist", "build", ".next", ".cache", ".tox", "egg-info",
}


# --- Parser functions ---

def _find_parent_scope(node: Node) -> str | None:
    """Walk up AST to find enclosing class or function name.

    Starts from the node's grandparent to skip the definition node itself.
    """
    # Skip: node (identifier) → parent (func/class_definition) → grandparent
    current = node.parent
    if current:
        current = current.parent
    while current:
        if current.type in ("class_definition", "class_declaration"):
            name_node = current.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8")
        if current.type in ("function_definition", "function_declaration"):
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
                    # Get full statement from parent
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
