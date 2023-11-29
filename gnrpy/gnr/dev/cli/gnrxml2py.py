#!/usr/bin/env python
# encoding: utf-8
import os

from gnr.core.cli import GnrCliArgParse
from gnr.core.gnrbag import Bag


description = "translate 4d genro xml to python model files"


def structToPy(tables, path):
    #shutil.rmtree(path,True)
    #os.makedirs(path)
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
                    f.write(".relation('%s', mode='foreignkey')" % relation_attr['related_column'])
            f.write("\n")
        f.close()


def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('xmlpath')
    options = parser.parse_args()
    struct = Bag(options.xmlpath)
    packages = struct.get('package', None)
    if packages:
        packages = list(struct['packages'].keys())
        for package in packages:
            if not os.path.isdir(package):
                os.makedirs(package)
            structToPy(struct['packages.%s.tables'%package], package)
    else:
        print(f"No packages found in {options.xmlpath}")
            
if __name__=='__main__':
    main()
