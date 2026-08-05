#!/usr/bin/env python
# encoding: utf-8

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapplistener import GnrAppListener

description = "Start the GnrListener for a GenroPy application"


def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('instance', help="Instance name")
    parser.add_argument('-w', '--workers', dest='workers', type=int, default=1,
                        help="Number of thread-pool workers (1 = synchronous)")
    parser.add_argument('-t', '--timeout', dest='timeout', type=int, default=5,
                        help="Select timeout in seconds")
    parser.add_argument('-c', '--coalesce', dest='coalesce', type=int, default=1,
                        help="Coalesce sleep in seconds after a batch")
    options = parser.parse_args()
    GnrAppListener(options.instance, timeout=options.timeout,
                   coalesce=options.coalesce, workers=options.workers).run()


if __name__ == '__main__':
    main()
