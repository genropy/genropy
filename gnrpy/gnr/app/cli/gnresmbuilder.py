#!/usr/bin/env python
import sys

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import GnrApp
from gnr.app.esmbuilder import GnrInstanceEsmBundler

description = "download and bundle ESM JavaScript dependencies for a Genropy instance"


def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('-v', '--verbose',
                        dest='verbose',
                        action='store_true',
                        help='Be verbose')
    parser.add_argument('-f', '--force',
                        dest='force',
                        action='store_true',
                        help='Force re-download and re-bundle ignoring cache')
    parser.add_argument('-o', '--output',
                        dest='output',
                        default=None,
                        metavar='DIR',
                        help='Output directory for bundles (default: <site>/resources/esm/)')
    parser.add_argument('instance_name')
    options = parser.parse_args()

    app = GnrApp(options.instance_name)
    bundler = GnrInstanceEsmBundler(app, verbose=options.verbose)

    try:
        output_dir, results = bundler.run(force=options.force, output=options.output)
    except RuntimeError as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

    if results is None:
        print('No ESM requirements found.')
        return

    print(f'\nAll packages bundled to: {output_dir}')


if __name__ == '__main__':
    main()
    sys.exit(0)
