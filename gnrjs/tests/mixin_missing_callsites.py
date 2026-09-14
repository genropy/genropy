import re,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2]
names=set(re.findall(r'^- `([^`]+)`',(root/'docs/bag-audit/mixin-missing-methods.md').read_text(),re.M))
paths=subprocess.check_output(['rg','--files','gnrjs','resources','projects','-g','*.js','-g','*.py','-g','!*.min.js','-g','!genro_bagjs_bundle.js','-g','!**/js_libs/**'],cwd=root,text=True).splitlines()
uses={n:[] for n in sorted(names)}
patt=re.compile(r'(?P<receiver>[\w.$]+|\))\s*(?:\.\s*(?P<dot>\w+)|\[\s*[\'"](?P<bracket>\w+)[\'"]\s*\])\s*\(')
for p in paths:
 if '/tests/' in p or p.endswith(('/gnrbag.js','/gnrbag_genro.js','/gnrbag_mixin.js')):continue
 for i,line in enumerate((root/p).read_text(errors='replace').splitlines(),1):
  if line.lstrip().startswith(('//','#')):continue
  for m in patt.finditer(line):
   n=m['dot'] or m['bracket']
   if n in uses:uses[n].append(dict(file=p,line=i,receiver=m['receiver'],text=line.strip()))
(root/'docs/bag-audit/mixin-missing-callsites.json').write_text(json.dumps(uses,indent=2)+'\n')
for n,rows in uses.items():
 print(n,len(rows),'JS',sum(r['file'].endswith('.js') for r in rows))
print('scanned',len(paths))
