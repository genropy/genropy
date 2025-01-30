# -*- coding: utf-8 -*-
import re
import sys
import os, os.path
import json
from collections import defaultdict
from gnr.core.gnrbag import Bag
from gnr.core.cli import GnrCliArgParse

NOTES_SEARCH = re.compile(r"\{?#[\s]*?(FIXME|ERROR|WARNING|TODO|BUG|WTF)[\s:]?(.+)")
NOTES_SEARCH_END = re.compile(r"(.*)#\}(.*)")
ALLOWED_EXTENSIONS = ['.py','.html','.js']
EXCLUDED_DIRNAME = ['htmlcov', '.eggs', '__pycache__']
PATH_EXCLUDE = re.compile(r".eggs")

description = "Show all annotations like fixme, todo etc in the Genropy codebase"

def main():
    p = GnrCliArgParse(
        description=description
    )
    p.add_argument("-n", "--note",
                   help="Show comments only related to this note",
                   dest="note")
    p.add_argument("-j", "--json",
                   help="Output data in json format",
                   action="store_true", default=False)
    p.add_argument("-b", "--bag",
                   help="Output data in Bag xml format",
                   action="store_true", default=False)
    
    options = p.parse_args()

    start_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"*4))
    found_notes = []
    for top, dirs, files in os.walk(start_path):
        if PATH_EXCLUDE.search(top):
            continue
        if os.path.basename(top) in EXCLUDED_DIRNAME:
            continue
        for filename in files:
            if not os.path.splitext(filename)[1] in ALLOWED_EXTENSIONS:
                continue
            file_fullpath = os.path.join(top, filename)
            with open(file_fullpath, 'r') as fp:
                line_num = 0
                for line in fp.readlines():
                    line_num += 1
                    if NOTES_SEARCH.search(line):
                        note, msg = NOTES_SEARCH.findall(line)[0]
                        if options.note:
                            if note.upper().strip() not in options.note.upper().strip():
                                continue
                        if NOTES_SEARCH_END.search(msg.strip()):
                            msg = NOTES_SEARCH_END.findall(msg.strip())[0][0]
                        found_notes.append(dict(file_path=file_fullpath, line_num=line_num,
                                                note=note, msg=msg.strip()))

    if options.json:
        print(json.dumps(found_notes))
        sys.exit(0)


    # regroup by filepath
    res = defaultdict(list)
    for item in found_notes:
        res[item['file_path']].append(item)

    if options.bag:
        b = Bag(res)
        print(b.toXml())
        sys.exit(0)
    else:
        for file_path, vals in res.items():
            print(f"{file_path}:")
            for v in vals:
                print("{note}:{line_num} - {msg}".format(**v))
            print("")
