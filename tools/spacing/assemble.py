#!/usr/bin/env python3
"""Put the spaced pieces back:  python3 assemble.py WORKDIR OUT.xml [--from out]

Reads the original TEI named in WORKDIR/meta.json, replaces every text line
with its line from WORKDIR/out/NNN.xml (a piece without output keeps the
original), restores the masked notes and writes OUT.xml.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MASK_RE, load_meta

work, outp = sys.argv[1], sys.argv[2]
sub = sys.argv[sys.argv.index('--from') + 1] if '--from' in sys.argv else 'out'
meta = load_meta(work)
lines = open(meta['tei'], encoding='utf8').read().split('\n')
missing = []
for name, idx in meta['pieces'].items():
    p = os.path.join(work, sub, name + '.xml')
    if not os.path.exists(p):
        missing.append(name); continue
    new = open(p, encoding='utf8').read().rstrip('\n').split('\n')
    assert len(new) == len(idx), (name, len(new), len(idx))
    for i, s in zip(idx, new):
        lines[i] = MASK_RE.sub(lambda m: meta['notes'][m.group(1)], s)
open(outp, 'w', encoding='utf8').write('\n'.join(lines))
print('written', outp, '; pieces without output (kept as they were):', ' '.join(missing) or 'none')
