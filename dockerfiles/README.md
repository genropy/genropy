# Docker support

The file contained in this folder are related to docker
integration/image creation for the Genropy Framework.


## Environment variables

You can use docker compose to build your derivate image, and the
following env variables will control genropy's behaviour.


| Variable                    | Meaning                                                 |
|-----------------------------|---------------------------------------------------------|
| ```GNR_DB_IMPLEMENTATION``` | The database adapter to use ("postgres", "sqlite", etc) |
| ```GNR_DB_HOST```           | The database host name                                  |
| ```GNR_DB_NAME```           | The name of the database to connect to                  |
| ```GNR_DB_USER```           | The user to connect to the database                     |
| ```GNR_DB_PORT```           | The database server port                                |
| ```GNR_DB_PASSWORD```       | The password for the database connection                |
| ```GNR_LOCALE```            | The L10N/I18N setting to use                            |
| ```GNR_ROOTPWD```           | The default admin password                              |
| ```GNR_MAINPACKAGE```       | The package used for authentication                     |

