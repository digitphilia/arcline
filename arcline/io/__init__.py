# -*- encoding: utf-8 -*-

"""
Project I/O Layer
=================

Pure I/O helpers for reading and writing :mod:`arcline` project
artifacts to and from disk. The canonical on-disk format is JSON
(diff-friendly, git-versionable); YAML and Parquet variants exist for
configuration ergonomics and bulk-data workflows respectively.

The :class:`Project` facade ties readers, writers, and the cross-file
:func:`validateProject` integrity checks together into a single
ergonomic API for the dashboard and CLI layers.
"""

import warnings as _warnings

from arcline.io.schema import (
    EDGES_SCHEMA,
    MANIFEST_SCHEMA,
    MANIFEST_SCHEMA_VERSION,
    NODES_SCHEMA,
)
from arcline.io.validators import ValidationIssue, validateProject
from arcline.io.readers import (
    fromCsv,
    fromJson,
    fromParquet,
    fromYaml,
)
from arcline.io.writers import toJson, toJsonRecords, toParquet, toYaml
from arcline.io.project import Project


def _deprecated(oldName, new):
    def _shim(*args, **kwargs):
        _warnings.warn(
            f"arcline.io.{oldName}() is deprecated; "
            f"use arcline.io.{new.__name__}() instead.",
            DeprecationWarning,
            stacklevel = 2,
        )
        return new(*args, **kwargs)
    _shim.__name__ = oldName
    _shim.__doc__ = f"Deprecated alias of :func:`{new.__name__}`."
    return _shim


from_json = _deprecated("from_json", fromJson)
from_yaml = _deprecated("from_yaml", fromYaml)
from_parquet = _deprecated("from_parquet", fromParquet)
from_csv = _deprecated("from_csv", fromCsv)
to_json = _deprecated("to_json", toJson)
to_json_records = _deprecated("to_json_records", toJsonRecords)
to_yaml = _deprecated("to_yaml", toYaml)
to_parquet = _deprecated("to_parquet", toParquet)
validate_project = _deprecated("validate_project", validateProject)


__all__ = [
    "Project",
    "fromJson",
    "fromYaml",
    "fromParquet",
    "fromCsv",
    "toJson",
    "toJsonRecords",
    "toYaml",
    "toParquet",
    "validateProject",
    "ValidationIssue",
    "MANIFEST_SCHEMA_VERSION",
    "NODES_SCHEMA",
    "EDGES_SCHEMA",
    "MANIFEST_SCHEMA",
    # Deprecated snake_case aliases (removed in 0.2.0):
    "from_json",
    "from_yaml",
    "from_parquet",
    "from_csv",
    "to_json",
    "to_json_records",
    "to_yaml",
    "to_parquet",
    "validate_project",
]
