#!/usr/bin/env python3
"""Run the whole word-spacing procedure for one e-text, step by step.

The spacing itself is done by agents (one per piece, see SESSION.md); every other
step is here. Run from the repository root:

  pipeline.py prepare TEI WORK --title "…"   cut the TEI into pieces, estimate the cost
  pipeline.py prompt  WORK NNN               the prompt for the agent of piece NNN
  pipeline.py status  WORK                   which pieces are done, half done, not started
  pipeline.py review  WORK                   assemble, avagraha pass, consistency report;
                                             drafts WORK/rules.txt for you to check, and
                                             WORK/sweep.txt (missed junctions) to pick from
  pipeline.py sample  WORK [N]               N random passages of the spaced text to proofread
  pipeline.py finish  WORK [--rng tei_all.rng]
                                             apply WORK/rules.txt, tag verses, verify against
                                             the original, write the TEI file with notes in its
                                             header, and the -flagged.txt / -prose.txt files
  pipeline.py prbody  WORK                   a pull-request description (under GitHub's limit)

WORK is a scratch directory outside the repository. Everything the steps need is
kept there (orig.xml = the TEI file as it was before, stats.json = the numbers).
"""
import argparse, collections, glob, json, os, random, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
TOKENS_PER_PIECE = 115_000      # measured: Mādhava 54 pieces ≈ 6 M, Caraka 125 pieces ≈ 14 M

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sub = ap.add_subparsers(dest='cmd', required=True)
p = sub.add_parser('prepare'); p.add_argument('tei'); p.add_argument('work'); p.add_argument('--title', required=True)
p.add_argument('--target', type=int, default=28000)
p = sub.add_parser('prompt'); p.add_argument('work'); p.add_argument('nums', nargs='+')
p = sub.add_parser('status'); p.add_argument('work')
p = sub.add_parser('review'); p.add_argument('work')
p = sub.add_parser('sample'); p.add_argument('work'); p.add_argument('n', nargs='?', type=int, default=40)
p = sub.add_parser('finish'); p.add_argument('work'); p.add_argument('--rng')
p = sub.add_parser('prbody'); p.add_argument('work')
a = ap.parse_args()
W = os.path.abspath(a.work)


def run(*args, capture=True, check=True):
    r = subprocess.run([PY, *map(str, args)], capture_output=capture, text=True)
    if r.returncode and check:
        sys.exit('%s failed:\n%s%s' % (' '.join(map(str, args)), r.stdout, r.stderr))
    return r.stdout


def tool(name):
    return os.path.join(HERE, name)


def load_stats():
    f = os.path.join(W, 'stats.json')
    return json.load(open(f, encoding='utf8')) if os.path.exists(f) else {}


