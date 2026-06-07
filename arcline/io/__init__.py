# -*- encoding: utf-8 -*-

"""
Project I/O Layer
=================

Pure I/O helpers for reading and writing :mod:`arcline` project
artifacts to and from disk. The canonical on-disk format is JSON
(diff-friendly, git-versionable); YAML and Parquet variants exist for
configuration ergonomics and bulk-data workflows respectively.

The :class:`Project` facade ties readers, writers, and the cross-file
:func:`validate_project` integrity checks together into a single
ergonomic API for the dashboard and CLI layers.
"""

from arcline.io.schema import (
    EDGES_SCHEMA,
    MANIFEST_SCHEMA,
    MANIFEST_SCHEMA_VERSION,
    NODES_SCHEMA,
)
from arcline.io.validators import ValidationIssue, validate_project
from arcline.io.readers import (
    from_csv,
    from_json,
    from_parquet,
    from_yaml,
)
from arcline.io.writers import to_json, to_parquet, to_yaml
from arcline.io.project import Project

__all__ = [
    "Project",
    "from_json",
    "from_yaml",
    "from_parquet",
    "from_csv",
    "to_json",
    "to_yaml",
    "to_parquet",
    "validate_project",
    "ValidationIssue",
    "MANIFEST_SCHEMA_VERSION",
    "NODES_SCHEMA",
    "EDGES_SCHEMA",
    "MANIFEST_SCHEMA",
]
