# -*- encoding: utf-8 -*-

"""
File-Based Project Facade
-------------------------

:class:`Project` is the user-facing entry point to an :mod:`arcline`
project on disk. It owns the canonical project layout
(``manifest.yaml``, ``nodes.json``, ``edges.json``, plus a few
auxiliary directories), delegates serialisation to the readers and
writers in :mod:`arcline.io`, and runs cross-file integrity checks
through :func:`arcline.io.validators.validateProject` on every load.

Constructors:

  * :meth:`Project.init` - create an empty, well-formed project on
    disk.
  * :meth:`Project.open` - load and validate an existing project.
  * :meth:`Project.fromGraph` - persist an in-memory graph as a new
    project.

The :meth:`toGraph` instance method materialises the project into a
backend-specific :class:`AbstractGraph` (currently
:class:`NetworkXGraph`).
"""

import io as _io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from arcline.graph.backends.networkx import NetworkXGraph
from arcline.graph.base.edges import AbstractEdge
from arcline.graph.base.graph import AbstractGraph
from arcline.graph.base.nodes import AbstractNode
from arcline.io.readers import __buildEdge__, __buildNode__
from arcline.io.schema import MANIFEST_SCHEMA_VERSION
from arcline.io.validators import ValidationIssue, validateProject
from arcline.io.writers import (
    _buildPayload,
    __edgeRecord__,
    __nodeRecord__,
    toJsonRecords,
)


_GITIGNORE_BODY : str = (
    "# arcline project local artifacts\n"
    ".cache/\n"
    "exports/\n"
)


def __extractRecords__(
        payload : Any, key : str, filePath : Path
) -> List[Dict[str, Any]]:
    """
    Normalise the parsed JSON payload of a ``nodes.json`` or
    ``edges.json`` file into a flat list of record dictionaries.

    Both the canonical flat-list form (``[{...}, {...}]``) and the
    legacy envelope form (``{"nodes": [...], "edges": [...]}``) are
    accepted. A ``None`` value for the requested key is coerced to
    an empty list rather than propagating into downstream iteration.

    :type  payload: Any
    :param payload: Parsed JSON payload as returned by
        :func:`json.load`.

    :type  key: str
    :param key: Envelope key to extract when ``payload`` is a dict
        (``"nodes"`` or ``"edges"``).

    :type  filePath: Path
    :param filePath: Source file path; included in error messages.

    :raises ValueError: If ``payload`` is neither a list nor a dict
        with the requested key, or if the extracted value is not a
        list.

    :rtype:   List[Dict[str, Any]]
    :returns: Flat list of record dictionaries, possibly empty.
    """

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        if key not in payload:
            return []
        records = payload.get(key)
        if records is None:
            raise ValueError(
                f"Field {key!r} in {filePath} is explicitly null; "
                f"use an empty array [] instead."
            )
        if not isinstance(records, list):
            raise ValueError(
                f"Expected {key!r} to be a JSON array in "
                f"{filePath}, got {type(records).__name__}."
            )
        return records

    raise ValueError(
        f"Unsupported JSON payload shape in {filePath}: expected "
        f"a list or an envelope dict with {key!r} key, got "
        f"{type(payload).__name__}."
    )


def __assembleRecords__(
        rawNodes : List[Dict[str, Any]],
        rawEdges : List[Dict[str, Any]]
) -> tuple:
    """
    Deserialise raw record dictionaries into pydantic-validated
    :class:`AbstractNode` and :class:`AbstractEdge` instances using
    the registry-driven helpers in :mod:`arcline.io.readers`.

    :type  rawNodes: List[Dict[str, Any]]
    :param rawNodes: Raw node dictionaries.

    :type  rawEdges: List[Dict[str, Any]]
    :param rawEdges: Raw edge dictionaries.

    :raises KeyError: If a record is missing required fields or
        references an unknown ``hashKey`` endpoint.
    :raises ValueError: If a record's ``kind`` discriminator is not
        registered.

    :rtype:   tuple
    :returns: ``(nodes, edges)`` lists of validated instances.
    """

    nodes : List[AbstractNode] = [
        __buildNode__(rec) for rec in rawNodes
    ]
    nodesByKey : Dict[str, AbstractNode] = {
        node.hashKey : node for node in nodes
    }
    edges : List[AbstractEdge] = [
        __buildEdge__(rec, nodesByKey) for rec in rawEdges
    ]

    return nodes, edges


