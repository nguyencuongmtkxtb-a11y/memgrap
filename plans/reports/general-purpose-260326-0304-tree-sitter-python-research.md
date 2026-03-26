# Tree-sitter Python Bindings Research

## 1. Package Comparison

| Package | Status | PyPI Name | Latest | Python |
|---------|--------|-----------|--------|--------|
| **py-tree-sitter** (official) | Active | `tree-sitter` | 0.25.2 (Sep 2025) | 3.10+ |
| **tree-sitter-language-pack** | Active | `tree-sitter-language-pack` | 0.13.0 (Mar 2026) | 3.10+ |
| **tree-sitter-languages** | DEAD | `tree-sitter-languages` | 1.10.2 (Feb 2024) | pinned to tree-sitter==0.21.3 |

### Recommendation

**Option A — Individual packages (best control):**
```bash
pip install tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript
```

**Option B — All-in-one bundle (convenience, 248 langs):**
```bash
pip install tree-sitter-language-pack
```

Option A = smaller footprint, official. Option B = easier multi-language support, has built-in `process()` for structure extraction.

Do NOT use `tree-sitter-languages` — unmaintained, incompatible with tree-sitter >= 0.22.

---

## 2. Setup Per Language

### Option A: Individual packages

```python
# Python
import tree_sitter_python as tspython
from tree_sitter import Language, Parser
PY_LANG = Language(tspython.language())

# JavaScript
import tree_sitter_javascript as tsjs
JS_LANG = Language(tsjs.language())

# TypeScript (TWO grammars: TS and TSX)
import tree_sitter_typescript as tsts
TS_LANG = Language(tsts.language_typescript())
TSX_LANG = Language(tsts.language_tsx())

parser = Parser(PY_LANG)  # pass language to constructor
tree = parser.parse(b"def hello(): pass")
```

### Option B: Language pack

```python
from tree_sitter_language_pack import get_parser, get_language

parser = get_parser("python")
tree = parser.parse(b"def hello(): pass")

# Or use the high-level process() API
from tree_sitter_language_pack import process, ProcessConfig
result = process("def hello(): pass", ProcessConfig(language="python"))
# Returns: { 'structure': [...], 'chunks': [...] }
```

---

## 3. Extracting Functions, Classes, Imports

### Via Query API (S-expression pattern matching)

```python
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY_LANG = Language(tspython.language())
parser = Parser(PY_LANG)

code = b"""
import os
from sys import argv

class MyClass:
    def method(self):
        pass

def my_function(x: int) -> str:
    return str(x)
"""

tree = parser.parse(code)

# -- Python queries --
query = PY_LANG.query("""
(function_definition
  name: (identifier) @func.name
  parameters: (parameters) @func.params) @func.def

(class_definition
  name: (identifier) @class.name) @class.def

(import_statement) @import
(import_from_statement) @import.from
""")

captures = query.captures(tree.root_node)
# Returns dict: { "func.name": [Node, ...], "class.name": [Node, ...], ... }
for name, nodes in captures.items():
    for node in nodes:
        print(f"{name}: L{node.start_point.row+1} {node.text.decode()}")
```

### JavaScript/TypeScript queries

```python
# JS function extraction
JS_QUERY = """
(function_declaration
  name: (identifier) @func.name) @func.def

(arrow_function) @func.arrow

(class_declaration
  name: (identifier) @class.name) @class.def

(import_statement) @import
(export_statement) @export
"""

# TypeScript adds:
TS_QUERY_EXTRA = """
(interface_declaration
  name: (type_identifier) @interface.name) @interface.def

(type_alias_declaration
  name: (type_identifier) @type.name) @type.def
"""
```

### Node properties available

```python
node.type          # "function_definition", "class_definition", etc.
node.text          # bytes — raw source text
node.start_point   # Point(row, column)
node.end_point     # Point(row, column)
node.children      # list of child nodes
node.named_children  # only named children (skip punctuation)
node.parent        # parent node
node.child_by_field_name("name")  # get child by grammar field
node.is_named      # True if named node (not punctuation/keywords)
```

---

## 4. AST Traversal

### TreeCursor (efficient, iterative — recommended for large files)

```python
from tree_sitter import Tree, Node
from typing import Generator

def traverse_tree(tree: Tree) -> Generator[Node, None, None]:
    """Depth-first pre-order traversal using TreeCursor."""
    cursor = tree.walk()
    visited_children = False
    while True:
        if not visited_children:
            yield cursor.node
            if not cursor.goto_first_child():
                visited_children = True
        elif cursor.goto_next_sibling():
            visited_children = False
        elif not cursor.goto_parent():
            break
```

