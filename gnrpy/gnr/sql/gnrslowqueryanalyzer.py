#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrslowqueryanalyzer : Analyze slow queries with EXPLAIN and AI
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
Slow Query Analyzer

Cron script to analyze slow queries:
1. Reads unanalyzed queries from SQLite (ordered by severity)
2. Runs EXPLAIN ANALYZE on PostgreSQL
3. Sends to Claude API for optimization suggestions
4. Updates SQLite with results

Usage:
    python gnrslowqueryanalyzer.py --sqlite-path /path/to/slow_queries.db \\
                                   --pg-connection "host=localhost dbname=mydb" \\
                                   --anthropic-key sk-ant-xxx \\
                                   --limit 10

Or as a module:
    from gnr.sql.gnrslowqueryanalyzer import analyze_slow_queries
    analyze_slow_queries(sqlite_path, pg_connection_string, anthropic_api_key)
"""

import os
import json
import sqlite3
import argparse
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

CLAUDE_SYSTEM_PROMPT = """You are a PostgreSQL performance expert.
Analyze the provided SQL query and its EXPLAIN ANALYZE output.

Provide concise, actionable recommendations to optimize the query.
Focus on:
- Missing indexes (suggest CREATE INDEX statements)
- Query structure improvements
- Join optimizations
- Potential N+1 problems

Be specific and practical. If the query is already optimal, say so briefly."""

CLAUDE_USER_PROMPT = """Analyze this slow PostgreSQL query:

## SQL Query
```sql
{sql}
```

## EXPLAIN ANALYZE Output (run with slowest execution parameters)
```
{explain}
```

## Execution Statistics
- Number of executions: {execution_count}
- Max execution time: {max_time:.3f}s
- Min execution time: {min_time:.3f}s
- Avg execution time: {avg_time:.3f}s
- Table: {dbtable}
{variance_note}

## Parameter Variations
Slowest execution args:
```json
{worst_args}
```

Fastest execution args:
```json
{best_args}
```

Provide optimization recommendations. If there's high variance between min/max times, analyze whether specific parameter values cause poor performance."""


def get_unanalyzed_queries(sqlite_path, limit=10):
    """Get queries that haven't been analyzed yet, ordered by severity.

    Severity is determined by: max_time * log(execution_count + 1)
    This prioritizes both slow queries and frequently executed ones.

    :param sqlite_path: path to SQLite database
    :param limit: maximum number of queries to return
    :returns: list of query dicts
    """
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            q.query_hash,
            q.sql,
            q.dbtable,
            q.first_seen,
            COUNT(e.id) as execution_count,
            MAX(e.execution_time) as max_time,
            MIN(e.execution_time) as min_time,
            AVG(e.execution_time) as avg_time,
            -- Get args from the slowest execution
            (SELECT args FROM slow_query_executions
             WHERE query_hash = q.query_hash
             ORDER BY execution_time DESC LIMIT 1) as worst_args,
            -- Get args from the fastest execution
            (SELECT args FROM slow_query_executions
             WHERE query_hash = q.query_hash
             ORDER BY execution_time ASC LIMIT 1) as best_args
        FROM slow_queries q
        JOIN slow_query_executions e ON e.query_hash = q.query_hash
        WHERE q.analyzed_at IS NULL
        GROUP BY q.query_hash
        ORDER BY MAX(e.execution_time) * (1 + LOG(COUNT(e.id) + 1)) DESC
        LIMIT ?
    """, (limit,))

    queries = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return queries


def run_explain_analyze(pg_connection_string, sql, sql_args=None):
    """Run EXPLAIN ANALYZE on PostgreSQL.

    :param pg_connection_string: PostgreSQL connection string
    :param sql: the SQL query to analyze
    :param sql_args: optional dict of query arguments
    :returns: EXPLAIN ANALYZE output as string
    """
    try:
        import psycopg2
    except ImportError:
        raise ImportError("psycopg2 is required for PostgreSQL connection")

    # Remove GNRCOMMENT if present
    clean_sql = sql
    if clean_sql.lstrip().startswith('--'):
        lines = clean_sql.split('\n', 1)
        if len(lines) > 1:
            clean_sql = lines[1]

    explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {clean_sql}"

    conn = psycopg2.connect(pg_connection_string)
    cursor = conn.cursor()

    try:
        if sql_args:
            args = json.loads(sql_args) if isinstance(sql_args, str) else sql_args
            cursor.execute(explain_sql, args)
        else:
            cursor.execute(explain_sql)

        rows = cursor.fetchall()
        explain_output = '\n'.join(row[0] for row in rows)
    finally:
        conn.rollback()  # Don't commit - EXPLAIN ANALYZE doesn't modify data but let's be safe
        conn.close()

    return explain_output


def get_ai_suggestion(sql, explain_output, query_stats, anthropic_api_key):
    """Get optimization suggestions from Claude.

    :param sql: the SQL query
    :param explain_output: EXPLAIN ANALYZE output
    :param query_stats: dict with execution_count, max_time, min_time, avg_time, dbtable, worst_args, best_args
    :param anthropic_api_key: Anthropic API key
    :returns: AI suggestion text
    """
    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic package is required for AI analysis")

    client = anthropic.Anthropic(api_key=anthropic_api_key)

    # Calculate variance note
    max_time = query_stats.get('max_time', 0)
    min_time = query_stats.get('min_time', 0)
    if min_time > 0 and max_time / min_time > 3:
        variance_note = f"- HIGH VARIANCE: max is {max_time/min_time:.1f}x slower than min - likely parameter-dependent"
    else:
        variance_note = ""

    user_message = CLAUDE_USER_PROMPT.format(
        sql=sql,
        explain=explain_output,
        execution_count=query_stats.get('execution_count', 0),
        max_time=max_time,
        min_time=min_time,
        avg_time=query_stats.get('avg_time', 0),
        dbtable=query_stats.get('dbtable', 'unknown'),
        variance_note=variance_note,
        worst_args=query_stats.get('worst_args', '{}'),
        best_args=query_stats.get('best_args', '{}')
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=CLAUDE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    return response.content[0].text


def update_query_analysis(sqlite_path, query_hash, explain_plan, ai_suggestion):
    """Update SQLite with analysis results.

    :param sqlite_path: path to SQLite database
    :param query_hash: the query hash to update
    :param explain_plan: EXPLAIN ANALYZE output
    :param ai_suggestion: AI recommendation text
    """
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE slow_queries
        SET explain_plan = ?,
            ai_suggestion = ?,
            analyzed_at = ?
        WHERE query_hash = ?
    """, (explain_plan, ai_suggestion, datetime.now().isoformat(), query_hash))

    conn.commit()
    conn.close()


