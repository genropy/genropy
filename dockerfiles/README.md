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


## Image labels

Besides the static OCI labels, the image carries the framework version,
the commit it was built from and the build time:

| Label                                   | Content                                            |
|-----------------------------------------|----------------------------------------------------|
| ```org.genropy.version```               | Framework version (see below)                      |
| ```org.genropy.revision```              | Git commit of the framework code in the image      |
| ```org.genropy.build_timestamp```       | UTC build time, e.g. `2026-11-16T04:12:30Z`        |
| ```org.opencontainers.image.version```  | Same as `org.genropy.version`                      |
| ```org.opencontainers.image.revision``` | Same as `org.genropy.revision`                     |

Images built on top of this one, such as the application images generated
by `gnr app dockerize`, inherit all these labels. The OCI keys describe the
image itself, so a derived image may override them with its own version and
revision: on an application image, always read the framework information
from the `org.genropy.*` labels.

The version is `VERSION` from `gnr/__init__.py` for release images. The
nightly `develop` image contains unreleased code, so its version is just
`develop`: the revision label gives the exact commit and the build timestamp
label tells when it was built.

They are filled by the `GNR_VERSION`, `GNR_REVISION` and
`GNR_BUILD_TIMESTAMP` build arguments,
which the CI build sets automatically. For a local build:

```
docker build -f dockerfiles/genropy/Dockerfile \
  --build-arg GNR_VERSION=$(sed -n 's/^VERSION = "\([0-9.]*\)"/\1/p' gnrpy/gnr/__init__.py) \
  --build-arg GNR_REVISION=$(git rev-parse HEAD) \
  --build-arg GNR_BUILD_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ) .
```

To read them from an image:

```
docker inspect -f '{{json .Config.Labels}}' ghcr.io/genropy/genropy:latest
docker inspect -f '{{index .Config.Labels "org.genropy.revision"}}' <application image>
```
