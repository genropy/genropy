"""Tests for issue #654: unreachable DB server should produce a clear error.

When 'gnr db migrate' is run against an unreachable database server,
the system should raise GnrSqlConnectionException with a clear message
instead of a misleading TypeError deep in diff_engine.py.
"""
import pytest
from unittest.mock import patch, MagicMock

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

try:
    import psycopg
    HAS_PSYCOPG3 = True
except ImportError:
    HAS_PSYCOPG3 = False

from gnr.sql.gnrsql_exceptions import (
    GnrNonExistingDbException,
    GnrSqlConnectionException,
)
from gnr.sql.gnrsqlmigration.migrator import SqlMigrator


class TestPsycopg2ConnectionError:
    """Test that psycopg2 adapter distinguishes connection errors from non-existing DB."""

    @pytest.mark.skipif(not HAS_PSYCOPG2, reason="psycopg2 not installed")
    def test_nonexisting_db_raises_nonexisting_exception(self):
        """OperationalError with 'does not exist' should raise GnrNonExistingDbException."""
        from gnr.sql.adapters.gnrpostgres import SqlDbAdapter

        adapter = MagicMock(spec=SqlDbAdapter)
        adapter.dbroot = MagicMock()
        adapter.dbroot.dbname = 'test_db'
        adapter._lock = MagicMock()
        adapter.get_connection_params = MagicMock(return_value={
            'host': 'localhost', 'dbname': 'nonexistent_db',
        })

        error = psycopg2.OperationalError('FATAL:  database "nonexistent_db" does not exist')
        with patch('psycopg2.connect', side_effect=error):
            with pytest.raises(GnrNonExistingDbException):
                SqlDbAdapter.connect(adapter)

    @pytest.mark.skipif(not HAS_PSYCOPG2, reason="psycopg2 not installed")
    def test_unreachable_server_raises_connection_exception(self):
        """OperationalError with connection refused should raise GnrSqlConnectionException."""
        from gnr.sql.adapters.gnrpostgres import SqlDbAdapter

        adapter = MagicMock(spec=SqlDbAdapter)
        adapter.dbroot = MagicMock()
        adapter.dbroot.dbname = 'test_db'
        adapter._lock = MagicMock()
        adapter.get_connection_params = MagicMock(return_value={
            'host': 'nonexistent-host.invalid', 'dbname': 'test_db',
        })

        error = psycopg2.OperationalError(
            'could not connect to server: Connection refused\n'
            '\tIs the server running on host "nonexistent-host.invalid" '
            'and accepting TCP/IP connections on port 5432?'
        )
        with patch('psycopg2.connect', side_effect=error):
            with pytest.raises(GnrSqlConnectionException) as exc_info:
                SqlDbAdapter.connect(adapter)
            assert exc_info.value.dbname == 'test_db'
            assert exc_info.value.original_error is error

    @pytest.mark.skipif(not HAS_PSYCOPG2, reason="psycopg2 not installed")
    def test_connection_exception_has_clear_message(self):
        """GnrSqlConnectionException.__str__ should produce a human-readable message."""
        exc = GnrSqlConnectionException(
            'mydb',
            original_error=Exception('Connection refused'),
        )
        msg = str(exc)
        assert 'mydb' in msg
        assert 'Connection refused' in msg


class TestPsycopg3ConnectionError:
    """Test that psycopg (v3) adapter distinguishes connection errors from non-existing DB."""

    @pytest.mark.skipif(not HAS_PSYCOPG3, reason="psycopg not installed")
    def test_nonexisting_db_raises_nonexisting_exception(self):
        """OperationalError with 'does not exist' should raise GnrNonExistingDbException."""
        from gnr.sql.adapters.gnrpostgres3 import SqlDbAdapter

        adapter = MagicMock(spec=SqlDbAdapter)
        adapter.dbroot = MagicMock()
        adapter.dbroot.dbname = 'test_db'
        adapter.get_connection_params = MagicMock(return_value={
            'host': 'localhost', 'database': 'nonexistent_db',
        })

        error = psycopg.OperationalError('FATAL:  database "nonexistent_db" does not exist')
        with patch('psycopg.connect', side_effect=error):
            with pytest.raises(GnrNonExistingDbException):
                SqlDbAdapter.connect(adapter)

    @pytest.mark.skipif(not HAS_PSYCOPG3, reason="psycopg not installed")
    def test_unreachable_server_raises_connection_exception(self):
        """OperationalError with connection refused should raise GnrSqlConnectionException."""
        from gnr.sql.adapters.gnrpostgres3 import SqlDbAdapter

        adapter = MagicMock(spec=SqlDbAdapter)
        adapter.dbroot = MagicMock()
        adapter.dbroot.dbname = 'test_db'
        adapter.get_connection_params = MagicMock(return_value={
            'host': 'nonexistent-host.invalid', 'database': 'test_db',
        })

        error = psycopg.OperationalError(
            'connection to server at "nonexistent-host.invalid", port 5432 failed: '
            'Connection refused'
        )
        with patch('psycopg.connect', side_effect=error):
            with pytest.raises(GnrSqlConnectionException) as exc_info:
                SqlDbAdapter.connect(adapter)
            assert exc_info.value.dbname == 'test_db'
            assert exc_info.value.original_error is error


class TestMigratorConnectionError:
    """Test that the migrator catches GnrSqlConnectionException and exits cleanly."""

    def test_migrator_exits_on_connection_error(self):
        """prepareMigrationCommands should raise SystemExit with a clear message
        when the DB server is unreachable."""
        migrator = MagicMock(spec=SqlMigrator)
        migrator.prepareMigrationCommands = SqlMigrator.prepareMigrationCommands.__get__(migrator)
        conn_error = GnrSqlConnectionException('mydb', original_error=Exception('No route to host'))
        migrator.prepareStructures.side_effect = conn_error

        with pytest.raises(SystemExit) as exc_info:
            migrator.prepareMigrationCommands()
        msg = str(exc_info.value)
        assert 'mydb' in msg
        assert 'No route to host' in msg
        assert 'Migration aborted' in msg
