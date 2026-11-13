#!/usr/bin/env python3
"""Whole-file check of a spaced (and verse-tagged) TEI file against the original.

  python3 verify.py ORIGINAL.xml NEW.xml [--rng tei_all.rng]

- letters: NEW minus its <lg>/<l> tags = ORIGINAL plus inserted spaces only
  (no letter, punctuation, markup or existing space changed or removed);
- tags: the list of tags is identical apart from the added <lg>/<l>;
- notes: every <note> identical, character for character;
- xml:ids identical; NEW well-formed; with --rng, NEW validates (e.g. tei_all.rng
  from https://tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng).
Prints the number of spaces added and of <lg>/<l> elements.
"""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import TAG_RE, NOTE_RE, added_spaces

ap = argparse.ArgumentParser()
ap.add_argument('orig')
ap.add_argument('new')
ap.add_argument('--rng')
a = ap.parse_args()
o = open(a.orig, encoding='utf8').read()
n = open(a.new, encoding='utf8').read()
VERSE = re.compile(r'</?lg\b[^>]*>|</?l\b[^>]*>')
ok = True
n0 = VERSE.sub('', n)
o0 = VERSE.sub('', o)
try:
    k = len(added_spaces(o0, n0))
    print('letters-ok: %d spaces added' % k)
except ValueError as e:
    ok = False
    print('LETTERS-CHANGED', e)
if TAG_RE.findall(o0) == TAG_RE.findall(n0):
    print('tags-ok')
else:
    ok = False
    print('TAGS-CHANGED')
if NOTE_RE.findall(o) == NOTE_RE.findall(n):
    print('notes-ok (%d notes unchanged)' % len(NOTE_RE.findall(o)))
else:
    ok = False
    print('NOTES-CHANGED')
ids = lambda s: re.findall(r'xml:id="([^"]+)"', s)
if ids(o) == ids(n):
    print('xml:ids-ok')
else:
    ok = False
    print('XML-IDS-CHANGED')
print('verse elements: %d <lg> (%d of them old), %d <l>' % (
    len(re.findall(r'<lg\b', n)), len(re.findall(r'<lg\b', o)), len(re.findall(r'<l\b(?!abel)', n))))
from lxml import etree
try:
    doc = etree.fromstring(n.encode('utf8'))
    print('xml-ok')
except etree.XMLSyntaxError as e:
    ok = False
    print('XML-BROKEN', e)
    doc = None
if a.rng and doc is not None:
    rng = etree.RelaxNG(etree.parse(a.rng))
    if rng.validate(doc):
        print('valid against', os.path.basename(a.rng))
    else:
        ok = False
        print('INVALID:')
        for e in list(rng.error_log)[:10]:
            print('  ', e)
sys.exit(0 if ok else 1)
