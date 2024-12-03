
import json
from gnr.sql.gnrsql_exceptions import GnrNonExistingDbException


class PgDbUtils:
    """
    A class to monitor and collect statistics from a PostgreSQL database.
    Each method returns results in JSON format.
    """

    def __init__(self,db=None):
        self.db = db 
        self.conn = None

    def connect(self):
        """Establishes the connection to the database."""
        if not self.conn:
            self.conn = self.db.adapter.connect()
        return self.conn

    def close_connection(self):
        """Closes the connection to the database."""
        if self.conn:
            self.conn.close()
            self.conn = None


    def _query_to_json(self, query):
        """
        Executes an SQL query and returns the result as JSON.

        :param query: The SQL query to execute
        :return: Query result in JSON format
        """
        try:
            self.connect()
            with self.conn.cursor() as cursor:
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
            return json.dumps([dict(zip(columns, row)) for row in rows], default=str)
        except GnrNonExistingDbException:
            self.close_connection()
            return {}

    def pgutils_open_transactions(self):
        """
        Returns a list of active transactions in the database.

        :return: List of active transactions in JSON format
        """
        query = """
        SELECT
            datname AS database,
            usename AS username,
            state,
            query,
            query_start
        FROM pg_stat_activity
        WHERE state IN ('active', 'idle in transaction');
        """
        return self._query_to_json(query)

    def pgutils_blocked_tables(self):
        """
        Returns a list of blocked tables.

        :return: List of blocked tables in JSON format
        """
        query = """
        SELECT
            t.relname AS table_name,
            l.locktype,
            l.mode,
            l.granted,
            a.query AS blocking_query
        FROM pg_locks l
        JOIN pg_class t ON l.relation = t.oid
        LEFT JOIN pg_stat_activity a ON l.pid = a.pid
        WHERE t.relkind = 'r' AND NOT l.granted;
        """
        return self._query_to_json(query)

    def pgutils_table_statistics(self):
        """
        Returns statistics about tables (e.g., row counts, sequential scans).

        :return: Table statistics in JSON format
        """
        query = """
        SELECT
            relname AS table_name,
            seq_scan AS sequential_scans,
            idx_scan AS index_scans,
            n_tup_ins AS inserts,
            n_tup_upd AS updates,
            n_tup_del AS deletes
        FROM pg_stat_user_tables
        ORDER BY seq_scan DESC;
        """
        return self._query_to_json(query)

    def pgutils_index_usage(self):
        """
        Returns information about index usage.

        :return: Index usage statistics in JSON format
        """
        query = """
        SELECT
            relname AS table_name,
            indexrelname AS index_name,
            idx_scan AS index_scans,
            idx_tup_read AS tuples_read,
            idx_tup_fetch AS tuples_fetched
        FROM pg_stat_user_indexes
        WHERE idx_scan > 0
        ORDER BY idx_scan DESC;
        """
        return self._query_to_json(query)

    def pgutils_database_size(self):
        """
        Returns the total size of the database.

        :return: Database size in JSON format
        """
        query = """
        SELECT
            pg_size_pretty(pg_database_size(current_database())) AS database_size;
        """
        return self._query_to_json(query)

    def pgutils_active_connections(self):
        """
        Returns the number of active connections per database.

        :return: Active connections in JSON format
        """
        query = """
        SELECT
            datname AS database,
            COUNT(*) AS active_connections
        FROM pg_stat_activity
        WHERE state = 'active'
        GROUP BY datname;
        """
        return self._query_to_json(query)

    def pgutils_transaction_status(self):
        """
        Returns the status of transactions (commits and rollbacks).

        :return: Transaction status in JSON format
        """
        query = """
        SELECT
            datname AS database,
            xact_commit AS committed_transactions,
            xact_rollback AS rolled_back_transactions
        FROM pg_stat_database;
        """
        return self._query_to_json(query)

    def pgutils_table_locks(self):
        """
        Returns tables with active locks.

        :return: Tables with active locks in JSON format
        """
        query = """
        SELECT
            t.relname AS table_name,
            l.mode,
            a.state,
            a.query
        FROM pg_locks l
        JOIN pg_class t ON l.relation = t.oid
        LEFT JOIN pg_stat_activity a ON l.pid = a.pid
        WHERE NOT l.granted;
        """
        return self._query_to_json(query)

    def pgutils_autovacuum_status(self):
        """
        Returns information about active autovacuum processes.

        :return: Autovacuum status in JSON format
        """
        query = """
        SELECT
            relname AS table_name,
            n_dead_tup AS dead_tuples,
            last_autovacuum,
            last_analyze
        FROM pg_stat_all_tables
        WHERE n_dead_tup > 0
        ORDER BY n_dead_tup DESC;
        """
        return self._query_to_json(query)


    # New methods using pg_stat_statements

    def pgstats_top_queries(self, limit=10):
        """
        Returns the top N queries by total execution time.

        :param limit: Number of queries to retrieve
        :return: Top queries in JSON format
        """
        query = f"""
        SELECT
            query,
            calls,
            total_time,
            mean_time,
            rows
        FROM pg_stat_statements
        ORDER BY total_time DESC
        LIMIT {limit};
        """
        return self._query_to_json(query)

    def pgstats_most_called_queries(self, limit=10):
        """
        Returns the top N most called queries.

        :param limit: Number of queries to retrieve
        :return: Most called queries in JSON format
        """
        query = f"""
        SELECT
            query,
            calls,
            total_time,
            mean_time,
            rows
        FROM pg_stat_statements
        ORDER BY calls DESC
        LIMIT {limit};
        """
        return self._query_to_json(query)

    def pgstats_least_efficient_queries(self, limit=10):
        """
        Returns the top N least efficient queries (highest mean execution time).

        :param limit: Number of queries to retrieve
        :return: Least efficient queries in JSON format
        """
        query = f"""
        SELECT
            query,
            calls,
            total_time,
            mean_time,
            rows
        FROM pg_stat_statements
        ORDER BY mean_time DESC
        LIMIT {limit};
        """
        return self._query_to_json(query)

    def pgstats_query_io_statistics(self, limit=10):
        """
        Returns the top N queries by I/O usage.

        :param limit: Number of queries to retrieve
        :return: Query I/O statistics in JSON format
        """
        query = f"""
        SELECT
            query,
            shared_blks_hit AS cache_hits,
            shared_blks_read AS disk_reads,
            shared_blks_dirtied AS dirty_blocks,
            shared_blks_written AS written_blocks
        FROM pg_stat_statements
        ORDER BY shared_blks_read DESC
        LIMIT {limit};
        """
        return self._query_to_json(query)

    def pgstats_query_memory_statistics(self, limit=10):
        """
        Returns the top N queries by temporary memory usage.

        :param limit: Number of queries to retrieve
        :return: Query memory usage statistics in JSON format
        """
        query = f"""
        SELECT
            query,
            temp_blks_read AS temp_blocks_read,
            temp_blks_written AS temp_blocks_written,
            total_time / calls AS avg_time_per_call
        FROM pg_stat_statements
        ORDER BY temp_blks_written DESC
        LIMIT {limit};
        """
        return self._query_to_json(query)


    @classmethod 
    def list_pgutils(self,prefix=None):
        return {methodname:getattr(self,methodname).__doc__.split('\n')[1] for methodname in dir(self) if methodname.startswith(f'{prefix}_')}



if __name__ == '__main__':
    from gnr.app.gnrapp import GnrApp
    erpy_softwell = GnrApp('erpy_softwell')
    db_utils = PgDbUtils(erpy_softwell.db)
    dbsize = db_utils.get_database_size()
    print('dbsize',dbsize)