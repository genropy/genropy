#!/usr/bin/env python
# encoding: utf-8

import re
import os

from gnr.core.cli import GnrCliArgParse
from gnr.core.gnrbag import Bag

description = ""

class SiteLocalizer(object):
    def __init__(self):
        parser = GnrCliArgParse(description=description)
        
        parser.add_argument("sitepath", nargs="?",
                            default=os.getcwd(),
                            help="the instance path")
        options = parser.parse_args()
        
        self.sitepath = options.sitepath

        siteconf = Bag(os.path.join(self.sitepath, 'siteconfig.xml'))
        instNode = siteconf.getNode('instances.#0')
        self.instId = instNode.label
        self.instancepath = instNode.getAttr('path')

    def do(self):
        missingBag = Bag(os.path.join(self.sitepath, 'data', '_missingloc'))['_missingloc']
        for pkg, mbag in list(missingBag.items()):
            pkglocpath = os.path.join('/usr', 'local', 'genro', 'packages', pkg, 'localization.xml')
            if os.path.exists(pkglocpath):
                pkgloc = Bag(pkglocpath)
            else:
                pkgloc = Bag()
            for missing in list(mbag.values()):
                _key = missing['txt']

                lbl = re.sub('\W', '_', _key).replace('__', '_')

                if not lbl in pkgloc:
                    pkgloc.setItem(lbl, None, _key=_key, it=_key, en='', fr='', de='')
            pkgloc.toXml(pkglocpath)
            for fpath in mbag.digest('#a.abs_path'):
                os.remove(fpath)


def main():
    mk = SiteLocalizer()
    mk.do()

if __name__ == '__main__':
    main()
    
    
