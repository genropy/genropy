#!/usr/bin/env python
# encoding: utf-8
"""``gnr db ormextract`` — print the normalized ORM structure as JSON.

Reads the instance model and emits the migrator JSON on stdout. This is the
producer half of the external-migration flow: pipe it into the standalone
engine, e.g.::

    gnr db ormextract myinstance | genro-sqlmigrate check --dsn ...

With ``--job`` it emits the full ``{connection, structure}`` package the
``genro-sqlmigrate`` CLI expects on stdin (the connection is taken from the
instance config), so no DSN needs to be passed separately::

    gnr db ormextract myinstance --job | genro-sqlmigrate migrate
"""

import json
import os
import sys

from gnr.core.cli import GnrCliArgParse
from gnr.db import logger
from gnr.db.cli._migrator_bridge import build_job, build_ormstructure
from gnr.db.cli.gnrmigrate import get_app
from gnr.sql import AdapterCapabilities

description = "print the normalized ORM structure (or full job) as JSON"


def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument("instance")
    parser.add_argument("-i", "--instance", dest="instance",
                        help="Use command on instance")
    parser.add_argument("-D", "--directory", dest="directory",
                        help="Use command on supplied directory")
    parser.add_argument("-s", "--site", dest="site",
                        help="Use command on supplied site")
    parser.add_argument("--config", dest="config_path",
                        help="gnrserve file path")
    parser.add_argument("--job", dest="job", action="store_true",
                        help="Emit the full {connection, structure} package "
                             "for genro-sqlmigrate, not just the structure")
    parser.set_defaults(loglevel="info")
    options = parser.parse_args()

    # Keep stdout clean for the JSON: this command is meant to be piped, but
    # Genropy logging writes to stdout. Redirect stdout at the file-descriptor
    # level (so even handlers that captured the old stream, or C-level writes,
    # go to stderr) while the app initializes and the model is read; then
    # restore fd 1 and write the JSON there.
    saved_fd = os.dup(1)
    os.dup2(2, 1)
    try:
        app, _storename = get_app(options)
        if not app.db.adapter.has_capability(AdapterCapabilities.MIGRATIONS):
            logger.error(f"Instance '{options.instance}' adapter doesn't "
                         "support migrations")
            sys.exit(1)
        extensions = app.db.application.config['db?extensions']
        if options.job:
            payload = build_job(app.db, extensions=extensions)
        else:
            payload = build_ormstructure(app.db, extensions=extensions)
    finally:
        sys.stdout.flush()
        os.dup2(saved_fd, 1)
        os.close(saved_fd)
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
