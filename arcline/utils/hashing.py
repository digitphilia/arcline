# -*- encoding: utf-8 -*-

"""
Deterministic Identifier Hashing
--------------------------------

Helpers that synthesise short, deterministic, human-friendly
identifiers for graph nodes and edges. The output is stable across
machines and Python interpreter sessions because it is derived purely
from :mod:`hashlib.blake2b` over the input strings.

The default form is ``<prefix>-<KIND>-<hash>`` (for example
``N-SUPPLIER-3a1f9b22``); a node-style ``"N"`` prefix and an
edge-style ``"E"`` prefix are exposed as convenience wrappers.
"""

import hashlib
from typing import Optional


def make_key(
        kind : str,
        name : str,
        prefix : Optional[str] = None,
        length : int = 8
) -> str:
    """
    Generate a deterministic short identifier of the form
    ``<prefix>-<KIND>-<hash>`` for a graph node or edge. The function
    is agnostic to node-vs-edge semantics; callers wire the desired
    prefix in via ``prefix``.

    The hash component is produced by :func:`hashlib.blake2b` over
    the UTF-8 encoded ``name`` with a ``digest_size`` of
    ``length // 2`` bytes, yielding ``length`` hex characters.
    ``name`` is the only input that contributes randomness; ``kind``
    only contributes to the human-readable middle segment.

    .. code-block:: python

        make_key("supplier", "Acme Inc")
        # -> 'N-SUPPLIER-3a1f9b22'

    :type  kind: str
    :param kind: Domain ``kind`` discriminator (e.g. ``"supplier"``,
        ``"lane"``); upper-cased in the output.

    :type  name: str
    :param name: Free-form human name used as the hash input.

    :type  prefix: Optional[str]
    :param prefix: Leading segment of the identifier; defaults to
        ``"N"`` for node-style keys when ``None``.

    :type  length: int
    :param length: Number of hex characters in the hash component.
        Must be a positive even integer; defaults to ``8``.

    :raises ValueError: If ``length`` is not a positive even integer
        or if ``kind`` / ``name`` is empty.

    :rtype:   str
    :returns: The synthesised identifier string.
    """

    if not isinstance(kind, str) or not kind:
        raise ValueError("`kind` must be a non-empty string.")

    if not isinstance(name, str) or not name:
        raise ValueError("`name` must be a non-empty string.")

    if not isinstance(length, int) or length <= 0 or length % 2 != 0:
        raise ValueError(
            "`length` must be a positive even integer "
            "(blake2b yields an even number of hex characters)."
        )

    digest = hashlib.blake2b(
        name.encode("utf-8"), digest_size = length // 2
    ).hexdigest()

    return f"{prefix or 'N'}-{kind.upper()}-{digest}"


def make_node_key(kind : str, name : str, length : int = 8) -> str:
    """
    Convenience wrapper around :func:`make_key` with ``prefix="N"``
    for node-style identifiers.

    :type  kind: str
    :param kind: Node ``kind`` discriminator.

    :type  name: str
    :param name: Free-form human name used as the hash input.

    :type  length: int
    :param length: Hex-character length of the hash segment.

    :rtype:   str
    :returns: A node-style identifier of the form
        ``N-<KIND>-<hash>``.
    """

    return make_key(
        kind = kind, name = name, prefix = "N", length = length
    )


def make_edge_key(
        kind : str,
        src_name : str,
        dst_name : str,
        length : int = 8
) -> str:
    """
    Convenience wrapper around :func:`make_key` for edge-style
    identifiers. The hash input is the concatenation of source and
    destination names joined with ``"->"`` so that an edge's identity
    captures both endpoints deterministically.

    :type  kind: str
    :param kind: Edge ``kind`` discriminator.

    :type  src_name: str
    :param src_name: Free-form name of the source endpoint.

    :type  dst_name: str
    :param dst_name: Free-form name of the destination endpoint.

    :type  length: int
    :param length: Hex-character length of the hash segment.

    :rtype:   str
    :returns: An edge-style identifier of the form
        ``E-<KIND>-<hash>``.
    """

    composite = f"{src_name}->{dst_name}"
    return make_key(
        kind = kind, name = composite, prefix = "E", length = length
    )
