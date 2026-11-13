#!/usr/bin/env python3
"""Tag the verses of the root text by metre:  python3 verse.py IN.xml OUT.xml [--report FILE]

Works on TEI files with one <ab> per line (the e-texts of this repository):
inside every <ab type="mula">, each half-verse (the text up to a daṇḍa '|' or a
closing '|| n ||') that scans is wrapped in <l>, and the half-verses of one verse
that stand together in one container (the <ab> itself, or one <seg>) in <lg>.
A verse broken by commentary or by a <seg> boundary gets <lg part="I">,
part="M", part="F" (TEI's way of marking an incomplete verse). Prose, and prose
headings in front of a verse ("atha …cūrṇam -"), stay outside <lg>. Nothing but
<lg>/<l> tags is added; the script checks that.

Metres recognised (metre.py): anuṣṭubh (pathyā and vipulās), the usual
syllable-counted metres (triṣṭubh/jagatī families, vasantatilakā, mālinī,
śārdūlavikrīḍita…), ardhasama metres, āryā (by morae), and repeated pāda patterns.
A half that only nearly scans is accepted when another half of the same verse
scans properly.
"""
import argparse, collections, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metre import classify_half, weights

TOK = re.compile(r'(<note\b[^>]*>.*?</note>|<note\b[^>]*/>|<label\b[^>]*>.*?</label>|<[^>]+>)', re.S)
DANDA = re.compile(r'\|+(?:\s*[0-9०-९][0-9०-९\-–.,\s]*\|*)?')
# prose marks: a dash between words, or a heading/colophon word at the start
HEADING = re.compile(r'(?:\s[-–—]+|[-–—]{2}|:-)\s*[^\W\d_]|^\W*(atha|iti|idānīm|idānīṃ|tatra|sa yathā|kecit)\b')


def STRICT_OK(m):
    return m is not None and m not in ('loose', 'āryā1', 'āryā2') and not m.startswith('pāda')


class Run:
    """a stretch of text in one container: (line, run number)"""
    def __init__(self, line, rid):
        self.line, self.rid = line, rid
        self.chars = []          # (raw position, char) of text outside notes


def runs_of_line(s, line):
    """split an <ab type="mula"> line into runs of text separated by <seg> tags"""
    runs, rid, cur = [], 0, None
    pos = 0
    for part in TOK.split(s):
        if part == '':
            continue
        if part.startswith('<'):
            name = re.match(r'</?([A-Za-z]+)', part).group(1)
            if name in ('note', 'label'):
                if cur is not None:
                    cur.chars.append((pos, '\x00'))          # a note: atomic, no letters
            elif name in ('seg', 'ab'):
                cur = None
                rid += 1
            # other tags (label, hi…) stay inside the run
            pos += len(part)
            continue
        if cur is None:
            cur = Run(line, rid)
            runs.append(cur)
        for k, ch in enumerate(part):
            cur.chars.append((pos + k, ch))
        pos += len(part)
    return runs


class Seg:
    """a daṇḍa-delimited segment of a run"""
    def __init__(self, run, a, b, end_kind):
        self.run, self.a, self.b = run, a, b        # indices into run.chars, [a, b)
        self.end = end_kind                         # 'verse' (|| or a number), 'half' (|), None
        self.ls = []                                # [(a, b)] verse lines found in it
        self.metres = []

    def text(self, a=None, b=None):
        a = self.a if a is None else a
        b = self.b if b is None else b
        return ''.join(c for _, c in self.run.chars[a:b] if c != '\x00')


def segments(run):
    txt = ''.join(c for _, c in run.chars)
    out, start = [], 0
    for m in DANDA.finditer(txt):
        a = start
        while a < m.start() and txt[a].isspace():
            a += 1
        kind = 'verse' if (len(m.group(0).strip('| \t')) or m.group(0).count('|') >= 2) else 'half'
        if a < m.start():
            out.append(Seg(run, a, m.end(), kind))
        start = m.end()
    a = start
    while a < len(txt) and txt[a].isspace():
        a += 1
    if a < len(txt) and re.search(r'[^\W\d_]', txt[a:]):
        b = len(txt)
        while b > a and txt[b - 1].isspace():
            b -= 1
        out.append(Seg(run, a, b, None))
    return out


def boundaries(seg):
    """possible starts of a verse after a prose heading: after a dash/colon, then any space"""
    txt = ''.join(c for _, c in seg.run.chars[seg.a:seg.b])
    good, other = [], []
    for m in re.finditer(r'(?:\s[-–—]+\s*|--\s*|\s*:-\s*|[-–—]\s+)|\s+', txt):
        k = seg.a + m.end()
        (good if re.search(r'[-–—:]', m.group(0)) else other).append(k)
    return good, other