class Project:
    """
    A file-based supply-chain project on disk.

    The project root contains:

    .. code-block:: text

        <path>/
            manifest.yaml
            nodes.json
            edges.json
            icons/
            scenarios/
            .gitignore
            .cache/        (created lazily)
            exports/       (created lazily)

    Instances are constructed via the three classmethods
    (:meth:`init`, :meth:`open`, :meth:`fromGraph`) rather than the
    raw ``__init__`` signature, which is reserved for internal use.
    """

    def __init__(
            self,
            path : Path,
            name : str,
            description : str,
            schemaVersion : str,
            nodes : List[AbstractNode],
            edges : List[AbstractEdge],
            createdAt : str,
            updatedAt : Optional[str] = None
    ) -> None:
        """
        Internal constructor. Prefer :meth:`init`, :meth:`open`, or
        :meth:`fromGraph`.

        :type  path: Path
        :param path: Resolved project root directory.

        :type  name: str
        :param name: Human-readable project name.

        :type  description: str
        :param description: Free-form project description.

        :type  schemaVersion: str
        :param schemaVersion: Schema version stamped into the
            manifest.

        :type  nodes: List[AbstractNode]
        :param nodes: Project node list.

        :type  edges: List[AbstractEdge]
        :param edges: Project edge list.

        :type  createdAt: str
        :param createdAt: ISO-8601 creation timestamp.

        :type  updatedAt: Optional[str]
        :param updatedAt: ISO-8601 last-update timestamp.
        """

        self.path : Path = path
        self.name : str = name
        self.description : str = description
        self.schemaVersion : str = schemaVersion
        self.nodes : List[AbstractNode] = nodes
        self.edges : List[AbstractEdge] = edges
        self.createdAt : str = createdAt
        self.updatedAt : Optional[str] = updatedAt


    @classmethod
    def init(
            cls,
            path : Union[Path, str],
            name : Optional[str] = None,
            description : str = "",
            persist : bool = True
    ) -> "Project":
        """
        Create an empty arcline project on disk and return the
        in-memory handle.

        Writes ``manifest.yaml``, empty ``nodes.json`` and
        ``edges.json`` arrays, a default ``.gitignore``, and creates
        the auxiliary ``icons/`` and ``scenarios/`` directories.

        :type  path: Union[Path, str]
        :param path: Project root directory; created if missing.

        :type  name: Optional[str]
        :param name: Human-readable project name; defaults to the
            directory name.

        :type  description: str
        :param description: Free-form project description.

        :type  persist: bool
        :param persist: When ``True`` (default) the manifest plus
            empty ``nodes.json`` / ``edges.json`` are written to
            disk immediately. Pass ``False`` to skip the artifact
            writes (only the auxiliary directories and ``.gitignore``
            are created); callers must invoke :meth:`save` to flush
            state. Used internally by :meth:`fromGraph` to avoid a
            redundant double-write.

        :raises FileExistsError: If ``path`` already contains a
            non-empty ``manifest.yaml``.

        :rtype:   Project
        :returns: An in-memory handle to the freshly created project.
        """

        root = Path(path).resolve()
        root.mkdir(parents = True, exist_ok = True)

        manifestPath = root / "manifest.yaml"
        if manifestPath.exists() and manifestPath.stat().st_size > 0:
            raise FileExistsError(
                f"Project already initialised at {root}; refusing "
                f"to overwrite an existing manifest.yaml."
            )

        (root / "icons").mkdir(exist_ok = True)
        (root / "scenarios").mkdir(exist_ok = True)

        gitignore = root / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(_GITIGNORE_BODY, encoding = "utf-8")

        createdAt = datetime.now(timezone.utc).isoformat()
        projName = name or root.name

        if persist:
            manifest : Dict[str, Any] = {
                "name": projName,
                "description": description,
                "arclineSchemaVersion": MANIFEST_SCHEMA_VERSION,
                "createdAt": createdAt,
                "updatedAt": createdAt,
                "defaultBackend": "networkx",
            }

            with manifestPath.open("w", encoding = "utf-8") as fp:
                yaml.safe_dump(
                    manifest, fp,
                    sort_keys = False, default_flow_style = False,
                )

            toJsonRecords([], root / "nodes.json")
            toJsonRecords([], root / "edges.json")

        return cls(
            path = root,
            name = projName,
            description = description,
            schemaVersion = MANIFEST_SCHEMA_VERSION,
            nodes = [],
            edges = [],
            createdAt = createdAt,
            updatedAt = createdAt,
        )


    @classmethod
    def open(cls, path : Union[Path, str]) -> "Project":
        """
        Load an existing project from disk and validate it.

        The manifest is parsed, raw node and edge dictionaries are
        run through :func:`validateProject`, and any
        ``error``-severity issue raises :class:`ValueError`. On
        success the records are deserialised through
        :func:`fromJson`.

        :type  path: Union[Path, str]
        :param path: Path to the project root directory.

        :raises FileNotFoundError: If a required artifact is missing.
        :raises ValueError: If validation reports any error-severity
            issue.

        :rtype:   Project
        :returns: A validated :class:`Project` instance.
        """

        root = Path(path).resolve()
        manifestPath = root / "manifest.yaml"
        nodesPath = root / "nodes.json"
        edgesPath = root / "edges.json"

        for required in (manifestPath, nodesPath, edgesPath):
            if not required.exists():
                raise FileNotFoundError(
                    f"Project file missing: {required}"
                )

        with manifestPath.open("r", encoding = "utf-8") as fp:
            manifest = yaml.safe_load(fp) or {}

        with nodesPath.open("r", encoding = "utf-8") as fp:
            nodesPayload = json.load(fp)

        with edgesPath.open("r", encoding = "utf-8") as fp:
            edgesPayload = json.load(fp)

        rawNodes = __extractRecords__(
            nodesPayload, "nodes", nodesPath,
        )
        rawEdges = __extractRecords__(
            edgesPayload, "edges", edgesPath,
        )

        issues = validateProject(
            nodes = rawNodes, edges = rawEdges, manifest = manifest,
        )
        errors = [i for i in issues if i.severity == "error"]
        if errors:
            messages = "; ".join(
                f"[{i.code}] {i.message}" for i in errors
            )
            raise ValueError(
                f"Project at {root} failed validation: {messages}"
            )

        try:
            nodes, edges = __assembleRecords__(rawNodes, rawEdges)
        except (KeyError, ValueError) as exc:
            raise ValueError(
                f"Project at {root} failed to deserialise records "
                f"(nodes: {nodesPath}, edges: {edgesPath}): {exc}"
            ) from exc

        return cls(
            path = root,
            name = manifest.get("name", root.name),
            description = manifest.get("description", "") or "",
            schemaVersion = manifest.get(
                "arclineSchemaVersion", MANIFEST_SCHEMA_VERSION
            ),
            nodes = nodes,
            edges = edges,
            createdAt = manifest.get("createdAt", ""),
            updatedAt = manifest.get("updatedAt"),
        )


    @classmethod
    def fromGraph(
            cls,
            graph : AbstractGraph,
            path : Union[Path, str],
            name : Optional[str] = None,
            description : Optional[str] = None
    ) -> "Project":
        """
        Persist an in-memory :class:`AbstractGraph` as a new
        on-disk project.

        :type  graph: AbstractGraph
        :param graph: The source graph; its :attr:`nodes` and
            :attr:`edges` lists are written verbatim.

        :type  path: Union[Path, str]
        :param path: Target project root directory; created if
            missing.

        :type  name: Optional[str]
        :param name: Human-readable project name; defaults to the
            directory name.

        :type  description: Optional[str]
        :param description: Free-form project description.

        :rtype:   Project
        :returns: The freshly persisted :class:`Project` handle.
        """

        proj = cls.init(
            path = path, name = name, description = description or "",
            persist = False,
        )
        proj.nodes = list(graph.nodes)
        proj.edges = list(graph.edges)
        proj.save()
        return proj


    def save(self) -> None:
        """
        Persist the in-memory project state to disk. Updates the
        manifest's ``updatedAt`` timestamp and rewrites both
        ``nodes.json`` and ``edges.json`` in canonical form.

        :rtype:   None
        """

        self.updatedAt = datetime.now(timezone.utc).isoformat()

        manifest : Dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "arclineSchemaVersion": self.schemaVersion,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
            "defaultBackend": "networkx",
        }

        with (self.path / "manifest.yaml").open(
            "w", encoding = "utf-8"
        ) as fp:
            yaml.safe_dump(
                manifest, fp,
                sort_keys = False, default_flow_style = False,
            )

        nodeRecords = [__nodeRecord__(node) for node in self.nodes]
        edgeRecords = [__edgeRecord__(edge) for edge in self.edges]

        toJsonRecords(nodeRecords, self.path / "nodes.json")
        toJsonRecords(edgeRecords, self.path / "edges.json")


    def toGraph(self, backend : str = "networkx") -> AbstractGraph:
        """
        Materialise the project into a backend-specific concrete
        :class:`AbstractGraph` instance.

        :type  backend: str
        :param backend: Backend identifier; only ``"networkx"`` is
            supported in the current iteration.

        :raises ValueError: If ``backend`` is unknown.

        :rtype:   AbstractGraph
        :returns: A fully-built backend graph.
        """

        if backend == "networkx":
            return NetworkXGraph(
                nodes = list(self.nodes), edges = list(self.edges),
            )

        raise ValueError(f"Unknown backend {backend!r}.")


    def validate(self) -> List[ValidationIssue]:
        """
        Re-run cross-file integrity checks on the current in-memory
        state by serialising to an in-memory JSON buffer and
        re-loading the raw dictionaries through
        :func:`validateProject`.

        :rtype:   List[ValidationIssue]
        :returns: Aggregated validation issues; empty when clean.
        """

        buffer = _io.StringIO()
        payload = _buildPayload(self.nodes, self.edges)
        json.dump(payload, buffer, default = str)
        buffer.seek(0)
        reloaded = json.loads(buffer.getvalue())

        manifest : Dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "arclineSchemaVersion": self.schemaVersion,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }

        return validateProject(
            nodes = reloaded.get("nodes", []),
            edges = reloaded.get("edges", []),
            manifest = manifest,
        )
