#!/usr/bin/env python3
"""Move the counters of an existing instance from adm.counter to sys.counter.

    gnr @<instance> sys migrate_counters --counters '*'
    gnr @<instance> sys migrate_counters --load

Without --load nothing is written. See docs/development/sys-counters-migration.md.
"""

import sys

from gnr.core.cli import GnrCliArgParse

description = "move the counters of an instance from adm.counter to sys.counter"


def main(instance):
    parser = GnrCliArgParse(description=description)
    parser.add_argument('--counters',
                        help="'*' or pkg.table.field,...; default: the experimental switch new_counters/counters")
    parser.add_argument('--table', action='append', dest='tables', metavar='PKG.TABLE',
                        help='only the counters of this table (repeatable)')
    parser.add_argument('--load', action='store_true',
                        help='build the blocks of the periods not loaded yet; without it nothing is written')
    options = parser.parse_args()

    db = instance.db
    sys_counter = db.table('sys.counter')
    if not sys_counter.countersToMigrate(options.counters, options.tables):
        print('No counter to migrate: set <experimental><new_counters counters="..."/></experimental> '
              'in instanceconfig.xml, or pass --counters')
        sys.exit(1)
    report = sys_counter.migrateCounters(counters=options.counters, tables=options.tables, load=options.load)
    if options.load:
        db.commit()

    totals = {}
    for row in report:
        totals[row['status']] = totals.get(row['status'], 0) + 1
        print('%(table)s.%(field)s  %(period)s  %(count)s numbers  %(status)s' % row)
        for problem in row['problems']:
            if problem['kind'] == 'not_loaded':
                continue
            details = ', '.join('%s=%s' % (k, v) for k, v in problem.items() if k != 'kind')
            print('    %s %s' % (problem['kind'], details))
    print('\n%s periods: %s' % (len(report), ', '.join('%s %s' % (n, status) for status, n in sorted(totals.items()))))
    if not options.load and totals.get('not_loaded'):
        print('Nothing written: run again with --load to build the blocks of the periods not loaded yet.')
    if totals.get('errors'):
        sys.exit(2)
