#!/usr/bin/env python3
"""Space before an avagraha, uniformly:  python3 avagraha.py IN.xml OUT.xml

"te'pi" → "te 'pi", "khaṇḍo'yaṃ" → "khaṇḍo 'yaṃ" (an apostrophe after word-final
e/o, before a letter: the elided a of the next word), as the Aṣṭāṅgasaṅgraha
writes it. An apostrophe after ā ("vā'pi", "pācanā'dhyāya") marks a fused
vowel and is left joined (rule 3). Only text in <body> outside notes and tags
is touched; only spaces are added.
"""
import re, sys

src = open(sys.argv[1], encoding='utf8').read()
head, sep, body = src.partition('<body>')
AV = re.compile(r"(?<=[^\W\d_][eo])(?='[^\W\d_])")
n = 0


def fix_text(t):
    global n
    new, k = AV.subn(' ', t)
    n += k
    return new


parts = re.split(r'(<note\b.*?</note>|<[^>]+>)', body, flags=re.S)
body = ''.join(p if p.startswith('<') else fix_text(p) for p in parts)
open(sys.argv[2], 'w', encoding='utf8').write(head + sep + body)
print(n, 'spaces added before an avagraha')
