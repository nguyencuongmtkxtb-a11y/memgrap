# Phase 1: AST Parser Module

## Overview
- **Priority:** High (foundation)
- **Status:** Pending
- **Description:** tree-sitter parser extracts code symbols from Python/JS/TS files

## Requirements
### Functional
- Parse Python, JavaScript, TypeScript files
- Extract: functions, classes, imports
- Return structured CodeSymbol with name, kind, line, parent scope, file_path
- Handle nested scopes (class methods, inner functions)

### Non-functional
- <1s for 500-file codebase
- Error-tolerant (tree-sitter handles broken syntax)

## Architecture
```
src/indexer/__init__.py
src/indexer/ast-parser.py
  - CodeSymbol (dataclass): name, kind, line, parent, file_path
  - LANG_REGISTRY: dict mapping extension → (Language, queries)
  - parse_file(path) → list[CodeSymbol]
  - parse_directory(path, extensions) → list[CodeSymbol]
```

## Dependencies
```toml
tree-sitter, tree-sitter-python, tree-sitter-javascript, tree-sitter-typescript
```

## Implementation Steps
1. Add tree-sitter deps to pyproject.toml
2. Create `src/indexer/__init__.py`
3. Create `src/indexer/ast-parser.py`:
   - CodeSymbol dataclass
   - LANG_REGISTRY: {".py": python, ".js": js, ".ts": ts, ".tsx": tsx}
   - S-expression queries per language (func_def, class_def, import)
   - parse_file() with scope tracking
   - parse_directory() with default ignore patterns (__pycache__, node_modules, .git)
4. Test: parse memgrap's own `src/`

## Success Criteria
- `parse_directory("src/")` returns all functions/classes/imports from memgrap
- Syntax errors don't crash
- <1s for 500 files
