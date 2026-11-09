#!/usr/bin/env python3

from gnr.core.cli import GnrCliArgParse

description = "Turn the audit queue into audit events"


def main(instance):
    parser = GnrCliArgParse(description=description)
    parser.add_argument('--block-size', dest='block_size', type=int, default=1000,
                        help='queue rows per block')
    options = parser.parse_args()
    gaps = instance.db.table('audit.event').batch(block_size=options.block_size)
    if gaps is None:
        print('Another audit batch is running: nothing done')
        return
    for gap in gaps:
        print('Version gap: {tbl} {record_pkey} version {version}, expected {expected_version}'.format(**gap))
