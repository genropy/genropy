#!/usr/bin/env python3

import tempfile
from gnr.core.cli import GnrCliArgParse

description = "Drop user settings table if empty"

def main(instance):

    parser = GnrCliArgParse(description=description)
    dbtable = instance.db.table('adm.user_setting')
    if dbtable.query().count():
        return
    instance.db.adapter.dropTable(dbtable)
    instance.db.commit()
    print("Dropped user settings")
