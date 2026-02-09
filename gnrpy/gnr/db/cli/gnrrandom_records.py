#!/usr/bin/env python
# encoding: utf-8

from gnr.core.cli import GnrCliArgParse
from gnr.app.cli.gnrdbsetup import get_app

description = "generate random records for a given table"


def main():
    parser = GnrCliArgParse(description=description)

    parser.add_argument('table',
                        help="Table name (pkg.tablename)")

    parser.add_argument('-i', '--instance',
                        dest='instance',
                        help="Instance name")

    parser.add_argument('-D', '--directory',
                        dest='directory',
                        help="Instance directory path")

    parser.add_argument('-n', '--how_many',
                        dest='how_many',
                        type=int,
                        default=10,
                        help="Number of records to generate (default: 10)")

    parser.add_argument('--seed',
                        dest='seed',
                        type=int,
                        default=None,
                        help="Random seed for reproducibility")

    parser.add_argument('--batch_prefix',
                        dest='batch_prefix',
                        default='RND',
                        help="Prefix for generated text fields (default: RND)")

    options = parser.parse_args()
    app, storename = get_app(options)
    if storename:
        app.db.use_store(storename)
    app.db.createRandomRecords(options.table,
                               how_many=options.how_many,
                               seed=options.seed,
                               batch_prefix=options.batch_prefix)
    print(f"{options.how_many} random records created for {options.table}")


if __name__ == '__main__':
    main()