def split2(seg, start):
    """two half-verses in seg from `start` on, split at a space"""
    good, other = boundaries(seg)
    for k in other:
        if k <= start:
            continue
        m1, _ = classify_half(seg.text(start, k))
        m2, _ = classify_half(seg.text(k, seg.b))
        if (STRICT_OK(m1) and STRICT_OK(m2) and m1.split('/')[0] == m2.split('/')[0]) or {m1, m2} == {'anuṣṭubh', 'loose'}:
            k2 = k
            while k2 > start and seg.run.chars[k2 - 1][1].isspace():
                k2 -= 1
            return [(start, k2), (k, seg.b)], [m1, m2]
    return None


def analyse(seg):
    full = seg.text()
    m, w = classify_half(full)
    if m:
        seg.ls, seg.metres = [(seg.a, seg.b)], [m]
        if STRICT_OK(m) and m != 'samavṛtta?':
            return
    n = len(w)
    # a whole verse with no daṇḍa between the halves (possibly after a heading)
    if n >= 32:
        good, other = boundaries(seg)
        for start in [seg.a] + good:
            r = split2(seg, start)
            if r:
                seg.ls, seg.metres = r
                return
    # prose heading + one half-verse
    if n > 16:
        good, other = boundaries(seg)
        weak = None
        for k in good + other:
            m1, w1 = classify_half(seg.text(k, seg.b))
            if STRICT_OK(m1) and len(w1) >= 16:
                seg.ls, seg.metres = [(k, seg.b)], [m1]
                return
            if weak is None and m1 in ('loose', 'āryā1') and len(w1) >= 16:
                weak = (k, m1)
        if weak and (not seg.ls or HEADING.search(full)):
            seg.ls, seg.metres = [(weak[0], seg.b)], [weak[1]]
            return
    if seg.ls and not HEADING.search(full):
        return          # a weak reading (or an unlisted samavṛtta); tag() decides
    seg.ls, seg.metres = [], []


