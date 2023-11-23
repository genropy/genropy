#!/usr/bin/env python
# encoding: utf-8
import sys, os
import argparse

from gnr.app.gnrapp import GnrApp

usage = """
    gnrlocalizer <instance_name> will analize packages of related instance
    and update localization.xml file in every package.
    """

def main():
    parser = argparse.ArgumentParser(usage)
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
