"""Collect candidate uses of every legacy member, including embedded JS in Python."""
import json
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[2]
report_dir = root / 'docs' / 'bag-audit'
rows = json.loads((report_dir / 'surface.json').read_text())
names = {row['member'] for row in rows} - {'constructor'}
pattern = re.compile(r'\.\s*([A-Za-z_$][\w$]*)\s*\(|\[\s*[\'\"]([^\'\"]+)[\'\"]\s*\]\s*\(')
uses = {name: [] for name in names}
paths = subprocess.check_output(['rg', '--files', 'gnrjs', 'resources', 'projects',
                                 '-g', '*.js', '-g', '*.py', '-g', '!genro_bagjs_bundle.js'],
                                cwd=root, text=True).splitlines()
for relative in paths:
    if relative.startswith('gnrjs/tests/') or relative.endswith(('/gnrbag.js', '/gnrbag_mixin.js')):
        continue
    for number, line in enumerate((root / relative).read_text(errors='replace').splitlines(), 1):
        for match in pattern.finditer(line):
            name = match.group(1) or match.group(2)
            if name in uses:
                uses[name].append(f'{relative}:{number}')
result = {name: {'candidate_count': len(locations), 'locations': locations}
          for name, locations in sorted(uses.items())}
(report_dir / 'callsites.json').write_text(json.dumps(result, indent=2) + '\n')
print(f'{len(paths)} source files scanned; {len(uses)} distinct member names. '
      'Matches are candidates, not inferred receiver types; computed names require runtime tests.')
