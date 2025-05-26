from gnr.lib.services import GnrBaseService
from gnr.app.gnrdeploy import get_random_password
from gnr.app import pkglog as logger

class DbAdmin(GnrBaseService):

    def __init__(self, *args, **kwargs):
        pass

    def database_create(self, database_name):
        logger.info("Creating database %s", database_name)
        return self._database_create(database_name)

    def database_list(self):
        logger.info("Requesting database list")
        return self._database_list()

    def database_delete(self, database_name):
        logger.info("Deleting database %s", database_name)
        return self._database_delete(database_name)
        
    def user_create(self, username, password=None):
        logger.info("Creating user %s", username)
        if password is None:
            logger.info("No password supplied, generating random one")
            password = self._gen_random_password()
        return self._user_create(username, password)

    def user_list(self):
        logger.info("Requesting database list")
        return self._user_list()
    
    def user_delete(self, username):
        logger.info("Deleting user %s", username)
        return self._user_delete(username)

    def user_change_password(self, username, password):
        logger.info("Changing password for user %s", username)
        return self._user_change_password(username, password)

    def user_set_all_privileges(self, username, database_name):
        logger.info("Settings all permission on %s to user %s",
                    database_name, username)
        return self._user_set_all_privileges(username,
                                             database_name)
    
    def _gen_random_password(self):
        return get_random_password(size=20)
        
