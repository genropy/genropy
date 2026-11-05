#!/usr/bin/env python3

from gnr.core.cli import GnrCliArgParse

description = "Give version 0 to the records of the audited tables that have none"


def main(instance):
    parser = GnrCliArgParse(description=description)
    parser.add_argument('--table', dest='sqltable', default=None,
                        help='only this audited table, as <sqlschema>.<sqlname>')
    parser.add_argument('--block-size', dest='block_size', type=int, default=1000,
                        help='records updated per block')
    options = parser.parse_args()
    instance.db.table('audit.members').touch(sqltable=options.sqltable,
                                             block_size=options.block_size)
