#!/usr/bin/env python
# encoding: utf-8

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import GnrApp
from gnr.sql.gnrsqlprivacy import privacy_report, privacy_report_text, privacy_report_tsv

description = "list the columns marked as personal data and the unmarked suspects (model only)"


def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument("instance_name", nargs=1)
    parser.add_argument("--format", dest="output_format", choices=("text", "tsv"),
                        default="text", help="output format")
    # gnr logs on stdout: a file keeps the report clean of startup warnings
    parser.add_argument("-o", "--output", dest="output_path", default=None,
                        help="write the report to this file instead of stdout")
    options = parser.parse_args()
    app = GnrApp(options.instance_name[0])
    rows = privacy_report(app.db)
    formatter = privacy_report_tsv if options.output_format == 'tsv' else privacy_report_text
    report = formatter(rows)
    if options.output_path:
        with open(options.output_path, 'w') as output_file:
            output_file.write(report)
    else:
        print(report, end='')


if __name__ == '__main__':
    main()
