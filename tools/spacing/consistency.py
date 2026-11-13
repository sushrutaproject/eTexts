#!/usr/bin/env python3
"""Cross-text consistency scan of a spaced TEI file.

  python3 consistency.py SPACED.xml [--top 80] [--particles]

Lists strings that the spaced text has both as one token and as two tokens
(e.g. "tadeva" in one chapter, "tad eva" in another), most frequent first,
with the line numbers of each form. With --particles, lists joined forms
ending in a particle (ca, tu, eva, api, iti, vā, hi, cet, iva) that are split
at least as often elsewhere (yacca / yac ca, tadeva / tad eva …).
Notes are not scanned (they are not spaced). Fix only the clear cases, by hand
or with fix.py.
"""
import argparse, collections, re, sys

ap = argparse.ArgumentParser()
ap.add_argument('spaced')
ap.add_argument('--top', type=int, default=80)
ap.add_argument('--particles', action='store_true')
ap.add_argument('--min', type=int, default=5, help='minimum length of the joined string')
ap.add_argument('--orig', help='the unspaced file: count only splits made by an added space')
a = ap.parse_args()

lines = open(a.spaced, encoding='utf8').read().split('\n')
olines = open(a.orig, encoding='utf8').read().split('\n') if a.orig else None
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import added_spaces


def mark_added(ln, no):
    """replace every added space by U+2423 so that tokens can be told apart"""
    if olines is None:
        return ln
    try:
        pos = set(added_spaces(olines[no - 1], ln))
    except ValueError:
        return ln
    return ''.join('\u2423' if i in pos else c for i, c in enumerate(ln))
J = collections.Counter()          # token -> count
S = collections.Counter()          # joined pair -> count
WJ = collections.defaultdict(list)
WS = collections.defaultdict(list)
PAIR = collections.defaultdict(collections.Counter)
inbody = False
for no, ln in enumerate(lines, 1):
    if '<body' in ln:
        inbody = True
    if not inbody:
        continue
    t = re.sub(r'<note\b.*?</note>', ' ', mark_added(ln, no))
    t = re.sub(r'<label\b.*?</label>', ' ', t)
    t = re.sub(r'<[^>]+>', '', t)
    # tokens; with --orig a pair counts as split only across an added space
    raw = re.split(r'([\s\u2423]+)', t)
    toks, seps = [], []
    for k in range(0, len(raw), 2):
        x = raw[k].strip('|‘’“”"()[],.;:?!-–—')
        sp = raw[k - 1] if k else ' '
        if x and not x.isdigit():
            toks.append(x); seps.append(sp)
    for x in toks:
        J[x] += 1
        if len(WJ[x]) < 6:
            WJ[x].append(no)
    for x, y, sp in zip(toks, toks[1:], seps[1:]):
        if olines is not None and '\u2423' not in sp:
            continue
        k = x + y
        S[k] += 1
        PAIR[k][x + ' ' + y] += 1
        if len(WS[k]) < 6:
            WS[k].append(no)

if a.particles:
    P = ['ca', 'tu', 'eva', 'api', 'iti', 'vā', 'hi', 'cet', 'iva']
    rows = []
    for k, n in S.items():
        for pair, c in PAIR[k].items():
            x, y = pair.split(' ')
            if y in P and J[k] and c >= J[k] and len(x) >= 2:
                rows.append((J[k], k, pair, c))
    rows.sort(reverse=True)
    for j, k, pair, c in rows[:a.top]:
        print('%-26s joined×%-3d  %-26s split×%-3d  J:%s  S:%s' % (k, j, pair, c, WJ[k], WS[k]))
    print(len(rows), 'joined particle forms split elsewhere')
    sys.exit()

rows = [(min(J[k], S[k]), k) for k in S if k in J and len(k) >= a.min]
rows.sort(reverse=True)
print(len(rows), 'strings found both joined and split')
for m, k in rows[:a.top]:
    forms = ', '.join('%s×%d' % (p, c) for p, c in PAIR[k].most_common(2))
    print('%-28s joined×%-3d split×%-3d (%s)  J:%s  S:%s' % (k, J[k], S[k], forms, WJ[k], WS[k]))
