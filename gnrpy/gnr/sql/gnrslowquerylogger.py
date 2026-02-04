#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrslowquerylogger : Slow query logging for analysis
# Copyright (c) : 2004 - 2024 Softwell srl - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari, Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""
Slow Query Logger

Logs slow SELECT queries to SQLite database for later analysis.
Queries are deduplicated by hash, with execution statistics tracked.

Configuration (in instanceconfig.xml db node):
    <db implementation="postgres"
        dbname="mydb"
        slow_query_threshold="0.5"
        slow_query_dbpath="/path/to/slow_queries.db" />

- slow_query_threshold: minimum execution time in seconds to log (default: disabled)
- slow_query_dbpath: path to SQLite database (default: {instanceFolder}/data/slow_queries.db)

Schema:
    CREATE TABLE slow_queries (
        query_hash TEXT PRIMARY KEY,
        sql TEXT,
        dbtable TEXT,
        first_seen TIMESTAMP,
        -- Fields populated by external analyzer cron:
        explain_plan TEXT,
        analyzed_at TIMESTAMP,
        ai_suggestion TEXT,
        ticket_url TEXT
    );

    CREATE TABLE slow_query_executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query_hash TEXT NOT NULL,
        execution_time REAL,
        executed_at TIMESTAMP,
        args TEXT,
        username TEXT,
        storename TEXT,
        FOREIGN KEY (query_hash) REFERENCES slow_queries(query_hash)
    );

External cron job can:
1. SELECT * FROM slow_queries WHERE explain_plan IS NULL
2. Join with executions to get worst-case args
3. Run EXPLAIN ANALYZE on each query
4. Pass to Claude for analysis
5. UPDATE with explain_plan, ai_suggestion, ticket_url
"""

import os
import json
import sqlite3
import hashlib
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS slow_queries (
    query_hash TEXT PRIMARY KEY,
    sql TEXT NOT NULL,
    dbtable TEXT,
    first_seen TIMESTAMP NOT NULL,
    explain_plan TEXT,
    analyzed_at TIMESTAMP,
    ai_suggestion TEXT,
    ticket_url TEXT
);

CREATE TABLE IF NOT EXISTS slow_query_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT NOT NULL,
    execution_time REAL NOT NULL,
    executed_at TIMESTAMP NOT NULL,
    args TEXT,
    username TEXT,
    storename TEXT,
    FOREIGN KEY (query_hash) REFERENCES slow_queries(query_hash)
);

CREATE INDEX IF NOT EXISTS idx_slow_queries_not_analyzed
    ON slow_queries(analyzed_at) WHERE analyzed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_executions_query_hash
    ON slow_query_executions(query_hash);

CREATE INDEX IF NOT EXISTS idx_executions_time
    ON slow_query_executions(execution_time DESC);

CREATE INDEX IF NOT EXISTS idx_executions_executed_at
    ON slow_query_executions(executed_at);
"""


def _get_query_hash(sql):
    """Generate a hash for the SQL query (ignoring comments).

    :param sql: the SQL statement
    :returns: MD5 hash of the normalized SQL
    """
    # Remove the initial comment line (e.g. "-- GNRCOMMENT - {...}\n")
    normalized = sql
    if normalized.lstrip().startswith('--'):
        lines = normalized.split('\n', 1)
        if len(lines) > 1:
            normalized = lines[1]

    # Normalize whitespace
    normalized = ' '.join(normalized.split())

    return hashlib.md5(normalized.encode('utf-8')).hexdigest()


def _serialize_args(sqlargs):
    """Prepare SQL arguments for JSON serialization.

    :param sqlargs: dict of SQL arguments
    :returns: JSON string
    """
    safe_args = {}
    for k, v in (sqlargs or {}).items():
        try:
            json.dumps(v)
            safe_args[k] = v
        except (TypeError, ValueError):
            safe_args[k] = str(v)
    return json.dumps(safe_args)


def _init_db(db_path):
    """Initialize the SQLite database with schema.

    :param db_path: path to SQLite database
    :returns: sqlite3 connection
    """
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def log_slow_query(db, sql, sqlargs, execution_time, dbtable=None):
    """Log a slow query to SQLite database.

    Inserts the query (if new) and always logs the execution details.

    :param db: the GnrSqlDb instance
    :param sql: the SQL statement
    :param sqlargs: the SQL arguments
    :param execution_time: query execution time in seconds
    :param dbtable: the main table involved
    """
    # Determine database path
    db_path = getattr(db, 'slow_query_dbpath', None)
    if not db_path:
        application = getattr(db, 'application', None)
        instance_folder = getattr(application, 'instanceFolder', None) if application else None
        if instance_folder:
            db_path = os.path.join(instance_folder, 'data', 'slow_queries.db')
        else:
            return

    query_hash = _get_query_hash(sql)
    now = datetime.now().isoformat()

    try:
        conn = _init_db(db_path)
        cursor = conn.cursor()

        # Insert query if not exists
        cursor.execute("""
            INSERT OR IGNORE INTO slow_queries
            (query_hash, sql, dbtable, first_seen)
            VALUES (?, ?, ?, ?)
        """, (query_hash, sql, dbtable, now))

        # Always insert execution record
        cursor.execute("""
            INSERT INTO slow_query_executions
            (query_hash, execution_time, executed_at, args, username, storename)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            query_hash,
            execution_time,
            now,
            _serialize_args(sqlargs),
            db.currentEnv.get('user'),
            db.currentEnv.get('storename')
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        logger.warning(f'Failed to log slow query: {e}')
