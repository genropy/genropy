import psycopg
from psycopg import sql

from gnrpkg.sys.services.dbadmin import DbAdmin
from gnr.app import pkglog as logger
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

    def _get_cursor(self):
        conn = psycopg.connect(
            host=self.dbadmin_host,
            port=self.dbadmin_port,
            user=self.dbadmin_user,
            password=self.dbadmin_password,
            autocommit=True  # needed for operations like CREATE DATABASE
        )
        return conn.cursor()

    def _database_create(self, database_name):
        self.cur.execute(sql.SQL("CREATE DATABASE {}").format(
            sql.Identifier(database_name)
        ))

    def _database_delete(self, database_name):
        self.cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(
            sql.Identifier(database_name)
        ))

    def _user_create(self, username, password):
        self.cur.execute(sql.SQL(
            "CREATE USER {} WITH PASSWORD %s"
        ).format(sql.Identifier(username)), [password])
        
    def _user_delete(self, username):
        self.cur.execute(sql.SQL("DROP USER IF EXISTS {}").format(
            sql.Identifier(username)
        ))

    def _user_set_permissions(self, username, database_name,
                              permission_list):
        self.cur.execute(sql.SQL(
            "GRANT ALL PRIVILEGES ON DATABASE {} TO {}"
        ).format(sql.Identifier(database_name), sql.Identifier(username)))

    
    def _database_list(self):
        self.cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
        return [row[0] for row in self.cur.fetchall()]
    
    def _user_change_password(self, username, password):
        self.cur.execute(sql.SQL(
            "ALTER USER {} WITH PASSWORD %s"
        ).format(sql.Identifier(username)), [password])
    
    
class ServiceParameters(BaseComponent):
    def service_parameters(self, pane, datapath=None, **kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.textbox(value='^.dbadmin_host', lbl='Database Server Host')
        fb.textbox(value='^.dbadmin_port', lbl='Database Server Port')
        fb.textbox(value='^.dbadmin_user', lbl='Database Administrator User')
        fb.textbox(value='^.dbadmin_password',lbl='Database Administrator Password')
