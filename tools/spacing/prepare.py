#!/usr/bin/env python3
"""Cut a TEI file (one <ab>/<head> per line) into pieces for the spacing agents.

  python3 prepare.py TEI WORKDIR [--target 28000] [--keep-notes]

Writes WORKDIR/in/NNN.xml (the text lines of whole chapters, or of part of a long
chapter cut at a line boundary), WORKDIR/meta.json (line numbers of every piece,
the masked notes) and an INSTRUCTIONS.md filled in for WORKDIR. Unless
--keep-notes is given, every <note>…</note> is replaced by <note n="§K"/> so that
the agents cannot touch the notes; assemble.py puts them back.
"""
import argparse, json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import NOTE_RE, body_lines, text_len

ap = argparse.ArgumentParser()
ap.add_argument('tei')
ap.add_argument('work')
ap.add_argument('--target', type=int, default=28000, help='text characters per piece')
ap.add_argument('--keep-notes', action='store_true')
ap.add_argument('--work-title', default=None, help='name of the work, for INSTRUCTIONS.md')
a = ap.parse_args()

lines = open(a.tei, encoding='utf8').read().split('\n')
idx = body_lines(lines)
notes = {}

def mask(s):
    if a.keep_notes:
        return s
    def rep(m):
        k = str(len(notes) + 1)
        notes[k] = m.group(0)
        return '<note n="§%s"/>' % k
    return NOTE_RE.sub(rep, s)

# chapter = run of text lines between two <div lines
chapters, cur, last = [], [], None
for i in idx:
    if last is not None and any(lines[j].strip().startswith(('<div', '</div')) for j in range(last + 1, i)):
        chapters.append(cur)
        cur = []
    cur.append(i)
    last = i
if cur:
    chapters.append(cur)

def tl(i):
    return text_len(NOTE_RE.sub('', lines[i]))     # notes are not spaced

def size(p):
    return sum(tl(i) for i in p)

pieces = []           # list of line-index lists
for ch in chapters:
    n = size(ch)
    if pieces and size(pieces[-1]) + n <= a.target:      # small chapters share a piece
        pieces[-1] = pieces[-1] + ch
    elif n <= a.target * 1.3:
        pieces.append(list(ch))
    else:                                                # long chapter: cut at line boundaries
        k = max(2, round(n / a.target))
        per = n / k
        part, acc = [], 0
        for i in ch:
            part.append(i)
            acc += tl(i)
            if acc >= per and len(part) and k > 1:
                pieces.append(part)
                part, acc, k = [], 0, k - 1
        if part:
            pieces.append(part)

# a tiny piece (e.g. a section heading alone) goes with the next one
i = 0
while i < len(pieces) - 1:
    if size(pieces[i]) < 1000:
        pieces[i + 1] = pieces[i] + pieces[i + 1]
        del pieces[i]
    else:
        i += 1

os.makedirs(os.path.join(a.work, 'in'), exist_ok=True)
os.makedirs(os.path.join(a.work, 'out'), exist_ok=True)
meta = {'tei': os.path.abspath(a.tei), 'pieces': {}, 'notes': notes if not a.keep_notes else {}}
for no, p in enumerate(pieces, 1):
    name = '%03d' % no
    with open(os.path.join(a.work, 'in', name + '.xml'), 'w', encoding='utf8') as f:
        f.write('\n'.join(mask(lines[i]) for i in p) + '\n')
    meta['pieces'][name] = p
# masking must run in piece order so that note numbers follow the text
with open(os.path.join(a.work, 'meta.json'), 'w', encoding='utf8') as f:
    json.dump(meta, f, ensure_ascii=False)

here = os.path.dirname(os.path.abspath(__file__))
ins = open(os.path.join(here, 'INSTRUCTIONS.md'), encoding='utf8').read()
ins = ins.replace('{DIR}', os.path.abspath(a.work)).replace('{TOOLS}', here)
if a.work_title:
    ins = ins.replace('{WORK}', a.work_title)
open(os.path.join(a.work, 'INSTRUCTIONS.md'), 'w', encoding='utf8').write(ins)
for name, p in meta['pieces'].items():
    print(name, 'lines %d-%d' % (p[0] + 1, p[-1] + 1), 'chars', size(p))
print(len(pieces), 'pieces;', len(notes), 'notes masked')
