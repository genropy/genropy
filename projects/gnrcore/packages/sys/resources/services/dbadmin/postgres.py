from contextlib import contextmanager

import psycopg
from psycopg import sql

from gnrpkg.sys.services.dbadmin import DbAdmin
from gnr.web.gnrbaseclasses import BaseComponent

class Service(DbAdmin):

    def __init__(self, parent,
                 dbadmin_host, dbadmin_port,
                 dbadmin_user, dbadmin_password): 

        self.parent=parent
        self.dbadmin_host = dbadmin_host
        self.dbadmin_port = dbadmin_port
        self.dbadmin_user = dbadmin_user
        self.dbadmin_password = dbadmin_password


    @contextmanager
    def __connect(self):
        conn = psycopg.connect(
            dbname="postgres",
            host=self.dbadmin_host,
            port=self.dbadmin_port,
            user=self.dbadmin_user,
            password=self.dbadmin_password,
            autocommit=True  # needed for operations like CREATE DATABASE
        )
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _execute(self, query, fetch = None):
        with self.__connect() as conn, conn.cursor() as cur:
            cur.execute(query)
            if fetch:
                return cur.fetchall()

    def _database_list(self):
        query = "SELECT datname FROM pg_database WHERE datistemplate = false"
        return [row[0] for row in self._execute(query, fetch=True)]

    def _database_create(self, database_name):
        query = sql.SQL("CREATE DATABASE {}").format(
            sql.Identifier(database_name)
        )
        self._execute(query)

    def _database_delete(self, database_name):
        query = sql.SQL("DROP DATABASE IF EXISTS {}").format(
            sql.Identifier(database_name)
            )
        self._execute(query)

    def _user_list(self):
        query = "SELECT rolname from pg_roles WHERE rolcanlogin = true"
        return [row[0] for row in self._execute(query, fetch=True)]
    
    def _user_create(self, username, password):
        query = sql.SQL("CREATE USER {} with PASSWORD {}").format(
            sql.Identifier(username), sql.Literal(password))
        self._execute(query)

    def _user_delete(self, username):
        query = sql.SQL("DROP USER IF EXISTS {}").format(sql.Identifier(username))
        self._execute(query)

    def _user_set_all_privileges(self, username, database_name):
        query = sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
            sql.Identifier(database_name), sql.Identifier(username)
        )
        self._execute(query)

    def _user_change_password(self, username, password):
        query = sql.SQL("ALTER USER {} WITH PASSWORD {}").format(
            sql.Identifier(username), password)
        self._execute(query)
    
class ServiceParameters(BaseComponent):
    def service_parameters(self, pane, datapath=None, **kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.textbox(value='^.dbadmin_host', lbl='Database Server Host')
        fb.textbox(value='^.dbadmin_port', lbl='Database Server Port')
        fb.textbox(value='^.dbadmin_user', lbl='Database Administrator User')
        fb.textbox(value='^.dbadmin_password',lbl='Database Administrator Password')
