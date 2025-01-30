import os

from psycopg2 import pool

from gnr.core.loghandlers.queuehandler import GnrQueueLoggingHandler

__all__ = ['GnrPostgresqlLoggingHandler']

class GnrPostgresqlLoggingHandler(GnrQueueLoggingHandler):
    _initial_sql = """CREATE TABLE IF NOT EXISTS log(
    Created text,
    UserName text,
    Name text,
    LogLevel int,
    LogLevelName text,    
    Message text,
    Module text,
    FuncName text,
    LineNo int,
    Exception text,
    Process int,
    Thread text,
    ThreadName text
    )"""
    
    _query = """INSERT INTO log(
    Created,
    UserName,
    Name,
    LogLevel,
    LogLevelName,
    Message,
    Module,
    FuncName,
    LineNo,
    Exception,
    Process,
    Thread,
    ThreadName
    )
    VALUES (
    %(created)s,
    %(username)s,
    %(name)s,
    %(levelno)s,
    %(levelname)s,
    %(msg)s,
    %(module)s,
    %(funcName)s,
    %(lineno)s,
    %(exc_text)s,
    %(process)s,
    %(thread)s,
    %(threadName)s
    );
    """

    def initialize(self):
        self.table_name = self.settings.get("table_name")

        # Initialize PostgreSQL connection pool
        self.connection_pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            **self.settings
        )

    def _process_record(self, log_entry):
        try:
            conn = self.connection_pool.getconn()
            user = os.environ.get("USER", "NA")
            to_record = log_entry.__dict__
            to_record['username'] = user
            with conn.cursor() as cursor:
                cursor.execute(self._query, to_record)
                conn.commit()
                
        except Exception as e:
            print(f"Error writing log to database: {e}")
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def shutdown(self):
        self.connection_pool.closeall()

