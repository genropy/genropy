#!/usr/bin/env python
# encoding: utf-8
import os
import sys
import ast
from pathlib import Path
from collections import defaultdict

from gnr.core.cli import GnrCliArgParse
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import uniquify
from gnr.app.gnrapp import GnrApp
from gnr.app.gnrdeploy import ThPackageResourceMaker
from gnr.web.gnrmenu import MenuStruct
from gnr.dev import logger


class CliResourceMaker(object):
    def __init__(self, options, models):
        self.options = options
        self.app = GnrApp(self.options.instance_name)
        self.models = models
        
    def run(self):
        needed_resources = defaultdict(list)
        
        for table_name in self.models:
            if '.' in table_name:
                full_pkg_name, table_name = table_name.split('.')
            else:
                full_pkg_name = table_name
                table_name = '*'
            if ':' in full_pkg_name:
                pkg_name = full_pkg_name.split(':')[1]
            else:
                pkg_name = full_pkg_name
            needed_resources[pkg_name].append(table_name)

        for pkg, tables in needed_resources.items():
            try:
                resource_maker = ThPackageResourceMaker(self.app, package=pkg, tables=tables,
                                                        force=self.options.force,
                                                        menu=self.options.menu,
                                                        columns=self.options.columns,
                                                        guess_size=self.options.guess_size,
                                                        indent=self.options.indent,
                                                        filename=self.options.name,
                                                        output=self.options.output)
                resource_maker.makeResources()
            except Exception as e:
                logger.error(e)
        
    
            
description = "create TableHandler resources automatically from model"


def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument("instance_name")
    parser.add_argument("-f", "--force", dest="force", action='store_true', default=False,
                        help="force the resource creation also if destination file exists")
    parser.add_argument("-m", "--menu", dest="menu", action='store_true', default=False,
                        help="create the menu for the th pages")
    parser.add_argument("-n", "--name", dest="name", 
                        help="output file name, the file will be, will work only if single table is passed")
    parser.add_argument("-o", "--output", dest="output",
                        help="""output file path will override -n/--name and automatic file placement in resources/tables/tablename, 
                        will work only if single table is passed""")
    parser.add_argument("-i", "--indent", dest="indent", default=4,
                        help="number of spaces of each level of indentation in the output file(s)")
    parser.add_argument("-g", "--guess_size", dest="guess_size", action='store_true', default=False, 
                        help="tries to guess the View column size")
    parser.add_argument("-c", "--columns", dest="columns", default=2,
                        help="number of columns in Form")
    parser.add_argument("models", nargs="+",
                        help="list of models in the form of packagename.modelname or project:packagename.modelname")
    options = parser.parse_args()
    if len(options.models) > 1:
        err_mesg = "{option_name} is incompatible with multiple table mode"
        if options.output:
            logger.error(err_mesg.format(option_name = '-o/--output'))
            sys.exit(1)
        if options.name:
            logger.error(err_mesg.format(option_name = '-n/--name'))
            sys.exit(1)
    maker = CliResourceMaker(options, options.models)
    maker.run()
        
if __name__ == '__main__':
    main()
