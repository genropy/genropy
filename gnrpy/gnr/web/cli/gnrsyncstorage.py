#!/usr/bin/env python
# encoding: utf-8

import os

from gnr.core.cli import GnrCliArgParse
from gnr.web.gnrwsgisite import GnrWsgiSite
from gnr.core.gnrsys import expandpath

try:
    import progressbar
    PROGRESS = progressbar.ProgressBar()
except ImportError:
    PROGRESS = None

description = "copy files between tow storages"

def sync_to_service(site=None, from_storage=None, to_storage=None, skip_existing=True, skip_same_size=False):
    done_path = expandpath('~/.gnrstsync.%s.%s.%s'%(site, from_storage, to_storage))
    done_list = None
    if os.path.exists(done_path):
        with open(done_path) as done_file:
            done_list = done_file.read().split('\n')
    s=GnrWsgiSite(site)
    with open(done_path, 'a') as done_file:
        def doneCb(src):
            done_file.write(src.fullpath)
            done_file.write('\n')
            done_file.flush()
        stor = s.storage(from_storage)
        stor.sync_to_service(to_storage, thermo=PROGRESS, done_list=done_list, doneCb=doneCb)
    os.unlink(done_path)

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('-s', '--skip_same_size', action="store_true", dest='skip_same_size',
                        help="Skip same size files")
    parser.add_argument('-e', '--skip_existing', action="store_true", dest='skip_existing',
                        help="Skip existing files")
    parser.add_argument('site_name',
                        action='append',
                        nargs=1)

    parser.add_argument('from_storage',
                        action='append',
                        nargs=1)
    
    parser.add_argument('to_storage',
                        action='append',
                        nargs=1)

    options = parser.parse_args()
    args = [
        options.site_name[0][0],
        options.from_storage[0][0],
        options.to_storage[0][0]
    ]
    kwargs = dict(skip_same_size=options.skip_same_size,
                  skip_existing=options.skip_existing)
    sync_to_service(*args, **kwargs)

if __name__ == "__main__":
    main()

