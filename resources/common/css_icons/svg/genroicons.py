"""
Ghigo's helper script to generate css file from files

"""

import os
import shutil
import sys

from gnr.core.gnrbag import Bag

FPATH = '/Users/fporcari/sviluppo/genro/resources/common/css_icons/svg'
if len(sys.argv) > 1:
    FPATH = sys.argv[1]

for f in os.listdir(FPATH):
    oldpath = os.path.join(FPATH,f)
    if '16' in f:
        newpath = os.path.join(FPATH,'16',f.replace('_16x16','').lower())
        if not os.path.isdir(oldpath):
            shutil.move(oldpath,newpath)

for s in (16,):
    b=Bag(os.path.join(FPATH,str(s)))
    pars={}
    r=[]
    pars['size']=s
    pars['height']=s+2
    pars['width']=s+6
    r.append(f"/* @group size{s} /*")
    for name in b['#0'].digest('#a.file_name'):
        pars['name']=name
        r.append(f"""
     .{name}{{
       background: url({s}/{name}.svg) no-repeat center center;
       }}""")
    r.append("/* @end */\n\n")
    print('\n'.join(r))
