#!/usr/bin/env python3
"""Apply consistency fixes:  python3 fix.py IN.xml OUT.xml RULES.txt

RULES.txt has one rule per line, '#' for comments:

    tathāhi => tathā hi        (split: the whole token tathāhi becomes two)
    tad anu => tadanu          (join: removes the space between the two tokens)

A token is matched whole (punctuation such as | ‘ ’ , around it is allowed),
in <body> text outside notes, labels and tags. verify.py afterwards makes sure
that no space of the original was removed. Prints how often each rule applied.
"""
import re, sys

src = open(sys.argv[1], encoding='utf8').read()
rules = []
for ln in open(sys.argv[3], encoding='utf8'):
    ln = ln.split('#', 1)[0].strip()
    if not ln:
        continue
    old, new = [x.strip() for x in ln.split('=>')]
    assert old.replace(' ', '') == new.replace(' ', ''), ln
    rules.append((old, new))

B = r"(?<![^\s|‘’“”\"(\[,.;:?!\-–—])"     # token start
E = r"(?![^\s|‘’“”\"()\],.;:?!\-–—])"      # token end
counts = {}


def fix_text(t):
    for old, new in rules:
        pat = re.compile(B + re.escape(old).replace(r'\ ', r' ') + E)
        t, k = pat.subn(new, t)
        counts[(old, new)] = counts.get((old, new), 0) + k
    return t


head, sep, body = src.partition('<body>')
parts = re.split(r'(<note\b.*?</note>|<label\b.*?</label>|<[^>]+>)', body, flags=re.S)
body = ''.join(p if p.startswith('<') else fix_text(p) for p in parts)
open(sys.argv[2], 'w', encoding='utf8').write(head + sep + body)
for (old, new), k in counts.items():
    print('%5d  %s => %s' % (k, old, new))
print(sum(counts.values()), 'changes')