def tag(lines, report, commentary=False):
    stats = collections.Counter()
    ins = collections.defaultdict(list)          # line -> [(pos, order, text)]
    prose = []
    # mūla stream by chapter
    chapters, cur = [], []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith(('<div', '</div', '<head')):
            if cur:
                chapters.append(cur); cur = []
            continue
        if s.startswith('<ab') and re.match(r'<ab\b[^>]*type="mula"', s):
            cur.append(i)
    if cur:
        chapters.append(cur)

    for ch in chapters:
        segs = []
        for i in ch:
            for r in runs_of_line(lines[i], i):
                for sg in segments(r):
                    analyse(sg)
                    segs.append(sg)
        # weak readings are accepted next to a half-verse that scans properly
        strict_at = [any(STRICT_OK(m) or m in ('pāda-odd', 'pāda-even') for m in sg.metres) for sg in segs]
        def near(i, d=2):
            return any(strict_at[j] for j in range(max(0, i - d), min(len(segs), i + d + 1)) if j != i)
        keep = []
        for i, sg in enumerate(segs):
            ok = []
            for (a, b), m in zip(sg.ls, sg.metres):
                if STRICT_OK(m):
                    ok.append((a, b, m, ''))
                elif m == 'loose' and near(i):
                    ok.append((a, b, 'anuṣṭubh (irregular)', ''))
                elif m in ('āryā1', 'āryā2'):
                    other = 'āryā2' if m == 'āryā1' else 'āryā1'
                    nb = [segs[j] for j in (i - 1, i + 1) if 0 <= j < len(segs)]
                    if any(other in x.metres for x in nb):
                        ok.append((a, b, 'āryā', ''))
                elif m.startswith('pāda') and near(i):
                    nb = [segs[j] for j in (i - 1, i + 1) if 0 <= j < len(segs)]
                    if m != 'pāda?' or any(x.metres and x.metres[0].startswith('pāda') for x in nb):
                        ok.append((a, b, 'anuṣṭubh pāda', ' part="%s"' % ('I' if sg.end is None else 'F')))
            if not ok and sg.end is not None and near(i, 1):
                # an unscanned half between halves that scan: accept if it is
                # about the length of a śloka half
                nsyl = len(weights(sg.text()))
                numbered = sg.end == 'verse'
                if (nsyl == 16 or (numbered and 14 <= nsyl <= 18)) and not HEADING.search(sg.text()):
                    ok.append((sg.a, sg.b, 'anuṣṭubh (irregular)', ''))
            if not ok:
                prose.append(sg)
            keep.append((sg, ok))
        # verses: runs of segments up to a verse end
        verses, v = [], []
        for sg, ok in keep:
            v.append((sg, ok))
            if sg.end == 'verse':
                verses.append(v); v = []
        if v:
            verses.append(v)
        for keep in verses:
            # group lines into <lg> by run
            groups = []
            for sg, ok in keep:
                for a, b, m, lpart in ok:
                    stats[m] += 1
                    if groups and groups[-1][0] is sg.run and all(
                            c.isspace() or c == '\x00' for _, c in sg.run.chars[groups[-1][1][-1][1]:a]):
                        groups[-1][1].append((a, b, lpart))
                    else:
                        groups.append([sg.run, [(a, b, lpart)]])
            for gi, (run, ls) in enumerate(groups):
                part = ''
                if len(groups) > 1:
                    part = ' part="%s"' % ('I' if gi == 0 else 'F' if gi == len(groups) - 1 else 'M')
                L = run.line
                pos = lambda k: run.chars[k][0]
                end = lambda k: run.chars[k - 1][0] + 1
                ins[L].append((pos(ls[0][0]), 1, '<lg%s>' % part))
                for a, b, lpart in ls:
                    ins[L].append((pos(a), 2, '<l%s>' % lpart))
                    ins[L].append((end(b), -2, '</l>'))
                ins[L].append((end(ls[-1][1]), -1, '</lg>'))
                stats['lg'] += 1
                stats['lg part'] += bool(part)
    if commentary:
        # verses quoted or composed in the commentaries: only where at least two
        # consecutive half-verses scan strictly, side by side in one run
        for i, ln in enumerate(lines):
            if not re.match(r'\s*<ab\b[^>]*type="commentary"', ln):
                continue
            for r in runs_of_line(ln, i):
                group = []
                def flush():
                    if len(group) >= 2:
                        pos = lambda k: r.chars[k][0]
                        end = lambda k: r.chars[k - 1][0] + 1
                        ins[i].append((pos(group[0][0]), 1, '<lg>'))
                        for a, b in group:
                            ins[i].append((pos(a), 2, '<l>'))
                            ins[i].append((end(b), -2, '</l>'))
                        ins[i].append((end(group[-1][1]), -1, '</lg>'))
                        stats['commentary lg'] += 1
                        stats['commentary l'] += len(group)
                    group.clear()
                for sg in segments(r):
                    analyse(sg)
                    strict = [(a, b) for (a, b), m in zip(sg.ls, sg.metres) if STRICT_OK(m)]
                    if len(strict) != len(sg.ls) or not strict:
                        flush(); continue
                    if group and not all(c.isspace() or c == '\x00' for _, c in r.chars[group[-1][1]:strict[0][0]]):
                        flush()
                    group.extend(strict)
                    if sg.end == 'verse':
                        flush()
                flush()
    out = list(lines)
    for L, items in ins.items():
        s = out[L]
        # at one position: closing tags first (</l> then </lg>), then <lg>, then <l>
        for p, o, t in sorted(items, key=lambda x: (x[0], x[1]), reverse=True):
            s = s[:p] + t + s[p:]
        out[L] = s
    if report:
        with open(report, 'w', encoding='utf8') as f:
            f.write('# root-text segments left as prose (line: text)\n')
            for sg in prose:
                f.write('%d: %s\n' % (sg.run.line + 1, sg.text()))
    return out, stats, prose


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp')
    ap.add_argument('out')
    ap.add_argument('--report')
    ap.add_argument('--commentary', action='store_true',
                    help='also tag verses in the commentaries where two or more consecutive halves scan strictly')
    a = ap.parse_args()
    src = open(a.inp, encoding='utf8').read()
    if re.search(r'<lg\b', src.split('<body>', 1)[-1]):
        raise SystemExit('the text already has <lg> tags; run verse.py on the untagged file')
    lines = src.split('\n')
    out, stats, prose = tag(lines, a.report, a.commentary)
    res = '\n'.join(out)
    # check: removing the new tags gives the input back
    back = re.sub(r'</?lg\b[^>]*>|</?l\b[^>]*>', '', res)
    assert back == src, 'verse tagging changed the text'
    open(a.out, 'w', encoding='utf8').write(res)
    for k, v in stats.most_common():
        print('%6d  %s' % (v, k))
    print('%6d  root-text segments left as prose' % len(prose))


if __name__ == '__main__':
    main()