def analyze_slow_queries(sqlite_path, pg_connection_string, anthropic_api_key,
                         limit=10, skip_ai=False):
    """Main function to analyze slow queries.

    :param sqlite_path: path to SQLite database with slow queries
    :param pg_connection_string: PostgreSQL connection string
    :param anthropic_api_key: Anthropic API key (optional if skip_ai=True)
    :param limit: maximum number of queries to analyze
    :param skip_ai: if True, only run EXPLAIN without AI analysis
    :returns: number of queries analyzed
    """
    queries = get_unanalyzed_queries(sqlite_path, limit)

    if not queries:
        logger.info("No unanalyzed queries found")
        return 0

    logger.info(f"Found {len(queries)} queries to analyze")
    analyzed = 0

    for query in queries:
        query_hash = query['query_hash']
        sql = query['sql']

        logger.info(f"Analyzing query {query_hash[:8]}... (max_time: {query['max_time']:.3f}s, "
                   f"executions: {query['execution_count']})")

        try:
            # Run EXPLAIN ANALYZE
            explain_output = run_explain_analyze(
                pg_connection_string,
                sql,
                query.get('worst_args')
            )

            # Get AI suggestion (optional)
            ai_suggestion = None
            if not skip_ai and anthropic_api_key:
                ai_suggestion = get_ai_suggestion(
                    sql,
                    explain_output,
                    query,
                    anthropic_api_key
                )

            # Update SQLite
            update_query_analysis(sqlite_path, query_hash, explain_output, ai_suggestion)
            analyzed += 1

            logger.info(f"  -> Analysis complete")

        except Exception as e:
            logger.error(f"  -> Failed to analyze: {e}")
            continue

    return analyzed


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze slow queries with EXPLAIN and AI suggestions'
    )
    parser.add_argument(
        '--sqlite-path',
        required=True,
        help='Path to slow_queries.db SQLite database'
    )
    parser.add_argument(
        '--pg-connection',
        required=True,
        help='PostgreSQL connection string (e.g., "host=localhost dbname=mydb user=postgres")'
    )
    parser.add_argument(
        '--anthropic-key',
        default=os.environ.get('ANTHROPIC_API_KEY'),
        help='Anthropic API key (or set ANTHROPIC_API_KEY env var)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Maximum number of queries to analyze (default: 10)'
    )
    parser.add_argument(
        '--skip-ai',
        action='store_true',
        help='Skip AI analysis, only run EXPLAIN ANALYZE'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    if not args.skip_ai and not args.anthropic_key:
        parser.error("--anthropic-key is required unless --skip-ai is specified")

    analyzed = analyze_slow_queries(
        sqlite_path=args.sqlite_path,
        pg_connection_string=args.pg_connection,
        anthropic_api_key=args.anthropic_key,
        limit=args.limit,
        skip_ai=args.skip_ai
    )

    print(f"Analyzed {analyzed} queries")


if __name__ == '__main__':
    main()
