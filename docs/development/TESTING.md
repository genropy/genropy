# Testing Genropy Framework

This guide will describe the needed steps to execute unit test for the
Genropy framework.

## Installation
Install genropy with the 'developer' profile, for example:

```
  cd genropy/gnrpy && pip install -e .[developer]
```

This will provide all the needed dependencies to run tests.


## Execute the tests

Python unit tests are localted in gnrpy/tests folder, so executing

```
cd gnrpy/tests && make
```

or, alternatively

```
cd gnrpy/tests && pytest
```
	
will execute all the tests. Since tests are organized per framework
sub-modules, you can test single part of if. The folders tests/app,
tests/core, tests/sql represents the framework sub-packages.

The makefile provided sets up coverage html output for convenience.

## A note about Postgres databases

The sql databases are execute against multiple adapters
automatically. When using a postgres-base adapter, it tests
automatically spins up a temporary postgres instance to be used for
tests, using testing.postgresql package. The DSN is provided
automatically so there is nothing to do.

If you need to use a pre-existing postgres server, you can setup the
following environment variables:

* GNR_TEST_PG_HOST
* GNR_TEST_PG_PORT
* GNR_TEST_PG_USER
* GNR_TEST_PG_PASSWORD

Variables names are self-explaining.

When tests are executed in a Github Action CI context, a temporary
service with postgres will be spin up automatically.




