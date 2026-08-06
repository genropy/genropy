#!/usr/bin/env python
# encoding: utf-8
"""Bridge to the external ``genro-sqlmigrate`` engine.

Genropy keeps only the ORM extractor (which reads the model and produces the
normalized JSON); the diff, SQL generation and execution can be delegated to
the standalone ``genro-sqlmigration`` package, driven as a subprocess through
its ``genro-sqlmigrate`` CLI.

The bridge is optional and self-detecting: if the CLI is not on PATH, or the
connection is not a plain local/direct one, the caller falls back to the
in-process legacy engine. Nothing here imports ``genro_sqlmigration`` — the two
codebases stay in separate processes.
"""

import json
import os
import shutil
import subprocess

from gnr.sql.gnrsqlmigration import SqlMigrator
from gnr.sql.gnrsql_exceptions import GnrNonExistingDbException

# Override the command path/name explicitly if it is not on PATH.
EXTERNAL_CMD_ENV = "GNR_SQLMIGRATE_CMD"
EXTERNAL_CMD_DEFAULT = "genro-sqlmigrate"


def external_cmd():
    """Return the external CLI path if available, else None."""
    override = os.environ.get(EXTERNAL_CMD_ENV)
    if override:
        return override if shutil.which(override) or os.path.isfile(override) else None
    return shutil.which(EXTERNAL_CMD_DEFAULT)


def is_direct_connection(db):
    """True when the DB is reachable with plain psycopg params (scope A).

    The external engine reopens its own connection from host/port/user/
    password/dbname. SSH tunnels or remote-forwarded stores are out of scope
    for now: those fall back to the in-process engine.
    """
    if getattr(db, "implementation", None) != "postgres":
        return False
    if getattr(db, "remote_host", None) or getattr(db, "remote_port", None):
        return False
    return True


def tenant_schemas(db):
    """Read the tenant schemas, tolerating a not-yet-created database.

    ``db.getTenantSchemas()`` queries the live tenant table, which fails when
    the target database does not exist yet. The legacy engine guards this the
    same way (see ``gnrsqlmigration.migrator.prepareStructures``): a missing DB
    means no tenant schemas, so the ORM structure can still be extracted and a
    ``CREATE DATABASE`` migration emitted.
    """
    try:
        return db.getTenantSchemas()
    except GnrNonExistingDbException:
        return []


def build_ormstructure(db, extensions=None):
    """Produce the normalized ORM structure JSON via the legacy extractor.

    The extractor is the one piece that reads the Genropy model; it stays in
    Genropy. This does NOT introspect the live database: it sets the tenant
    schemas the extractor needs (from the db getters) without the full
    ``prepareStructures`` DB round-trip.
    """
    migrator = SqlMigrator(db, extensions=extensions)
    migrator.tenant_schemas = tenant_schemas(db)
    return migrator.ormExtractor.get_json_struct()


def build_job(db, extensions=None, options=None):
    """Assemble the ``{connection, structure, options}`` job for the CLI."""
    connection = {
        "dbname": db.dbname,
        "host": db.host or "localhost",
        "port": str(db.port or 5432),
        "application_schemas": db.getApplicationSchemas(),
        "read_only_schemas": db.readOnlySchemas(),
        "tenant_schemas": tenant_schemas(db),
    }
    if db.user:
        connection["user"] = db.user
    if db.password:
        connection["password"] = db.password
    job = {
        "connection": connection,
        "structure": build_ormstructure(db, extensions=extensions),
    }
    if options:
        job["options"] = options
    return job


def run_external(cmd, subcommand, job, apply=False):
    """Run ``genro-sqlmigrate <subcommand>`` with the job on stdin.

    Returns the CompletedProcess (stdout = SQL/diff, returncode: for ``check``
    0 = aligned, 1 = changes needed).
    """
    argv = [cmd, subcommand]
    if apply:
        argv.append("--apply")
    return subprocess.run(
        argv, input=json.dumps(job), text=True, capture_output=True, check=False,
    )


def normalize_sql(sql):
    """Split a migration SQL block into canonically-ordered statements.

    Both engines return the SQL as a single ``'\\n'.join(...)`` of commands;
    within a phase the statement order depends on dict iteration, so a plain
    text diff would flag order-only differences. Splitting on ``;``, stripping
    empties and sorting removes that noise, leaving only substantial changes.
    """
    if not sql:
        return []
    statements = [s.strip() for s in sql.replace("\n", " ").split(";")]
    return sorted(s for s in statements if s)


def compare_sql(legacy, external):
    """Compare the legacy and external migration SQL.

    Returns a dict with ``verdict`` (``IDENTICAL`` / ``EQUIVALENT`` /
    ``DIVERGENT``) plus the statements present on one side only. IDENTICAL =
    byte-identical; EQUIVALENT = same after normalization (order/whitespace
    only); DIVERGENT = the normalized statement sets differ.
    """
    legacy = (legacy or "").strip()
    external = (external or "").strip()
    if legacy == external:
        return {"verdict": "IDENTICAL", "only_legacy": [], "only_external": []}
    norm_legacy = normalize_sql(legacy)
    norm_external = normalize_sql(external)
    if norm_legacy == norm_external:
        return {"verdict": "EQUIVALENT", "only_legacy": [], "only_external": []}
    set_legacy = set(norm_legacy)
    set_external = set(norm_external)
    return {
        "verdict": "DIVERGENT",
        "only_legacy": sorted(set_legacy - set_external),
        "only_external": sorted(set_external - set_legacy),
    }
