# -*- encoding: utf-8 -*-

"""
Regression test: importing :mod:`arcline.io` must populate the
graph registry with the built-in taxonomy.

Without the side-effect import in ``arcline/io/__init__.py``, the
``arcline dashboard`` and ``arcline validate`` CLI entrypoints fail
with ``unknown-node-kind`` errors because nothing else along their
import chain triggers ``arcline.graph.library``.
"""

from __future__ import annotations

import subprocess
import sys


_PROBE = (
    "from arcline.io import Project;"
    "from arcline.graph.registry import resolve_node, resolve_edge;"
    "_=[resolve_node(k) for k in"
    "   ('supplier','plant','warehouse','customer')];"
    "_=[resolve_edge(k) for k in"
    "   ('lane','production','storage')];"
    "print('registry-ok')"
)


def test_arclineIo_pre_imports_library_taxonomy():
    """
    Spawning a clean Python subprocess and importing only
    ``arcline.io`` must make every shipped node and edge ``kind``
    resolvable through the registry.
    """

    proc = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output = True, text = True,
        encoding = "utf-8", errors = "replace",
    )
    assert proc.returncode == 0, proc.stderr
    assert "registry-ok" in proc.stdout
