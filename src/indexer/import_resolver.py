"""Resolve import source strings to actual file paths in the project.

Maps language-specific import syntax to CodeFile paths already indexed in Neo4j.
Example: "from src.indexer.ast_parser import ..." -> "D:/MEMGRAP/src/indexer/ast_parser.py"

Resolution strategies per language:
- Python: dotted module -> path with / separators + .py
- JS/TS: relative paths ./foo -> resolve from file dir; bare specifiers -> node_modules
- Go: full import path -> last segment matches package dir
- Rust: crate::module -> src/module.rs or src/module/mod.rs
- Java/Kotlin: com.example.Foo -> com/example/Foo.java
- C/C++: #include "foo.h" -> search include paths
- C#: using Namespace -> search for Namespace dir
- Ruby: require "foo" -> lib/foo.rb
- PHP: use Foo\\Bar -> Foo/Bar.php
"""

import os
from pathlib import Path


def resolve_import(
    import_source: str,
    file_path: str,
    indexed_paths: set[str],
    project_root: str = "",
) -> str | None:
    """Try to resolve an import source string to an indexed file path.

    Args:
        import_source: Raw import string (e.g. "src.indexer.ast_parser", "./utils", "fmt")
        file_path: The file containing the import
        indexed_paths: Set of all indexed file paths for fuzzy matching
        project_root: Project root directory for absolute resolution

    Returns:
        Matched file path from indexed_paths, or None if unresolvable.
    """
    if not import_source or not indexed_paths:
        return None

    ext = Path(file_path).suffix.lower()
    file_dir = os.path.dirname(file_path).replace("\\", "/")

    # Try language-specific resolution
    candidates = _generate_candidates(import_source, ext, file_dir, project_root)

    # Match candidates against indexed paths (normalized)
    for candidate in candidates:
        candidate = candidate.replace("\\", "/")
        # Exact match
        if candidate in indexed_paths:
            return candidate
        # Suffix match (for when paths differ in prefix)
        for indexed in indexed_paths:
            if indexed.endswith(candidate) or candidate.endswith(indexed.rsplit("/", 1)[-1]):
                # Verify it's a meaningful suffix match, not just filename
                if "/" in candidate and indexed.endswith(candidate):
                    return indexed

    return None


def _generate_candidates(
    source: str, ext: str, file_dir: str, project_root: str,
) -> list[str]:
    """Generate possible file path candidates from import source."""
    candidates: list[str] = []

    if ext == ".py":
        # Python: dotted module -> path
        module_path = source.replace(".", "/")
        candidates.append(f"{module_path}.py")
        candidates.append(f"{module_path}/__init__.py")
        if project_root:
            candidates.append(f"{project_root}/{module_path}.py")
            candidates.append(f"{project_root}/{module_path}/__init__.py")

    elif ext in (".js", ".jsx", ".ts", ".tsx"):
        # JS/TS: relative or bare specifier
        clean = source.strip("'\"")
        if clean.startswith("."):
            # Relative import
            base = os.path.normpath(os.path.join(file_dir, clean)).replace("\\", "/")
            for suffix in ("", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx", "/index.js"):
                candidates.append(base + suffix)
        else:
            # Bare specifier — likely node_modules, skip resolution
            pass

    elif ext == ".go":
        # Go: full import path -> match last path segment
        clean = source.strip('"')
        parts = clean.split("/")
        if parts:
            candidates.append(parts[-1])  # package name for fuzzy match

    elif ext == ".rs":
        # Rust: crate::foo::bar -> src/foo/bar.rs or src/foo/bar/mod.rs
        clean = source.replace("::", "/").replace("crate", "src")
        candidates.append(f"{clean}.rs")
        candidates.append(f"{clean}/mod.rs")

    elif ext in (".java", ".kt", ".kts"):
        # Java/Kotlin: com.example.Foo -> com/example/Foo.java
        clean = source.replace(".", "/")
        candidates.append(f"{clean}.java")
        candidates.append(f"{clean}.kt")

    elif ext in (".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx"):
        # C/C++: #include "foo.h" -> search
        clean = source.strip('"<>')
        candidates.append(clean)
        if file_dir:
            candidates.append(f"{file_dir}/{clean}")

    elif ext == ".cs":
        # C#: using Namespace -> search
        clean = source.replace(".", "/")
        candidates.append(f"{clean}.cs")

    elif ext == ".rb":
        # Ruby: require "foo" -> lib/foo.rb
        clean = source.strip("'\"")
        candidates.append(f"{clean}.rb")
        candidates.append(f"lib/{clean}.rb")

    elif ext == ".php":
        # PHP: use Foo\Bar -> Foo/Bar.php
        clean = source.replace("\\", "/")
        candidates.append(f"{clean}.php")

    elif ext == ".swift":
        # Swift: import Framework — usually external, skip
        pass

    return candidates
