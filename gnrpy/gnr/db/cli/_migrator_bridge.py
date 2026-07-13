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


def build_ormstructure(db, extensions=None):
    """Produce the normalized ORM structure JSON via the legacy extractor.

    The extractor is the one piece that reads the Genropy model; it stays in
    Genropy. This does NOT introspect the live database: it sets the tenant
    schemas the extractor needs (from the db getters) without the full
    ``prepareStructures`` DB round-trip.
    """
    migrator = SqlMigrator(db, extensions=extensions)
    migrator.tenant_schemas = db.getTenantSchemas()
    return migrator.ormExtractor.get_json_struct()


def build_job(db, extensions=None, options=None):
    """Assemble the ``{connection, structure, options}`` job for the CLI."""
    connection = {
        "dbname": db.dbname,
        "host": db.host or "localhost",
        "port": str(db.port or 5432),
        "application_schemas": db.getApplicationSchemas(),
        "read_only_schemas": db.readOnlySchemas(),
        "tenant_schemas": db.getTenantSchemas(),
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
