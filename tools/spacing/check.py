#!/usr/bin/env python3
"""Check spacing-agent output:  python3 check.py WORKDIR NNN [NNN ...]   (or 'all')

For every piece: letters-ok (out = in plus inserted spaces only, nothing else
changed or removed), xml-ok (well-formed), tags-ok (identical list of tags),
lines-ok (same number of lines), and the number of spaces added.
"""
import os, re, sys, xml.dom.minidom as md
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import TAG_RE, added_spaces

work = sys.argv[1]
names = sys.argv[2:]
if names == ['all']:
    names = sorted(f[:-4] for f in os.listdir(os.path.join(work, 'in')) if f.endswith('.xml'))
bad = 0
for n in names:
    a = open(os.path.join(work, 'in', n + '.xml'), encoding='utf8').read()
    try:
        b = open(os.path.join(work, 'out', n + '.xml'), encoding='utf8').read()
    except FileNotFoundError:
        print(n, 'MISSING'); bad += 1; continue
    try:
        k = len(added_spaces(a, b)); lt = 'letters-ok'
    except ValueError as e:
        k = len(b) - len(a); lt = 'LETTERS-CHANGED ' + str(e)
    # spaces inside tags are not allowed either
    if TAG_RE.findall(a) != TAG_RE.findall(b):
        tg = 'TAGS-CHANGED'
    else:
        tg = 'tags-ok'
    try:
        md.parseString(('<x xmlns="http://www.tei-c.org/ns/1.0">' + b + '</x>').encode()); wf = 'xml-ok'
    except Exception as e:
        wf = 'XML-BROKEN ' + str(e)
    ln = 'lines-ok' if a.count('\n') == b.count('\n') else 'LINES-CHANGED'
    ok = lt == 'letters-ok' and tg == 'tags-ok' and wf == 'xml-ok' and ln == 'lines-ok'
    bad += not ok
    print(n, lt, wf, tg, ln, 'spaces-added', k)
sys.exit(1 if bad else 0)