### Simple recursive (fine for small files)

```python
def traverse(node, depth=0):
    print(f"{'  '*depth}{node.type}: {node.text.decode()[:50]}")
    for child in node.children:
        traverse(child, depth + 1)
```

### Targeted extraction (most practical for code indexing)

```python
def extract_symbols(tree, language):
    """Extract all top-level and nested symbols."""
    query = language.query("""
    (function_definition name: (identifier) @func.name) @func.def
    (class_definition name: (identifier) @class.name) @class.def
    (import_statement) @import
    (import_from_statement) @import.from
    """)

    captures = query.captures(tree.root_node)
    symbols = []

    for capture_name, nodes in captures.items():
        for node in nodes:
            symbols.append({
                "type": capture_name,
                "name": node.text.decode(),
                "line_start": node.start_point.row + 1,
                "line_end": node.end_point.row + 1,
                "parent": node.parent.type if node.parent else None,
            })
    return symbols
```

---

## 5. Language Grammars Needed

### Individual packages (Option A)

| Language | Package | Import | Grammar function |
|----------|---------|--------|-----------------|
| Python | `tree-sitter-python` | `tree_sitter_python` | `.language()` |
| JavaScript | `tree-sitter-javascript` | `tree_sitter_javascript` | `.language()` |
| TypeScript | `tree-sitter-typescript` | `tree_sitter_typescript` | `.language_typescript()` |
| TSX | `tree-sitter-typescript` | `tree_sitter_typescript` | `.language_tsx()` |

Note: TypeScript package has TWO grammars. TSX parser also handles JS with Flow annotations.

### Language pack (Option B)

```python
from tree_sitter_language_pack import get_language
# Just use string names: "python", "javascript", "typescript", "tsx"
```

### Key node types per language

**Python:** `function_definition`, `class_definition`, `import_statement`, `import_from_statement`, `decorated_definition`, `module`

**JavaScript:** `function_declaration`, `arrow_function`, `class_declaration`, `import_statement`, `export_statement`, `variable_declaration`, `method_definition`

**TypeScript:** All JS types + `interface_declaration`, `type_alias_declaration`, `enum_declaration`

---

## 6. Performance Considerations

### Parsing speed
- Tree-sitter is written in C (called via Python bindings) — very fast
- Benchmarks: 25x-52x faster than alternatives (JavaParser, regex-based parsers)
- Helix-Lint: 1M lines in < 10 seconds
- Typical Python file (500 LOC): < 1ms to parse

### Incremental parsing
- `tree.edit()` + `parser.parse(new_source, old_tree)` — only reparses changed regions
- Critical for watch-mode / real-time indexing
- Not needed for batch indexing (full parse is fast enough)

### Memory
- Trees share structure — editing creates new tree reusing unchanged subtree nodes
- For batch processing: parse file, extract, discard tree — no accumulation
- `node.text` returns bytes view into source, not copies

### Best practices for large codebases
- **Batch parse**: iterate files, parse each, extract symbols, discard tree
- **Don't hold trees in memory** unless doing incremental updates
- **Use TreeCursor** over recursive `.children` access for large files (avoids Python object creation overhead)
- **Use queries** over manual traversal when possible — query engine is in C, much faster than Python loops
- **Parallelize**: tree-sitter is thread-safe for parsing different files (each parser instance)
- **File size**: tree-sitter handles 100K+ line files fine; Python binding overhead is the bottleneck

### Estimated indexing throughput
- ~1,000-5,000 files/second for symbol extraction (parse + query)
- Bottleneck is usually file I/O, not parsing
- For a 10K-file codebase: 2-10 seconds total

---

## 7. Install Commands (Final)

```bash
# Option A: Minimal, individual grammars
pip install tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript

# Option B: All-in-one (248 languages, has process() API)
pip install tree-sitter-language-pack
```

Both work on Python 3.11 + Windows 10 via pre-built wheels — no compilation needed.

---

## Sources

- [py-tree-sitter docs](https://tree-sitter.github.io/py-tree-sitter/)
- [py-tree-sitter GitHub](https://github.com/tree-sitter/py-tree-sitter)
- [tree-sitter-language-pack PyPI](https://pypi.org/project/tree-sitter-language-pack/)
- [tree-sitter-language-pack GitHub](https://github.com/Goldziher/tree-sitter-language-pack)
- [tree-sitter-typescript PyPI](https://pypi.org/project/tree-sitter-typescript/)
- [Simon Willison's tree-sitter TIL](https://til.simonwillison.net/python/tree-sitter)
- [tree-sitter-haskell 50x speedup](https://owen.cafe/posts/tree-sitter-haskell-perf/)
