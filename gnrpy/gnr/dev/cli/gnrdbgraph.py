#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import sys
import subprocess
from io import StringIO

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import GnrApp

"""example:   gnrdbgraph -O genropynet sys adm"""

def loadRelations(app, tables):
    b = {}
    for full in tables:
        pkg, tbl = full.split('.', 2)
        relCols = app.db.packages['%(pkg)s.tables.%(tbl)s' % {'pkg': pkg, 'tbl': tbl}].relatingColumns
        b[full] = bb = {}
        if relCols:
            for c in relCols:
                pkg_r, tbl_r, fld_r = c.split('.', 3)
                full_r = "%s.%s" % (pkg_r, tbl_r)
                if full_r in tables:
                    bb[full_r] = None
    return b

def quote(s):
    return s.replace('.', '_')

def remove_package(full):
    pkg, tbl = full.split('.', 2)
    return tbl

def writeDigraph(title, relations, remove_package_prefix, out):
    print("digraph", title, "{", file=out)
    for tbl1, tables in list(relations.items()):
        if remove_package_prefix: tbl1 = remove_package(tbl1)
        print(quote(tbl1), file=out)
        for tbl2 in list(tables.keys()):
            if remove_package_prefix: tbl2 = remove_package(tbl2)
            print("  ", quote(tbl2), "->", quote(tbl1), file=out)
    print("}", file=out)


description="This program requires graphviz"

def main():
    p = GnrCliArgParse(
        description=description
    )

    p.add_argument('-T', '--type', dest='output_type',
                   help='Output type (e.g. png, gif)',
                   default="png")
    p.add_argument('-g', '--graphviz-command', dest='graphviz',
                   help="Graphviz command (e.g. dot, neato, circo)",
                   default="dot")
    p.add_argument('-G', '--graphviz-options', dest="graphviz_options",
                   help="Graphviz options",
                   default='')
    p.add_argument('-o', '--output-file', dest='output_file',
                   help='Output file (defaults to <instance name>.<output type>)',
                   default=None)
    p.add_argument('-O', '--auto-open', dest='auto_open', 
                   help="Auto call 'open' on output file (works on MacOSX)",
                   action="store_true",
                   default=False,)
    p.add_argument('-P', '--remove-package-prefix', dest='remove_package_prefix',
                   help="Remove package prefixes", action="store_true",
                   default=False)
    p.add_argument('-D', '--digraph', dest="dump_digraph", action="store_true",
                   help="Output digraph to stdout",
                   default=False)
    
    p.add_argument('params', nargs='*',
                   help="instance package1 package2.table1 package2.table3...")
    
    options = p.parse_args()
    
    params = options.params
    if not params:
        p.print_help()
        sys.exit(1)
        
    instance = params[0]
    packages_and_tables = params[1:]

    app = GnrApp(instance)
    tables = []
    for p_or_t in packages_and_tables:
        exclude = p_or_t.endswith('-')
        if exclude:
            p_or_t = p_or_t[:-1]
        if '.' in p_or_t:
            tt = [p_or_t.lower()]
        else:
            pkg = app.db.packages[p_or_t]
            if pkg:
                tt = ["%s.%s" % (p_or_t, t) for t in list(pkg.tables.keys())]
            else:
                tt = []
                print("Package not found:", p_or_t, file=sys.stderr)
        if not exclude:
            tables.extend(tt)
        else:
            for t in tt:
                if t in tables:
                    tables.remove(t)
    print("Tables:", " ".join(tables))
    relations = loadRelations(app, tables)

    output = options.output_file
    if not output:
        output = f"{instance}.{options.output_type}"
    cmdline = "%(cmd)s -T%(type)s -o%(output)s" % {'cmd': options.graphviz,
                                                   'type': options.output_type,
                                                   'output': output}
    if options.graphviz_options:
        cmdline = f"{cmdline} -G{options.graphviz_options}"
    print(cmdline)
    graphviz = subprocess.Popen(cmdline, stdin=subprocess.PIPE, shell=True)
    buf = StringIO()
    writeDigraph(instance, relations, options.remove_package_prefix, buf)
    if options.dump_digraph:
        print(buf.getvalue())
    graphviz.communicate(buf.getvalue())
    if options.auto_open:
        subprocess.call([f"open {output}"], shell=True)

if __name__ == '__main__':
    main()
