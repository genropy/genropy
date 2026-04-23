#!/usr/bin/env python
# encoding: utf-8

import os
from datetime import datetime

from gnr.core.cli import GnrCliArgParse
from gnr.sql.gnrsql_exceptions import GnrSqlMissingColumn, GnrSqlMissingField, GnrSqlMissingTable
from gnr.web import logger
from gnr.web.gnrwsgisite import GnrWsgiSite


description = "move files from a storage to another, based on db record"


class StorageMover(object):
    def __init__(self, options):
        self.options = options
        self.site = GnrWsgiSite(options.site_name)
        self._log_lines = []

    def _log(self, level, msg, *args):
        text = msg % args if args else msg
        ts = datetime.now().strftime('%H:%M:%S')
        self._log_lines.append('[%s] %s %s' % (level, ts, text))
        getattr(logger, level.lower())(msg, *args)

    def _write_report(self, started_at, candidates, moved, errors):
        dry_run = self.options.dry_run
        ts = started_at.strftime('%Y%m%d_%H%M%S')
        from_storage = self.options.from_storage
        to_storage = self.options.to_storage
        site_name = self.options.site_name
        filename = '%s_%s_to_%s_%s.log' % (site_name, from_storage, to_storage, ts)
        filepath = os.path.join(os.getcwd(), filename)

        mode_label = 'DRY RUN' if dry_run else 'LIVE'
        lines = [
            'Storage Move Report',
            '=' * 60,
            'Site:    %s' % site_name,
            'From:    %s' % from_storage,
            'To:      %s' % to_storage,
            'Column:  %s' % self.options.column,
            'Tables:  %s' % ', '.join(self.options.tables),
            'Mode:    %s' % mode_label,
            'Started: %s' % started_at.strftime('%Y-%m-%d %H:%M:%S'),
            '',
            'Detail',
            '-' * 60,
        ] + self._log_lines + [
            '',
            'Summary',
            '-' * 60,
            'Candidates (files found in source): %d' % candidates,
        ]

        if dry_run:
            lines.append('Would move:                         %d' % candidates)
        else:
            lines.append('Moved:                              %d' % moved)

        lines += [
            'Errors (source file not found):     %d' % errors,
            '',
            'Finished: %s' % datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        ]

        with open(filepath, 'w') as f:
            f.write('\n'.join(lines) + '\n')

        logger.info("Report written to: %s", filepath)

    def _validate_storage(self, storage_name):
        handler = self.site.storage_handler
        if handler.getStorageParameters(storage_name):
            return
        local_path = os.path.join(self.site.site_static_dir, storage_name)
        if os.path.isdir(local_path):
            return
        self._log('ERROR', "Storage '%s' does not exist (not configured and no local directory found at %s)",
                  storage_name, local_path)
        raise SystemExit(1)

    def run(self):
        from_storage = self.options.from_storage
        to_storage = self.options.to_storage
        column = self.options.column
        dry_run = self.options.dry_run
        candidates = 0
        moved = 0
        errors = 0
        started_at = datetime.now()

        try:
            self._validate_storage(to_storage)
            if from_storage == to_storage:
                self._log('ERROR', "'from' and 'to' storage are the same: '%s'", from_storage)
                raise SystemExit(1)

            for table_name in self.options.tables:
                self._log('INFO', "Processing %s table: %s",
                          self.options.site_name, table_name)
                try:
                    tbl = self.site.db.table(table_name)
                except GnrSqlMissingTable:
                    self._log('ERROR', "Table '%s' does not exist", table_name)
                    raise SystemExit(1)
                try:
                    records = tbl.query(
                        subtable='*',
                        where='$%s IS NOT NULL AND $%s LIKE :prefix' % (column, column),
                        prefix='%s:%%' % from_storage,
                        excludeLogicalDeleted=False,
                        excludeDraft=False
                    ).fetch()
                except (GnrSqlMissingColumn, GnrSqlMissingField):
                    self._log('ERROR', "Column '%s' does not exist in table '%s'", column, table_name)
                    raise SystemExit(1)

                for record in records:
                    filepath = record[column]
                    relative_path = filepath.split(':', 1)[1]
                    # dest_path is constructed deterministically; matches dest_node.path
                    dest_path = '%s:%s' % (to_storage, relative_path)

                    src_node = self.site.storageNode(filepath)
                    if not src_node.isfile:
                        self._log('ERROR', "Source file not found: %s", filepath)
                        errors += 1
                        continue

                    candidates += 1
                    if dry_run:
                        self._log('INFO', "[DRY] Would move: %s -> %s", filepath, dest_path)
                        continue

                    self._log('INFO', "Moving: %s -> %s", filepath, dest_path)
                    dest_node = self.site.storageNode(dest_path)
                    # Copy first so source stays intact if the commit below fails.
                    # Delete source only after the DB record is safely committed.
                    src_node.copy(dest_node)
                    new_record = dict(record)
                    new_record[column] = dest_path
                    tbl.raw_update(new_record, record)
                    self.site.db.commit()
                    src_node.delete()
                    moved += 1

            if dry_run:
                logger.info("Dry run complete. %d file(s) to move, %d not found.", candidates, errors)
            else:
                logger.info("Done. Moved %d file(s), %d error(s).", moved, errors)
        finally:
            self._write_report(started_at, candidates, moved, errors)


def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('--dry-run', action="store_true",
                        dest='dry_run',
                        help="Do not execute, just report")
    parser.add_argument('-c', '--column',
                        dest='column',
                        default="filepath",
                        help="The column containing the file path")
    parser.add_argument('-t', '--table',
                        dest='tables',
                        action="append",
                        required=True)

    parser.add_argument('site_name')
    parser.add_argument('from_storage')
    parser.add_argument('to_storage')

    options = parser.parse_args()

    mover = StorageMover(options)
    mover.run()


if __name__ == "__main__":
    main()
