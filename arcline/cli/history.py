# -*- encoding: utf-8 -*-

"""
Historian CLI Subcommands
-------------------------

Wires the historian's bulk-prewarm + cache-bust + spec-validation
operations onto the ``arcline history`` Typer subgroup. The subgroup
is registered onto the top-level app from :mod:`arcline.cli.main`.

Three subcommands::

    arcline history sync <project> [--since YYYY-MM-DD] [--until YYYY-MM-DD]
    arcline history clear <project> [--kind ...] [--hash-key ...]
    arcline history validate

The ``sync`` and ``validate`` paths require ``ARCLINE_MSSQL_DSN``;
``clear`` is offline-only and operates entirely on the Parquet cache.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import typer

from arcline.historian import (
    HistorianError,
    clearCache,
    fetch,
    iterCatalog,
    redactDsn,
    testConnection,
)
from arcline.historian.connection import getDsn
from arcline.io import Project


history = typer.Typer(
    name = "history",
    help = "Historian bulk operations against the MS-SQL warehouse.",
    no_args_is_help = True,
)


@history.command("sync")
def sync(
    project : Path = typer.Argument(
        ..., help = "Path to an arcline project directory.",
    ),
    since : Optional[str] = typer.Option(
        None, "--since",
        help = "Lower bound of the fetch range (YYYY-MM-DD). Defaults to 2 years ago.",
    ),
    until : Optional[str] = typer.Option(
        None, "--until",
        help = "Upper bound of the fetch range (YYYY-MM-DD). Defaults to today.",
    ),
) -> None:
    """Pre-warm the Parquet cache for every (entity, attribute) in the project."""
    if not testConnection():
        typer.secho(
            f"Cannot reach warehouse (DSN: {redactDsn(getDsn())}). "
            f"Set ARCLINE_MSSQL_DSN.",
            fg = typer.colors.RED, err = True,
        )
        raise typer.Exit(code = 2)

    today = date.today()
    startDate = since or (today - timedelta(days = 730)).isoformat()
    endDate = until or today.isoformat()

    projectObj = Project.open(project)
    graph = projectObj.toGraph()

    catalog = list(iterCatalog())
    typer.echo(f"syncing {len(catalog)} catalog entries [{startDate} .. {endDate}]")

    okCount = 0
    skipCount = 0
    failCount = 0

    for kind, attribute, spec in catalog:
        for entity in _entitiesOfKind(graph, kind):
            try:
                fetch(
                    projectPath = project, kind = kind,
                    hashKey = entity.hashKey, attribute = attribute,
                    spec = spec, start = startDate, end = endDate,
                    refresh = True,
                )
                okCount += 1
            except HistorianError as exc:
                failCount += 1
                typer.secho(
                    f"  FAIL {kind}/{entity.hashKey}/{attribute}: {exc}",
                    fg = typer.colors.YELLOW, err = True,
                )
        if not list(_entitiesOfKind(graph, kind)):
            skipCount += 1

    typer.secho(
        f"sync complete: ok={okCount} fail={failCount} skipped-kinds={skipCount}",
        fg = typer.colors.GREEN if failCount == 0 else typer.colors.YELLOW,
    )
    raise typer.Exit(code = 0 if failCount == 0 else 1)


@history.command("clear")
def clear(
    project : Path = typer.Argument(
        ..., help = "Path to an arcline project directory.",
    ),
    kind : Optional[str] = typer.Option(
        None, "--kind",
        help = "Limit cache clear to a single kind (e.g. 'lane').",
    ),
    key : Optional[str] = typer.Option(
        None, "--hash-key",
        help = "Limit cache clear to a single entity hash key.",
    ),
) -> None:
    """Delete cached Parquet snapshots; scope narrows by --kind / --hash-key."""
    deleted = clearCache(project, kind = kind, hashKey = key)
    typer.secho(
        f"cleared {deleted} cached parquet file(s)",
        fg = typer.colors.GREEN,
    )


@history.command("validate")
def validate() -> None:
    """Smoke-check the catalog: connection + every HistorySpec round-trips."""
    catalog = list(iterCatalog())
    typer.echo(f"catalog: {len(catalog)} (kind, attribute, spec) entries")

    if not testConnection():
        typer.secho(
            f"warehouse unreachable (DSN: {redactDsn(getDsn())}); "
            f"set ARCLINE_MSSQL_DSN to enable live validation.",
            fg = typer.colors.YELLOW,
        )
        raise typer.Exit(code = 0)

    typer.secho("warehouse reachable", fg = typer.colors.GREEN)

    failed = 0
    for kind, attribute, spec in catalog:
        try:
            from arcline.historian.fetcher import buildQuery
            buildQuery(spec)
            typer.echo(f"  OK   {kind}/{attribute} -> {spec.qualifiedTable()}")
        except Exception as exc:
            failed += 1
            typer.secho(
                f"  FAIL {kind}/{attribute}: {exc}",
                fg = typer.colors.RED,
            )
    if failed:
        raise typer.Exit(code = 1)


def _entitiesOfKind(graph, kind: str):
    for n in graph.nodes:
        if getattr(type(n), "kind", None) == kind:
            yield n
    for e in graph.edges:
        if getattr(type(e), "kind", None) == kind:
            yield e
