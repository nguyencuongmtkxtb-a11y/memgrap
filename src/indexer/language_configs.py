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
    relation_query_src: str = ""
    _parser: Parser = field(default=None, init=False, repr=False)
    _query: object = field(default=None, init=False, repr=False)
    _relation_query: object = field(default=None, init=False, repr=False)

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

    @property
    def relation_query(self) -> Query | None:
        if not self.relation_query_src:
            return None
        if self._relation_query is None:
            self._relation_query = Query(self.language, self.relation_query_src)
        return self._relation_query


# ---------------------------------------------------------------------------
# S-expression queries per language
# ---------------------------------------------------------------------------

PYTHON_QUERY = """
(function_definition name: (identifier) @func.name) @func.def
(class_definition name: (identifier) @class.name) @class.def
(import_statement) @import.stmt
(import_from_statement module_name: (dotted_name) @import.module) @import.from
"""

PYTHON_RELATION_QUERY = """
(call function: (identifier) @call.name)
(call function: (attribute attribute: (identifier) @call.name))
(class_definition superclasses: (argument_list (identifier) @extends.name))
(import_from_statement module_name: (dotted_name) @import.source)
"""

JS_QUERY = """
(function_declaration name: (identifier) @func.name) @func.def
(class_declaration name: (identifier) @class.name) @class.def
(import_statement) @import.stmt
(export_statement declaration: (function_declaration name: (identifier) @func.name)) @export.func
(export_statement declaration: (class_declaration name: (identifier) @class.name)) @export.class
"""

JS_RELATION_QUERY = """
(call_expression function: (identifier) @call.name)
(call_expression function: (member_expression property: (property_identifier) @call.name))
(class_declaration (class_heritage (identifier) @extends.name))
(import_statement source: (string) @import.source)
"""

# TS grammar uses type_identifier for class names (not identifier like JS)
TS_QUERY = """
(function_declaration name: (identifier) @func.name) @func.def
(class_declaration name: (type_identifier) @class.name) @class.def
(import_statement) @import.stmt
(export_statement declaration: (function_declaration name: (identifier) @func.name)) @export.func
(export_statement declaration: (class_declaration name: (type_identifier) @class.name)) @export.class
"""

TS_RELATION_QUERY = """
(call_expression function: (identifier) @call.name)
(call_expression function: (member_expression property: (property_identifier) @call.name))
(class_heritage (extends_clause value: (identifier) @extends.name))
(import_statement source: (string) @import.source)
"""

GO_QUERY = """
(function_declaration name: (identifier) @func.name) @func.def
(method_declaration name: (field_identifier) @func.name) @func.def
(type_declaration (type_spec name: (type_identifier) @class.name)) @class.def
(import_declaration) @import.stmt
"""

GO_RELATION_QUERY = """
(call_expression function: (identifier) @call.name)
(call_expression function: (selector_expression field: (field_identifier) @call.name))
(import_spec path: (interpreted_string_literal) @import.source)
"""

RUST_QUERY = """
(function_item name: (identifier) @func.name) @func.def
(impl_item type: (type_identifier) @class.name) @class.def
(struct_item name: (type_identifier) @class.name) @class.def
(enum_item name: (type_identifier) @class.name) @class.def
(trait_item name: (type_identifier) @class.name) @class.def
(use_declaration) @import.stmt
"""

RUST_RELATION_QUERY = """
(call_expression function: (identifier) @call.name)
(call_expression function: (field_expression field: (field_identifier) @call.name))
(call_expression function: (scoped_identifier name: (identifier) @call.name))
(use_declaration argument: (scoped_identifier) @import.source)
(impl_item trait: (type_identifier) @extends.name)
"""

JAVA_QUERY = """
(method_declaration name: (identifier) @func.name) @func.def
(constructor_declaration name: (identifier) @func.name) @func.def
(class_declaration name: (identifier) @class.name) @class.def
(interface_declaration name: (identifier) @class.name) @class.def
(import_declaration) @import.stmt
"""

