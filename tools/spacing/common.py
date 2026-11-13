"""Shared helpers for the word-spacing tools (see README.md)."""
import json, os, re

NOTE_RE = re.compile(r'<note\b[^>]*>.*?</note>|<note\b[^>]*/>', re.S)
MASK_RE = re.compile(r'<note n="§(\d+)"/>')
TAG_RE = re.compile(r'<[^>]+>')


def body_lines(lines):
    """indices of the lines that carry text to be spaced: one <ab>/<head>/<p>/<lg>
    element per line, inside <body>"""
    out, inbody = [], False
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith('<body'):
            inbody = True
            continue
        if s.startswith('</body'):
            inbody = False
        if inbody and re.match(r'<(ab|head|p|lg)\b', s):
            if not re.search(r'</(ab|head|p|lg)>\s*$', s):
                raise SystemExit('line %d: element does not close on its own line' % (i + 1))
            out.append(i)
    return out


def text_len(s):
    return len(TAG_RE.sub('', s))


def squash(s):
    return ''.join(s.split())


def added_spaces(old, new):
    """positions in `new` of spaces inserted relative to `old`; raises ValueError
    if `new` is not `old` plus some inserted spaces"""
    i = j = 0
    res = []
    while j < len(new):
        if i < len(old) and old[i] == new[j]:
            i += 1
            j += 1
        elif new[j] == ' ':
            res.append(j)
            j += 1
        else:
            raise ValueError('differs at %d: %r / %r' % (j, old[max(0, i - 30):i + 30], new[max(0, j - 30):j + 30]))
    if i != len(old):
        raise ValueError('text missing at the end: %r' % old[i:i + 60])
    return res


def load_meta(work):
    with open(os.path.join(work, 'meta.json'), encoding='utf8') as f:
        return json.load(f)
