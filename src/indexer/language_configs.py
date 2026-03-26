"""Language configurations for tree-sitter AST parsing.

Defines S-expression queries and language objects for each supported language.
New languages are loaded via optional try/except imports — missing packages
are skipped gracefully so the indexer still works for installed languages.
"""

import logging
from dataclasses import dataclass, field

from tree_sitter import Language, Parser, Query

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class LangConfig:
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


# ---------------------------------------------------------------------------
# S-expression queries per language
# ---------------------------------------------------------------------------

PYTHON_QUERY = """
(function_definition name: (identifier) @func.name) @func.def
(class_definition name: (identifier) @class.name) @class.def
(import_statement) @import.stmt
(import_from_statement module_name: (dotted_name) @import.module) @import.from
"""

JS_QUERY = """
(function_declaration name: (identifier) @func.name) @func.def
(class_declaration name: (identifier) @class.name) @class.def
(import_statement) @import.stmt
(export_statement declaration: (function_declaration name: (identifier) @func.name)) @export.func
(export_statement declaration: (class_declaration name: (identifier) @class.name)) @export.class
"""

# TS uses same grammar shape as JS — queries are compatible
TS_QUERY = JS_QUERY

GO_QUERY = """
(function_declaration name: (identifier) @func.name) @func.def
(method_declaration name: (field_identifier) @func.name) @func.def
(type_declaration (type_spec name: (type_identifier) @class.name)) @class.def
(import_declaration) @import.stmt
"""

RUST_QUERY = """
(function_item name: (identifier) @func.name) @func.def
(impl_item type: (type_identifier) @class.name) @class.def
(struct_item name: (type_identifier) @class.name) @class.def
(enum_item name: (type_identifier) @class.name) @class.def
(trait_item name: (type_identifier) @class.name) @class.def
(use_declaration) @import.stmt
"""

JAVA_QUERY = """
(method_declaration name: (identifier) @func.name) @func.def
(constructor_declaration name: (identifier) @func.name) @func.def
(class_declaration name: (identifier) @class.name) @class.def
(interface_declaration name: (identifier) @class.name) @class.def
(import_declaration) @import.stmt
"""

C_QUERY = """
(function_definition declarator: (function_declarator declarator: (identifier) @func.name)) @func.def
(struct_specifier name: (type_identifier) @class.name) @class.def
(enum_specifier name: (type_identifier) @class.name) @class.def
(preproc_include) @import.stmt
"""

CPP_QUERY = """
(function_definition declarator: (function_declarator declarator: (identifier) @func.name)) @func.def
(function_definition declarator: (function_declarator declarator: (qualified_identifier name: (identifier) @func.name))) @func.def
(class_specifier name: (type_identifier) @class.name) @class.def
(struct_specifier name: (type_identifier) @class.name) @class.def
(namespace_definition name: (namespace_identifier) @class.name) @class.def
(preproc_include) @import.stmt
"""

CSHARP_QUERY = """
(method_declaration name: (identifier) @func.name) @func.def
(constructor_declaration name: (identifier) @func.name) @func.def
(class_declaration name: (identifier) @class.name) @class.def
(interface_declaration name: (identifier) @class.name) @class.def
(struct_declaration name: (identifier) @class.name) @class.def
(using_directive) @import.stmt
"""

RUBY_QUERY = """
(method name: (identifier) @func.name) @func.def
(singleton_method name: (identifier) @func.name) @func.def
(class name: (constant) @class.name) @class.def
(module name: (constant) @class.name) @class.def
(call method: (identifier) @import.name (#eq? @import.name "require")) @import.stmt
"""

PHP_QUERY = """
(function_definition name: (name) @func.name) @func.def
(method_declaration name: (name) @func.name) @func.def
(class_declaration name: (name) @class.name) @class.def
(interface_declaration name: (name) @class.name) @class.def
(trait_declaration name: (name) @class.name) @class.def
(namespace_use_declaration) @import.stmt
"""


# ---------------------------------------------------------------------------
# Registry builder — each language loaded via optional import
# ---------------------------------------------------------------------------

def _try_register(
    registry: dict[str, LangConfig],
    module_name: str,
    query: str,
    extensions: list[str],
    lang_attr: str = "language",
) -> None:
    """Import a tree-sitter-* module and register its extensions.

    Args:
        registry: dict to populate
        module_name: e.g. "tree_sitter_go"
        query: S-expression query string
        extensions: file extensions to map (e.g. [".go"])
        lang_attr: attribute name on module that returns the language ptr
    """
    try:
        import importlib
        mod = importlib.import_module(module_name)
        lang = Language(getattr(mod, lang_attr)())
        for ext in extensions:
            registry[ext] = LangConfig(lang, query)
    except (ImportError, AttributeError):
        log.debug("%s not installed, skipping %s support", module_name, extensions)


def _build_registry() -> dict[str, LangConfig]:
    """Build extension-to-LangConfig map, skipping unavailable languages."""
    registry: dict[str, LangConfig] = {}

    # Required languages (always installed with memgrap)
    import tree_sitter_python as ts_python
    import tree_sitter_javascript as ts_javascript
    import tree_sitter_typescript as ts_typescript

    py_lang = Language(ts_python.language())
    js_lang = Language(ts_javascript.language())
    ts_lang = Language(ts_typescript.language_typescript())
    tsx_lang = Language(ts_typescript.language_tsx())

    registry[".py"] = LangConfig(py_lang, PYTHON_QUERY)
    registry[".js"] = LangConfig(js_lang, JS_QUERY)
    registry[".jsx"] = LangConfig(js_lang, JS_QUERY)
    registry[".ts"] = LangConfig(ts_lang, TS_QUERY)
    registry[".tsx"] = LangConfig(tsx_lang, TS_QUERY)

    # Optional languages — skip gracefully if not installed
    _try_register(registry, "tree_sitter_go", GO_QUERY, [".go"])
    _try_register(registry, "tree_sitter_rust", RUST_QUERY, [".rs"])
    _try_register(registry, "tree_sitter_java", JAVA_QUERY, [".java"])
    _try_register(registry, "tree_sitter_c", C_QUERY, [".c", ".h"])
    _try_register(registry, "tree_sitter_cpp", CPP_QUERY, [".cpp", ".cc", ".cxx", ".hpp", ".hxx"])
    _try_register(registry, "tree_sitter_c_sharp", CSHARP_QUERY, [".cs"])
    _try_register(registry, "tree_sitter_ruby", RUBY_QUERY, [".rb"])
    _try_register(registry, "tree_sitter_php", PHP_QUERY, [".php"], lang_attr="language_php")

    return registry


LANG_REGISTRY: dict[str, LangConfig] = _build_registry()