def save_stats(**kw):
    s = load_stats(); s.update(kw)
    json.dump(s, open(os.path.join(W, 'stats.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)


def pieces():
    return sorted(f[:-4] for f in os.listdir(os.path.join(W, 'in')) if f.endswith('.xml'))


def body_text(xml):
    b = xml[xml.index('<body'):]
    b = re.sub(r'<note\b.*?</note>|<note\b[^>]*/>', '', b, flags=re.S)
    return re.sub(r'<[^>]+>', ' ', b)


TOKEN = re.compile(r"[a-zāīūṛṝḷṃḥṅñṭḍṇśṣ']+")

# ---------------------------------------------------------------- prepare
if a.cmd == 'prepare':
    os.makedirs(W, exist_ok=True)
    out = run(tool('prepare.py'), a.tei, W, '--work-title', a.title, '--target', a.target)
    open(os.path.join(W, 'pieces.txt'), 'w', encoding='utf8').write(out)
    with open(a.tei, encoding='utf8') as f:
        open(os.path.join(W, 'orig.xml'), 'w', encoding='utf8').write(f.read())
    n = len(pieces())
    chars = sum(int(l.split()[-1]) for l in out.splitlines() if re.match(r'\d{3} lines ', l))
    save_stats(tei=os.path.abspath(a.tei), title=a.title, pieces=n)
    print(out.splitlines()[-1])
    print('text to space: %d characters in %d pieces' % (chars, n))
    print('estimated agent work: about %.0f million tokens (%d pieces × ~%dk); with 12 agents at a time'
          % (n * TOKENS_PER_PIECE / 1e6, n, TOKENS_PER_PIECE // 1000))
    print('running time about %.1f hours at the measured rate (Śārṅgadhara: 56 pieces in about 2 hours),'
          ' longer if the usage limit interrupts it.' % (n * 2.1 / 60))
    print('TELL THE USER THIS ESTIMATE AND ASK BEFORE LAUNCHING THE AGENTS.')
    print('INSTRUCTIONS for the agents:', os.path.join(W, 'INSTRUCTIONS.md'))

# ---------------------------------------------------------------- prompt
elif a.cmd == 'prompt':
    title = load_stats().get('title', 'the text')
    for n in a.nums:
        n = '%03d' % int(n)
        print(f'Read {W}/INSTRUCTIONS.md and carry it out for piece {n} (in/{n}.xml → out/{n}.xml '
              f'in that work directory). This is a Sanskrit word-spacing task on a TEI/XML file of '
              f'{title}. Follow the rules exactly; read every line and decide each junction (no blind '
              f'global rules); run check.py until it passes (letters-ok xml-ok tags-ok lines-ok). Write '
              f'your report to reports/{n}.txt as the instructions say, touch no file other than '
              f'out/{n}.xml, reports/{n}.txt and your own helper scripts under scripts/ (with {n} in '
              f'their names; do not copy or run other agents\' scripts), and reply with the single line '
              f'the instructions ask for.')
        print()

# ---------------------------------------------------------------- status
elif a.cmd == 'status':
    out = run(tool('check.py'), W, 'all', check=False)
    res = {l.split()[0]: l for l in out.splitlines() if l.strip()}
    done, noreport, bad, todo = [], [], [], []
    for n in pieces():
        line = res.get(n, '')
        if 'MISSING' in line or not os.path.exists(os.path.join(W, 'out', n + '.xml')):
            todo.append(n)
        elif not all(k in line for k in ('letters-ok', 'xml-ok', 'tags-ok', 'lines-ok')):
            bad.append(n)
        elif not os.path.exists(os.path.join(W, 'reports', n + '.txt')):
            noreport.append(n)
        else:
            done.append(n)
    print('done (passes, report written): %d' % len(done))
    print('output passes, no report yet:  %d  %s' % (len(noreport), ' '.join(noreport)))
    print('output fails check:            %d  %s' % (len(bad), ' '.join(bad)))
    print('no output yet:                 %d  %s' % (len(todo), ' '.join(todo)))
    print('(pieces still running are among the last two groups)')
    sp = sum(int(re.search(r'spaces-added (\d+)', res[n]).group(1)) for n in done + noreport
             if re.search(r'spaces-added (\d+)', res.get(n, '')))
    print('spaces added so far:', sp)

# ---------------------------------------------------------------- review
elif a.cmd == 'review':
    out = run(tool('check.py'), W, 'all')
    lines = [l for l in out.splitlines() if l.strip()]
    badl = [l for l in lines if not all(k in l for k in ('letters-ok', 'xml-ok', 'tags-ok', 'lines-ok'))]
    if badl:
        sys.exit('not all pieces pass:\n' + '\n'.join(badl))
    agent_spaces = sum(int(re.search(r'spaces-added (\d+)', l).group(1)) for l in lines)
    run(tool('assemble.py'), W, os.path.join(W, 'spaced.xml'))
    av = run(tool('avagraha.py'), os.path.join(W, 'spaced.xml'), os.path.join(W, 'spaced2.xml'))
    avn = int(re.search(r'(\d+) spaces added', av).group(1))
    s2 = os.path.join(W, 'spaced2.xml'); orig = os.path.join(W, 'orig.xml')
    cons = run(tool('consistency.py'), s2, '--orig', orig, '--top', 1000)
    part = run(tool('consistency.py'), s2, '--particles', '--top', 1000)
    open(os.path.join(W, 'cons.txt'), 'w', encoding='utf8').write(cons)
    open(os.path.join(W, 'part.txt'), 'w', encoding='utf8').write(part)
    save_stats(agent_spaces=agent_spaces, avagraha_spaces=avn)

    # draft rules: split forms that are particles/connectives and split more often than not
    P2 = {'ca', 'tu', 'eva', 'api', 'iti', 'ity', 'hi', 'vā', 'āha', 'arthaḥ', 'arthaṃ',
          'uktaṃ', 'uktam', 'uktaḥ', 'uktā', 'ucyate', 'ucyante', 'atra', 'anena', 'anenāpi', 'iha', 'te',
          'yaḥ', 'tadā', 'ādau', 'ante', 'eṣa', 'ete', 'tena', 'yathā', 'yathetyādi', 'tarhi', 'tarhy', 'veti'}
    P1 = {'ity', 'tv', 'kiṃ', 'yady', 'kin', 'kiñ', 'yas', 'yac', 'tataś', 'evam'}
    PRON = {'tad', 'tat', 'yad', 'yat', 'etad', 'etat', 'tal', 'tac', 'tan'}
    rows = []
    for ln in cons.splitlines()[1:]:
        m = re.match(r'(\S+)\s+joined×(\d+)\s+split×(\d+)\s+\((.+?)×\d+\)', ln)
        if m:
            rows.append((m.group(1), m.group(4), int(m.group(2)), int(m.group(3))))
    for ln in part.splitlines():
        m = re.match(r'(\S+)\s+joined×(\d+)\s+(\S+ \S+)\s+split×(\d+)', ln)
        if m and m.group(1) not in [r[0] for r in rows]:
            rows.append((m.group(1), m.group(3), int(m.group(2)), int(m.group(4))))
    keep, left = [], []
    for j, sp, nj, ns in rows:
        if '|' in j or sp.count(' ') != 1:
            left.append((j, sp, nj, ns)); continue
        x, y = sp.split(' ')
        ok = (y in P2 or x in P1)
        if x in PRON and y not in ('yathā', 'yathetyādi', 'āha', 'uktaṃ', 'uktam', 'eva', 'ca', 'api'):
            ok = False
        if x == 'iti' and y.startswith('pad'):
            ok = False
        if x in ('punar', 'prāg', 'prāk', 'pṛthag', 'pṛthak', 'samyag', 'samyak'):
            ok = False
        if ns < nj and x not in P1 and y not in ('ca', 'tu', 'eva', 'api', 'iti', 'hi', 'vā'):
            ok = False
        (keep if ok else left).append((j, sp, nj, ns))
    with open(os.path.join(W, 'rules.txt'), 'w', encoding='utf8') as f:
        f.write('# consistency rules for fix.py (old => new). Drafted by pipeline.py review:\n'
                '# check every line; delete what is wrong; add good lines from sweep.txt and\n'
                '# from undecided.txt; a join rule (a b => ab) may only remove an ADDED space.\n')
        for j, sp, nj, ns in keep:
            f.write('%s => %s\n' % (j, sp))
    with open(os.path.join(W, 'undecided.txt'), 'w', encoding='utf8') as f:
        f.write('# joined/split pairs not ruled on (joined×N split×M); context decides (rule 5) or the editor.\n')
        for j, sp, nj, ns in left:
            f.write('%-40s %-44s joined×%d split×%d\n' % (j, sp, nj, ns))

    # sweep: case/verb endings run into the next word, as candidates for review
    txt = open(s2, encoding='utf8').read()
    C = collections.Counter(TOKEN.findall(body_text(txt)))
    END_V = ('ānām', 'āṇām', 'īnām', 'īṇām', 'ūnām', 'ūṇām', 'eṣv', 'iṣv', 'uṣv', 'āsv', 'anty', 'ety', 'aty')
    END_C = ('air', 'ais', 'aiś', 'bhir', 'bhis', 'bhiś', 'ayor', 'yor')
    END_S = ('ād', 'āt', 'ān', 'ed', 'et', 'en')          # ablative/optative: need strong evidence
    BAD_A = re.compile(r'(sthair|dhair|vaiś|abhis|abhiś|praty|mahān|siddhān|samān|yathāsv|^danty|^jīvanty)$')
    VOW = 'aāiīuūṛeo'
    cand = []
    for t, n in C.items():
        if len(t) < 9 or "'" in t:
            continue
        for k in range(4, len(t) - 2):
            A, B = t[:k], t[k:]
            if BAD_A.search(A) or len(B) < 3 or B.startswith(('ādi', 'ādau', 'ādy')):
                continue
            if A.endswith(('ety', 'aty')) and C[A] < 2:     # -etyādi lemmata, ati- compounds
                continue
            if A.endswith(END_V) and B[0] in VOW and C[B] >= 2:
                pass
            elif A.endswith(END_C) and B[0] not in VOW + 'kcṭtpśṣs' and C[B] >= 2:
                pass
            elif A.endswith(('ais', 'bhis')) and B[0] == 't' and C[B] >= 2:      # -ais tathā
                pass
            elif A.endswith(('aiś', 'bhiś')) and B[0] in 'cś' and C[B] >= 2:     # -aiś ca
                pass
            elif A.endswith(END_C) and A.endswith(('air', 'bhir')) and B[0] in VOW and C[B] >= 2:
                pass
            elif A.endswith(END_S) and C[A] >= 8 and C[B] >= 8:
                pass
            else:
                continue
            cand.append((t, A, B, n, C[A], C[B]))
    with open(os.path.join(W, 'sweep.txt'), 'w', encoding='utf8') as f:
        f.write('# candidate missed junctions (token => split  ×count [count of left part, right part]).\n'
                '# Many are false (compounds, lexical words): copy only the real ones into rules.txt.\n')
        for t, A, B, n, ca, cb in sorted(cand):
            f.write('%s => %s %s   ×%d [%d,%d]\n' % (t, A, B, n, ca, cb))
    print('pieces ok; agent spaces %d; avagraha spaces %d' % (agent_spaces, avn))
    print(cons.splitlines()[0] if cons else '')
    print('drafted %d rules in rules.txt; %d pairs in undecided.txt; %d sweep candidates in sweep.txt'
          % (len(keep), len(left), len(cand)))
    print('NEXT: check rules.txt line by line, add the real hits from sweep.txt, then run finish.')

# ---------------------------------------------------------------- sample
elif a.cmd == 'sample':
    f = os.path.join(W, 'final.xml') if os.path.exists(os.path.join(W, 'final.xml')) else os.path.join(W, 'spaced2.xml')
    L = [l for l in open(f, encoding='utf8').read().split('\n') if '<ab type=' in l]
    random.seed(len(L))
    for l in random.sample(L, min(a.n, len(L))):
        t = re.sub(r'<note\b.*?</note>|<note\b[^>]*/>', '', l)
        t = re.sub(r'<[^>]+>', '', t).strip()
        i = random.randrange(max(1, len(t) - 300))
        print(t[i:i + 300]); print()

# ---------------------------------------------------------------- finish
elif a.cmd == 'finish':
    st = load_stats()
    tei, orig = st['tei'], os.path.join(W, 'orig.xml')
    s2, s3, fin = (os.path.join(W, x) for x in ('spaced2.xml', 'spaced3.xml', 'final.xml'))
    rules = os.path.join(W, 'rules.txt')
    fx = run(tool('fix.py'), s2, s3, rules)
    fixn = int(re.search(r'(\d+) changes', fx).group(1))
    nrules = sum(1 for l in open(rules, encoding='utf8') if '=>' in l.split('#')[0])
    vs = run(tool('verse.py'), s3, fin, '--commentary', '--report', os.path.join(W, 'prose.txt'))
    vargs = [tool('verify.py'), orig, fin] + (['--rng', a.rng] if a.rng else [])
    vr = run(*vargs)
    print(vr)
    if 'letters-ok' not in vr or 'tags-ok' not in vr:
        sys.exit('verify.py did not pass; nothing written to the repository')
    total = int(re.search(r'letters-ok: (\d+) spaces added', vr).group(1))

    s = open(fin, encoding='utf8').read()
    if 'Word spaces have been added' in s[:s.index('<text')]:
        sys.exit('the header already has a spacing note')
    ncomm = len(set(re.findall(r'<ab type="commentary"[^>]*subtype="([^"]+)"', s)))
    comm = 'the commentaries' if ncomm > 1 else 'the commentary'
    hasnotes = '<note' in s[s.index('<body'):]
    n0 = s.count('\n')
    m = re.search(r'\n([ \t]*)</editorialDecl>', s)
    ind = m.group(1) + '  '
    ed = (f'\n{ind}<p>Word spaces have been added (2026-11) between the words that the source runs\n'
          f'{ind}  together, in the root text and {comm}{" but not in the notes" if hasnotes else ""}: sandhi forms\n'
          f'{ind}  are kept as they are and only a space is inserted (tasminn eva, tac chāstram, ity\n'
          f'{ind}  eke); fused vowels and compounds are not divided; a space precedes an avagraha\n'
          f'{ind}  after e or o (te \'pi). No letter, punctuation mark or element of the source was\n'
          f'{ind}  changed.</p>\n'
          f'{ind}<p>Verse in the root text is marked by metre: each half-verse (up to a daṇḍa or the\n'
          f'{ind}  verse number) is an l, the half-verses of a verse that stand together an lg. Where\n'
          f'{ind}  commentary interrupts a verse, its parts are lg[@part=\'I\'], [@part=\'M\'] and\n'
          f'{ind}  [@part=\'F\'] (a single pāda split off: l[@part]). Prose, headings and colophons\n'
          f'{ind}  stay outside lg. In {comm}, quoted or composed verses are marked as lg where\n'
          f'{ind}  two or more consecutive half-verses scan.</p>')
    s = s[:m.start()] + ed + s[m.start():]
    m = re.search(r'<revisionDesc>\n([ \t]*)', s)
    if m:
        import datetime
        s = s[:m.end()] + '<change when="%s">Word spacing added to root text and %s, and verse marked as lg/l by metre (tools/spacing/).</change>\n%s' % (
            datetime.date.today().isoformat(), comm.replace('the ', ''), m.group(1)) + s[m.end():]
    else:
        print('WARNING: no <revisionDesc>; add a <change> by hand')
    shift = s.count('\n') - n0
    open(tei, 'w', encoding='utf8').write(s)

    base = os.path.splitext(tei)[0].replace('-full', '')
    name = os.path.basename(base)
    # prose file
    out = ['# Root-text segments left as prose by tools/spacing/verse.py (line in %s: text)' % os.path.basename(tei)]
    for ln in open(os.path.join(W, 'prose.txt'), encoding='utf8').read().split('\n')[1:]:
        mm = re.match(r'(\d+): (.*)', ln)
        if mm:
            out.append('%d: %s' % (int(mm.group(1)) + shift, mm.group(2)))
    open(base + '-prose.txt', 'w', encoding='utf8').write('\n'.join(out) + '\n')
    nprose = len(out) - 1

    # counts
    lg = collections.Counter(); l_ = collections.Counter()
    for mm in re.finditer(r'<ab type="(mula|commentary)".*?</ab>', s, flags=re.S):
        lg[mm.group(1)] += len(re.findall(r'<lg\b', mm.group(0)))
        l_[mm.group(1)] += len(re.findall(r'<l\b', mm.group(0)))
    nnotes = len(re.findall(r'<note\b', s[s.index('<body'):]))
    T = body_text(s)
    def cnt(rx):
        return len(re.findall(rx, T))
    policy = {k: cnt(v) for k, v in {
        'kiñ ca': r'\bkiñ ca\b', 'kiṃ vā': r'\bkiṃ vā\b', 'ityādi / ityantena (joined; should be ity ādi, ity antena)': r'\bity(?:ād[iy]|ant)',
        'kin tarhi': r'\bkin tarhi', 'itipad- (joined)': r'\bitipad', 'iti pad- (split)': r'\biti pad',
        'punarukt- (joined)': r'\bpunarukt', 'punar ukt- (split)': r'\bpunar ukt',
        'yatkiñcit (joined)': r'\byatkiñci', 'yat kiñcit (split)': r'\byat kiñci'}.items()}
    save_stats(fix_rules=nrules, fix_changes=fixn, total_spaces=total, prose=nprose, notes=nnotes,
               lg_root=lg['mula'], l_root=l_['mula'], lg_comm=lg['commentary'], l_comm=l_['commentary'],
               lg_part=len(re.findall(r'<lg part=', s)), l_part=len(re.findall(r'<l part=', s)),
               policy=policy, flagged_file=base + '-flagged.txt', prose_file=base + '-prose.txt')

    # flagged file
    spots = []
    for f in sorted(glob.glob(os.path.join(W, 'reports', '*.txt'))):
        for l in open(f, encoding='utf8').read().split('\n'):
            l = l.strip().lstrip('-•* ').strip()
            if re.match(r'\d{3} l\.', l):
                spots.append(l)
    und = [l for l in open(os.path.join(W, 'undecided.txt'), encoding='utf8').read().split('\n')[1:] if l.strip()]
    rl = [l for l in open(rules, encoding='utf8').read().split('\n') if '=>' in l.split('#')[0]]
    pol = '\n'.join('- %s: %d' % kv for kv in policy.items())
    head = f'''# {st['title']}: word spacing and verse tagging — spots to check

Word spacing was added in 2026-11 by {st['pieces']} agents, one per piece of the TEI file
(tools/spacing/, see its README). Each agent reported up to five places it was
unsure of; they are listed below as "NNN l.LINE", where NNN is the piece and
LINE the line within that piece. Use the form quoted to find the place in
{os.path.basename(tei)} (search for it; after the avagraha pass te'pi is te 'pi).

Decisions taken across the whole text (as for the Śārṅgadharasaṃhitā, the
Mādhavanidāna and the Carakasaṃhitā; see tools/spacing/INSTRUCTIONS.md):
- the notes are not spaced.
- avagraha: a space before ' after e/o everywhere (te 'pi); ā' (tathā'pi) stays joined.
- particles split everywhere (tathā ca, yad vā, na hi, yady api, ity arthaḥ, yad
  uktaṃ, tad yathā, kiñ ca, kiṃ vā, ity ādi and its cases, ity antena …); joined:
  tadanu, tadanantaraṃ, kintu, parantu, athavā, itastataḥ.
- a doubled consonant at a word junction written once: left joined; typos are left
  uncorrected and usually joined.
- commentary lemmata: the space goes after ity; a fused vowel keeps the lemma joined
  to it (yathety ādi), a consonant junction is split (kaṭv ity ādi).

Policy questions for the editor (counts in this text):
{pol}

Joined/split pairs left as the agents had them (context decides, or the editor):
''' + '\n'.join('  ' + u for u in und) + '''

Root-text segments the verse tagger left as prose are listed in
''' + os.path.basename(base) + '''-prose.txt.

## Uncertain spots reported by the agents

'''
    open(base + '-flagged.txt', 'w', encoding='utf8').write(
        head + '\n'.join(spots) + '\n\n## Consistency fixes applied (old => new; whole tokens, outside notes)\n\n'
        + '\n'.join(rl) + '\n')
    print(vs.strip().splitlines()[-1])
    print('wrote', tei, base + '-flagged.txt', base + '-prose.txt')
    print('spaces %d (agents %d, avagraha %d, fixes %d); root lg/l %d/%d; commentary lg/l %d/%d; prose %d; flagged %d'
          % (total, st.get('agent_spaces', 0), st.get('avagraha_spaces', 0), fixn, lg['mula'], l_['mula'],
             lg['commentary'], l_['commentary'], nprose, len(spots)))
    print('NEXT: read the flagged file header and edit the policy section if needed; proofread with '
          '"sample"; build the site; then prbody.')

# ---------------------------------------------------------------- prbody
elif a.cmd == 'prbody':
    st = load_stats()
    fl = open(st['flagged_file'], encoding='utf8').read()
    i = fl.index('Policy questions for the editor'); j = fl.index('Root-text segments the verse tagger')
    policy = fl[i:j].strip()
    spots = fl[fl.index('## Uncertain spots reported by the agents'):fl.index('## Consistency fixes applied')].split('\n', 1)[1].strip().split('\n')
    fname = os.path.relpath(st['flagged_file'], os.path.dirname(os.path.dirname(st['tei'])))
    pname = os.path.relpath(st['prose_file'], os.path.dirname(os.path.dirname(st['tei'])))
    tname = os.path.relpath(st['tei'], os.path.dirname(os.path.dirname(st['tei'])))
    body = f'''Word spacing and verse tagging for {st['title']} (`{tname}`), done the same way as the earlier texts, following `tools/spacing/README.md`, `INSTRUCTIONS.md` and `SESSION.md`.

## Numbers

| | |
|---|---|
| Pieces (one agent each) | {st['pieces']} |
| Spaces inserted by the agents | {st['agent_spaces']:,} |
| Spaces inserted before an avagraha (`te 'pi`) | {st['avagraha_spaces']:,} |
| Consistency fixes (`fix.py`) | {st['fix_changes']:,} changes from {st['fix_rules']} rules |
| **Spaces inserted in all** | **{st['total_spaces']:,}** |
| Root text: `<lg>` / `<l>` | {st['lg_root']:,} / {st['l_root']:,} |
| of which `<lg part="…">` / `<l part="…">` | {st['lg_part']:,} / {st['l_part']:,} |
| Commentary: `<lg>` / `<l>` | {st['lg_comm']:,} / {st['l_comm']:,} |
| Notes (unspaced, unchanged) | {st['notes']:,} |
| Root-text segments left as prose | {st['prose']:,} (listed in `{pname}`) |

## Checks

- `check.py`: all {st['pieces']} pieces `letters-ok xml-ok tags-ok lines-ok`.
- `verify.py` against the file on main: letters, tags, notes and xml:ids unchanged, well-formed, valid.
- `consistency.py`: clear cases fixed by rule (listed at the end of `{fname}`), the others listed there for review.
- Proofread: PROOFREADING RESULT — FILL IN.
- Site built locally; chapters looked at: FILL IN.

## {policy}

## Flagged items ({len(spots)} lines, as reported by the agents)

`NNN l.LINE` = piece and line within the piece; search for the quoted form in the TEI file.
'''
    tail = '\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n'
    budget = 64000 - len(body) - len(tail) - 300
    shown, n = [], 0
    for l in spots:
        if n + len(l) + 1 > budget:
            break
        shown.append(l); n += len(l) + 1
    note = '' if len(shown) == len(spots) else \
        f'\nThe first {len(shown)} of {len(spots)} are shown (GitHub limits the length of a description); the full list is in `{fname}`.\n'
    body += note + '\n<details>\n<summary>Show the list</summary>\n\n```\n' + '\n'.join(shown) + '\n```\n\n</details>\n' + tail
    out = os.path.join(W, 'pr.md')
    open(out, 'w', encoding='utf8').write(body)
    print('wrote', out, len(body), 'characters; fill in the two FILL IN lines before use')
