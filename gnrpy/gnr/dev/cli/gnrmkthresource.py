#!/usr/bin/env python
# encoding: utf-8
import os
from collections import defaultdict

from gnr.core.cli import GnrCliArgParse
from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrApp
from gnr.core.gnrlang import uniquify
from gnr.web.gnrmenu import MenuStruct

class ThResourceMaker(object):
    def __init__(self, options, args):
        self.options= options
        self.args = args
        self.option_force = getattr(options, 'force', False)
        self.option_menu = getattr(options, 'menu', False)
        self.option_name = getattr(options, 'name', None)
        self.option_output = getattr(options, 'create_instance', None)
        self.option_indent = getattr(options, 'indent', 4)
        self.option_columns = int(getattr(options, 'columns', 2))
        self.option_guess_size = getattr(options, 'guess_size', False)
        self.packages = dict()
        self.pkg_tables = defaultdict(list)
        self.packageMenus = dict()
        for table_name in self.args:
            if '.' in table_name:
                full_pkg_name, table_name = table_name.split('.')
            else:
                full_pkg_name = table_name
                table_name = '*'
            self.packages[full_pkg_name]=True
            if ':' in full_pkg_name:
                pkg_name = full_pkg_name.split(':')[1]
            else:
                pkg_name = full_pkg_name
            self.pkg_tables[pkg_name].append(table_name)
        config=Bag()
        config.setItem('db',None,dbname='_dummydb')
        for pkg in self.packages:
            config['packages.%s'%pkg]=None
        self.app=GnrApp(custom_config=config)
    
    def makeResources(self):
        hasLookups=False
        tables=[]
        for pkg, tbl_names in list(self.pkg_tables.items()):
            for tbl_name in tbl_names:
                if tbl_name=='*':
                    tables.extend([(pkg,t) for t in list(self.app.db.package(pkg).tables)])
                    break
                else:
                    tables.append((pkg,tbl_name))
        tables = uniquify(tables)
        if len(tables)>1 and (self.option_output or self.option_name):
            if self.option_name:
                print('-n/--name option is incompatible with multiple table mode')
            if self.option_name:
                print('-o/--output option is incompatible with multiple table mode')
            exit(-1)
        for pkg in list(self.pkg_tables.keys()):
            packageFolder = self.app.packages(pkg).packageFolder
            path = os.path.join(packageFolder,'menu.xml')
            self.packageMenus[pkg] = Bag(path) if os.path.exists(path) else Bag()

        for package,table in tables:
            if 'lookup' in self.app.db.table('%s.%s'%(package,table)).attributes:
                hasLookups=True
                continue
            else:
                self.createResourceFile(pkg, table)
        if self.option_menu:
            for pkg in list(self.pkg_tables.keys()):
                packageFolder = self.app.packages(pkg).packageFolder
                xmlmenupath = os.path.join(packageFolder,'menu.xml')
                if hasLookups:
                    self.packageMenus[package].setItem('auto.lookups', None, label="!!Lookup tables", 
                                                                    pkg=pkg, tag='lookupBranch')
                self.packageMenus[pkg].toXml(xmlmenupath)
                ms = MenuStruct(xmlmenupath)
                ms.toPython(os.path.join(packageFolder,'menu.py'))
                os.remove(xmlmenupath)
        
    def write(self, out_file, line=None, indent=0):
        line = line or ''
        out_file.write('%s%s\n'%(self.option_indent*indent*' ',line))

    def writeHeaders(self, out_file):
        self.write(out_file, '#!/usr/bin/python3')
        self.write(out_file, '# -*- coding: utf-8 -*-')
        self.write(out_file)
    
    def writeImports(self, out_file):
        self.write(out_file, "from gnr.web.gnrbaseclasses import BaseComponent")
        self.write(out_file, "from gnr.core.gnrdecorator import public_method")
        self.write(out_file)
    
    def writeViewClass(self, out_file, columns):
        self.write(out_file, "class View(BaseComponent):")
        self.write(out_file)
        self.write(out_file, "def th_struct(self,struct):", indent=1)
        self.write(out_file, 'r = struct.view().rows()', indent=2)
        for column, size in columns:
            if self.option_guess_size:
                self.write(out_file, "r.fieldcell('%s', width='%iem')"%(column,size), indent=2)
            else:
                self.write(out_file, "r.fieldcell('%s')"%column, indent=2)
        self.write(out_file)
        self.write(out_file, "def th_order(self):", indent=1)
        self.write(out_file, "return '%s'"%columns[0][0], indent=2)
        self.write(out_file)
        self.write(out_file, "def th_query(self):", indent=1)
        self.write(out_file, "return dict(column='%s', op='contains', val='')"%columns[0][0], indent=2)
        self.write(out_file)
        self.write(out_file)
        self.write(out_file)
    
    def writeFormClass(self, out_file, columns):
        self.write(out_file, "class Form(BaseComponent):")
        self.write(out_file)
        self.write(out_file, "def th_form(self, form):", indent=1)
        self.write(out_file, "pane = form.record", indent=2)
        self.write(out_file, "fb = pane.formbuilder(cols=%i, border_spacing='4px')"%self.option_columns, indent=2)
        for column, size in columns:
            self.write(out_file, "fb.field('%s')"%column, indent=2)
        self.write(out_file)
        self.write(out_file)
        self.write(out_file, "def th_options(self):", indent=1)
        self.write(out_file, "return dict(dialog_height='400px', dialog_width='600px')", indent=2)


    def createResourceFile(self, package, table):
        packageFolder = self.app.packages(package).packageFolder
        resourceFolder = os.path.join(packageFolder,'resources', 'tables', table)

        # populate the menu anyway, even if the resource already exists
        if self.option_menu:
            self.packageMenus[package].setItem('auto.%s' %table,None,label='!!%s' %table.capitalize(),
                                                            table='%s.%s' %(package,table), tag='thpage')

        if not os.path.exists(resourceFolder) and not self.option_output:
            os.makedirs(resourceFolder)
        if self.option_name and not self.option_name.endswith('.py'):
            self.option_name = '%s.py'%self.option_name
        name = self.option_name or 'th_%s.py'%table
        path = os.path.join(resourceFolder, name) if not self.option_output else self.option_output
        if os.path.exists(path) and not self.option_force:
            print('%s exist: will be skipped, use -f/--force to force replace' % name)
            return
        columns = []
        max_size = 35
        tbl_obj =  self.app.db.table('%s.%s'%(package,table))
        for col_name in tbl_obj.columns:
            if col_name=='id' or col_name.startswith('__'):
                continue
            column = tbl_obj.columns[col_name]
            if column.dtype=='A':
                size = column.attributes.get('size','')
                if size:
                    if ':' in size:
                        size =size.split(':')[1]
                else:
                    size=max_size
                size = max(int(size),max_size)
            else:
                size = 7
            columns.append((column.name,size))

        with open(path,'w') as out_file:
            self.writeHeaders(out_file)
            self.writeImports(out_file)
            self.writeViewClass(out_file, columns)
            self.writeFormClass(out_file, columns)
            print(f'{name} created, columns:', ', '.join([f'{x[0]} ({x[1]})' for x in columns]))

description = "create TableHandler resources automatically from model"

def main():
    old_description = """
    gnrmkthresource is used to create TableHandler resources
    automatically from model
    
    The syntax is:
    
    gnrmkthresource projectName:packageName.tableName [Optional suffixes]
    
    where:
    
    - \"projectName\": name of the project 
    - \"packageName\": name of the package
    - \"tableName\": name of the table for which you create the resource
    """
    parser = GnrCliArgParse(description=description)
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

    parser.add_argument("args", nargs="*")
    options = parser.parse_args()
    thresourcemaker = ThResourceMaker(options, options.args)
    thresourcemaker.makeResources()
        
if __name__ == '__main__':
    main()
