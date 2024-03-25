#!/usr/bin/env python
# encoding: utf-8
import sys, os

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import GnrApp

description = "analize packages of related instance and update localization.xml file for each one"

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('-a', '--all',
                        dest='scan_all',
                        action='store_true',
                        help="Scan also genro source")
    parser.add_argument('-t', '--translate',
                        dest='translations',
                        action='store_true',
                        help="Translate")

    parser.add_argument("instance_name", nargs=1)
    
    options = parser.parse_args()
    instance_name = options.instance_name[0]
                                          
    app = GnrApp(instance_name)
    if options.translations:
        app.localizer.autoTranslate('en,it,fr,de')
    app.localizer.updateLocalizationFiles(scan_all=options.scan_all)

        
if __name__ == '__main__':
    main()