JAVA_RELATION_QUERY = """
(method_invocation name: (identifier) @call.name)
(class_declaration (superclass (type_identifier) @extends.name))
(class_declaration (super_interfaces (type_list (type_identifier) @extends.name)))
"""

C_QUERY = """
(function_definition declarator: (function_declarator declarator: (identifier) @func.name)) @func.def
(struct_specifier name: (type_identifier) @class.name) @class.def
(enum_specifier name: (type_identifier) @class.name) @class.def
(preproc_include) @import.stmt
"""

C_RELATION_QUERY = """
(call_expression function: (identifier) @call.name)
(call_expression function: (field_expression field: (field_identifier) @call.name))
(preproc_include path: (string_literal) @import.source)
(preproc_include path: (system_lib_string) @import.source)
"""

CPP_QUERY = """
(function_definition declarator: (function_declarator declarator: (identifier) @func.name)) @func.def
(function_definition declarator: (function_declarator declarator: (qualified_identifier name: (identifier) @func.name))) @func.def
(class_specifier name: (type_identifier) @class.name) @class.def
(struct_specifier name: (type_identifier) @class.name) @class.def
(namespace_definition name: (namespace_identifier) @class.name) @class.def
(preproc_include) @import.stmt
"""

CPP_RELATION_QUERY = """
(call_expression function: (identifier) @call.name)
(call_expression function: (field_expression field: (field_identifier) @call.name))
(call_expression function: (qualified_identifier name: (identifier) @call.name))
(base_class_clause (type_identifier) @extends.name)
(preproc_include path: (string_literal) @import.source)
(preproc_include path: (system_lib_string) @import.source)
"""

CSHARP_QUERY = """
(method_declaration name: (identifier) @func.name) @func.def
(constructor_declaration name: (identifier) @func.name) @func.def
(class_declaration name: (identifier) @class.name) @class.def
(interface_declaration name: (identifier) @class.name) @class.def
(struct_declaration name: (identifier) @class.name) @class.def
(using_directive) @import.stmt
"""

CSHARP_RELATION_QUERY = """
(invocation_expression function: (identifier) @call.name)
(invocation_expression function: (member_access_expression name: (identifier) @call.name))
(class_declaration (base_list (identifier) @extends.name))
(using_directive (identifier) @import.source)
"""

RUBY_QUERY = """
(method name: (identifier) @func.name) @func.def
(singleton_method name: (identifier) @func.name) @func.def
(class name: (constant) @class.name) @class.def
(module name: (constant) @class.name) @class.def
(call method: (identifier) @import.name (#eq? @import.name "require")) @import.stmt
"""

RUBY_RELATION_QUERY = """
(call method: (identifier) @call.name)
(class superclass: (superclass (constant) @extends.name))
"""

PHP_QUERY = """
(function_definition name: (name) @func.name) @func.def
(method_declaration name: (name) @func.name) @func.def
(class_declaration name: (name) @class.name) @class.def
(interface_declaration name: (name) @class.name) @class.def
(trait_declaration name: (name) @class.name) @class.def
(namespace_use_declaration) @import.stmt
"""

PHP_RELATION_QUERY = """
(function_call_expression function: (name) @call.name)
(member_call_expression name: (name) @call.name)
(class_declaration (base_clause (name) @extends.name))
(namespace_use_declaration (namespace_use_clause (qualified_name) @import.source))
"""

# Kotlin grammar uses identifier (not simple_identifier/type_identifier)
# interface_declaration doesn't exist — interfaces are class_declaration nodes
KOTLIN_QUERY = """
(function_declaration (identifier) @func.name) @func.def
(class_declaration (identifier) @class.name) @class.def
(object_declaration (identifier) @class.name) @class.def
(import) @import.stmt
"""

KOTLIN_RELATION_QUERY = """
(call_expression (identifier) @call.name)
(delegation_specifier (constructor_invocation (user_type (identifier) @extends.name)))
(delegation_specifier (user_type (identifier) @extends.name))
(import (qualified_identifier) @import.source)
"""

