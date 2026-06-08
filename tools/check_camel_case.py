# -*- encoding: utf-8 -*-

"""
camelCase Naming Convention Checker
-----------------------------------

A tiny, dependency-free pre-commit / CI gate that enforces the
:mod:`arcline` strict camelCase convention. The repository style is::

    * Class names         : PascalCase (e.g., ``AbstractNode``)
    * Functions / methods : camelCase  (e.g., ``makeKey``, ``bindProject``)
    * Parameters / locals : camelCase  (e.g., ``srcKey``, ``hashKey``)
    * Pydantic attributes : camelCase  (e.g., ``leadTimeDays``)
    * Constants / env vars: UPPER_SNAKE_CASE (e.g., ``ARCLINE_MSSQL_DSN``)

The default Python convention (PEP-8 snake_case) is allowed only for:

    * Test functions (``def test_*``)
    * Pytest fixtures named ``test_*`` / ``tmp_path`` / ``capsys`` / ...
    * Python dunder methods (``__init__``, ``__set_name__``, ...)
    * Externally-mandated kwargs (Dash, Pydantic, Typer, networkx,
      pandas, SQLAlchemy) - listed in ``EXEMPT_NAMES``
    * Module / file names (PEP-328 module path convention is retained
      because renaming files cascades into every import everywhere)
    * Explicitly-tagged deprecated aliases (see
      ``arcline/io/__init__.py`` and ``arcline/utils/__init__.py``)
    * The legacy graph registry (``arcline/graph/registry.py``) is
      grandfathered as an existing public API. Future re-issues may
      migrate it to camelCase under a deprecation window.

Usage
~~~~~

    python tools/check_camel_case.py            # full repo
    python tools/check_camel_case.py arcline/   # specific subtree

Exit codes
~~~~~~~~~~

    0 - no violations
    1 - at least one violation

The script is intentionally lint-pass-only - it does not auto-fix.
"""

import ast
import re
import sys
from pathlib import Path
from typing import Iterable, List, Set, Tuple


EXEMPT_NAMES: Set[str] = {
    # Python stdlib / dunder fragments
    "exc_info", "is_alive", "digest_size",
    # Pytest
    "tmp_path", "tmp_path_factory", "capsys", "monkeypatch",
    # Pydantic v2
    "model_dump", "model_copy", "model_validate", "model_fields",
    "model_config", "model_extra", "model_construct",
    "model_dump_json", "field_validator", "model_validator",
    "default_factory", "field_info",
    # Typer / Click
    "no_args_is_help", "add_completion",
    # Dash component base class (custom-component contract)
    "available_properties", "available_wildcard_properties",
    # Dash component props / kwargs
    "n_clicks", "is_open", "no_update", "page_container",
    "register_page", "prevent_initial_call", "allow_duplicate",
    "triggered_id", "add_clicks", "cancel_clicks", "save_clicks",
    "use_pages", "pages_folder", "external_stylesheets",
    "suppress_callback_exceptions", "run_server",
    # Dash table / AG-Grid
    "dash_table", "dash_ag_grid", "column_defs", "page_size",
    "row_selectable", "style_cell", "style_table", "html_for",
    # NetworkX
    "add_edge", "add_node", "add_nodes_from", "has_edge", "has_node",
    "in_degree", "out_degree", "remove_edge", "remove_node",
    "spring_layout", "multipartite_layout", "shell_layout",
    "edge_keys",
    # Pandas
    "read_csv", "read_parquet", "to_dict", "to_csv", "to_parquet",
    "set_index", "reset_index", "drop_duplicates", "fillna", "isna",
    "to_datetime", "to_timedelta", "date_range",
    # YAML / JSON
    "safe_load", "safe_dump", "sort_keys", "default_flow_style",
    "ensure_ascii", "exclude_unset", "exclude_none",
    # Pathlib / os
    "exist_ok", "st_size", "write_text", "token_hex",
    # logging stdlib
    "asctime", "levelname",
    # typing
    "get_args", "get_origin",
    # functools / importlib
    "lru_cache", "import_module", "pkg_resources",
    # plotly
    "graph_objects",
    # pydantic-settings / flask
    "env_prefix", "pydantic_settings", "flask_caching",
    # SQLAlchemy / pyodbc (Phase 1.5)
    "primary_key", "foreign_key", "create_engine", "text_clause",
    # Dash bootstrap components import alias
    "dash_bootstrap_components",
    # arcline.graph.registry (grandfathered legacy public API)
    "register_node", "register_edge", "resolve_node", "resolve_edge",
    "iter_nodes", "iter_edges", "clear_registry",
    # arcline.io/utils deprecated camelCase shim names (intentional)
    "from_json", "from_yaml", "from_parquet", "from_csv",
    "to_json", "to_json_records", "to_yaml",
    "validate_project",
    "make_key", "make_node_key", "make_edge_key",
    "configure_logging", "get_logger",
}

EXEMPT_PREFIXES: Tuple[str, ...] = (
    "_",          # private / protected
    "test_",      # pytest test functions
)

SNAKE_NAME_RE = re.compile(r"^[a-z]+(?:_[a-z0-9]+)+$")


def isSnakeCase(name: str) -> bool:
    """Return ``True`` when ``name`` is a snake_case identifier we own."""
    if name in EXEMPT_NAMES:
        return False
    if any(name.startswith(p) for p in EXEMPT_PREFIXES):
        return False
    return bool(SNAKE_NAME_RE.match(name))


class CamelCaseVisitor(ast.NodeVisitor):
    """Walk an AST and collect ``(lineno, name, kind)`` for every snake_case identifier we own."""

    def __init__(self) -> None:
        self.violations: List[Tuple[int, str, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if isSnakeCase(node.name):
            self.violations.append((node.lineno, node.name, "function"))
        for arg in (
            node.args.args + node.args.kwonlyargs + node.args.posonlyargs
        ):
            if isSnakeCase(arg.arg):
                self.violations.append((arg.lineno, arg.arg, "param"))
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_Assign(self, node: ast.Assign) -> None:
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and isSnakeCase(tgt.id):
                self.violations.append((tgt.lineno, tgt.id, "variable"))
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and isSnakeCase(node.target.id):
            self.violations.append(
                (node.target.lineno, node.target.id, "variable")
            )
        self.generic_visit(node)


def checkFile(path: Path) -> List[Tuple[int, str, str]]:
    """Return a list of ``(lineno, name, kind)`` violations for ``path``."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    visitor = CamelCaseVisitor()
    visitor.visit(tree)
    return visitor.violations


def iterTargets(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            yield root
        elif root.is_dir():
            for p in root.rglob("*.py"):
                if "__pycache__" in p.parts:
                    continue
                yield p


def main(argv: List[str]) -> int:
    roots = [Path(a) for a in argv[1:]] or [Path("arcline"), Path("tests")]
    totalViolations = 0
    for path in iterTargets(roots):
        violations = checkFile(path)
        if not violations:
            continue
        for lineno, name, kind in violations:
            print(f"{path}:{lineno}: snake_case {kind} {name!r}")
            totalViolations += 1
    if totalViolations:
        print(
            f"\n{totalViolations} naming-convention violation(s) found. "
            f"All non-exempt identifiers must use camelCase. See "
            f"tools/check_camel_case.py for the exemption list.",
            file=sys.stderr,
        )
        return 1
    print("OK: no naming-convention violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
