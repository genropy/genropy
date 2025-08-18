#!/usr/bin/env python3

import tempfile
from gnr.core.cli import GnrCliArgParse

description = "dump the instance database"

def main(instance):

    parser = GnrCliArgParse(description=description)
    switches = [
        'data_only', 'clean', 'create', 'no_owner',
        'schema_only', 'no_privileges', 'if_exists',
        'quote_all_identifiers', 'plain_text'
    ]
    
    for s in switches:
        parser.add_argument(f"--{s}", action='store_true', help=s)

    parser.add_argument("--compress", dest='compress',
                        choices=['gzip','lz4','zstd','none'],
                        default="none",
                        help="Dump compression level")
    parser.add_argument("-o", "--output",
                        dest='output',
                        help="where to save the dump",
                        default=tempfile.mktemp())
    
    options = parser.parse_args()
    r = instance.db.dump(options.output, options=options.__dict__)

    print(f"Dump completed in file: {r}")