# Swift grammar: structs/enums are also class_declaration nodes
SWIFT_QUERY = """
(function_declaration name: (simple_identifier) @func.name) @func.def
(class_declaration name: (type_identifier) @class.name) @class.def
(protocol_declaration name: (type_identifier) @class.name) @class.def
(import_declaration) @import.stmt
"""

SWIFT_RELATION_QUERY = """
(call_expression (simple_identifier) @call.name)
(inheritance_specifier (user_type (type_identifier) @extends.name))
(import_declaration (identifier) @import.source)
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
    relation_query: str = "",
) -> None:
    """Import a tree-sitter-* module and register its extensions.

    Args:
        registry: dict to populate
        module_name: e.g. "tree_sitter_go"
        query: S-expression query string
        extensions: file extensions to map (e.g. [".go"])
        lang_attr: attribute name on module that returns the language ptr
        relation_query: S-expression for call/extends/import-source extraction
    """
    try:
        import importlib
        mod = importlib.import_module(module_name)
        lang = Language(getattr(mod, lang_attr)())
        for ext in extensions:
            registry[ext] = LangConfig(lang, query, relation_query)
    except (ImportError, AttributeError):
        log.debug("%s not installed, skipping %s support", module_name, extensions)


def _build_registry() -> dict[str, LangConfig]:
    """Build extension-to-LangConfig map, skipping unavailable languages."""
    registry: dict[str, LangConfig] = {}

    # Required languages (always installed with memgrap)
    import tree_sitter_javascript as ts_javascript
    import tree_sitter_python as ts_python
    import tree_sitter_typescript as ts_typescript

    py_lang = Language(ts_python.language())
    js_lang = Language(ts_javascript.language())
    ts_lang = Language(ts_typescript.language_typescript())
    tsx_lang = Language(ts_typescript.language_tsx())

    registry[".py"] = LangConfig(py_lang, PYTHON_QUERY, PYTHON_RELATION_QUERY)
    registry[".js"] = LangConfig(js_lang, JS_QUERY, JS_RELATION_QUERY)
    registry[".jsx"] = LangConfig(js_lang, JS_QUERY, JS_RELATION_QUERY)
    registry[".ts"] = LangConfig(ts_lang, TS_QUERY, TS_RELATION_QUERY)
    registry[".tsx"] = LangConfig(tsx_lang, TS_QUERY, TS_RELATION_QUERY)

    # Optional languages — skip gracefully if not installed
    _try_register(registry, "tree_sitter_go", GO_QUERY, [".go"], relation_query=GO_RELATION_QUERY)
    _try_register(registry, "tree_sitter_rust", RUST_QUERY, [".rs"], relation_query=RUST_RELATION_QUERY)
    _try_register(registry, "tree_sitter_java", JAVA_QUERY, [".java"], relation_query=JAVA_RELATION_QUERY)
    _try_register(registry, "tree_sitter_c", C_QUERY, [".c", ".h"], relation_query=C_RELATION_QUERY)
    _try_register(registry, "tree_sitter_cpp", CPP_QUERY, [".cpp", ".cc", ".cxx", ".hpp", ".hxx"], relation_query=CPP_RELATION_QUERY)
    _try_register(registry, "tree_sitter_c_sharp", CSHARP_QUERY, [".cs"], relation_query=CSHARP_RELATION_QUERY)
    _try_register(registry, "tree_sitter_ruby", RUBY_QUERY, [".rb"], relation_query=RUBY_RELATION_QUERY)
    _try_register(registry, "tree_sitter_php", PHP_QUERY, [".php"], lang_attr="language_php", relation_query=PHP_RELATION_QUERY)
    _try_register(registry, "tree_sitter_kotlin", KOTLIN_QUERY, [".kt", ".kts"], relation_query=KOTLIN_RELATION_QUERY)
    _try_register(registry, "tree_sitter_swift", SWIFT_QUERY, [".swift"], relation_query=SWIFT_RELATION_QUERY)

    return registry


LANG_REGISTRY: dict[str, LangConfig] = _build_registry()
