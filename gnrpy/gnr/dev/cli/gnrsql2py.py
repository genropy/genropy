#!/usr/bin/env python
# encoding: utf-8

import os
import re

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrdeploy import PackageMaker, PathResolver
from gnr.sql.gnrsql import GnrSqlDb

CONN_STRING_RE=r"(?P<user>\w*)\:?(?P<password>\w*)\@(?P<host>(\w|\.)*)\:?(?P<port>\w*)\/(?P<database>(\w|\.)*)"
CONN_STRING = re.compile(CONN_STRING_RE)


def structToPy(tables, path):

    header = """# encoding: utf-8
from gnr.core.gnrbag import Bag, BagResolver
class Table(object):
    def config_db(self, pkg):
        tbl =  pkg.table('%s', pkey='%s', name_long='%s')
"""
    for tablename, columns, attributes in tables.digest('#k,#v.columns,#a'):
        f = open(os.path.join(path, '%s.py' % tablename), 'w')
        pkey = attributes.get('pkey')
        f.write(header % (tablename, pkey, tablename))
        for column in columns:
            colName = column.label
            colAttr = column.attr
            colAttr.pop('default', None)
            colAttr['name_long'] = '!!%s' % colName.title()
            colAttr.pop('tag', None)
            atlst = []
            for k, v in list(colAttr.items()):
                atlst.append("%s ='%s'" % (k, v))
            f.write("        tbl.column('%s', %s)" % (colName, ', '.join(atlst)))
            value = column.value
            if hasattr(value, '_htraverse'):
                relation_attr = column.value.getAttr('relation') or {}
                if 'relation' in value and 'related_column' in relation_attr:
                    f.write(".relation('%s', mode='foreignkey')"%relation_attr['related_column'])
            f.write("\n")
        f.close()


def parse_connection_string(connection_string):
    conn = dict()
    match = re.search(CONN_STRING, connection_string)
    conn['user'] = match.group('user') or None
    conn['password'] = match.group('password') or None
    conn['host'] = match.group('host') or None
    conn['port'] = match.group('port') or None
    conn['database'] = match.group('database') or None
    return conn

description = "used to translate an existing database to python model files"

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('-i', '--implementation',
                      dest='implementation', default='postgres',
                      help='Database implementation (postgres|mysql|sqlite|mssql')
    parser.add_argument('-p', '--package', dest='package', help='Do only these packages (comma separated)')
    parser.add_argument('-P', '--project', dest='project', help='Add packages to this project')
    parser.add_argument("connection_string", help="user:password@host:port/database")

    options = parser.parse_args()
    conn = parse_connection_string(options.connection_string)
    base_path = None

    if options.project:
        path_resolver = PathResolver()
        base_path = os.path.join(path_resolver.project_name_to_path(options.project), 'packages')
        
    db = GnrSqlDb(implementation=options.implementation, dbname=conn['database'],
                  host=conn['host'], user=conn['user'], password=conn['password'], port=conn['port'],
                  main_schema=None)

    db.importModelFromDb()
    struct = db.model.src
    packages = list(struct['packages'].keys())
    allowed_packages = [p.strip() for p in options.package.split(',')] if options.package else []
    for package in packages:
        if not struct[f'packages.{package}.tables']:
            continue
        
        if allowed_packages and package not in allowed_packages:
            continue
        
        package_maker = PackageMaker(package, sqlprefix='', base_path = base_path)
        print(dir(package_maker))
        print(f'Creating package {package} in {package_maker.package_path}')
        package_maker.do()
        print(f'Package {package} done')
        print(f'Creating model files {package_maker.model_path}')
        structToPy(struct[f'packages.{package}.tables'], package_maker.model_path)
        print(f'Model files for package {package} done')

if __name__=='__main__':
    main()
