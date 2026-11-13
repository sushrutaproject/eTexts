"""Syllable weights and metre tests for IAST Sanskrit (used by verse.py).

weights("dharmārthakāmamokṣāṇāṃ") -> "GGGGGGGG"-style string of L (light) / G (heavy).
Spaces, punctuation, avagraha and digits are ignored, so a consonant cluster
across a word boundary makes the preceding syllable heavy, as it should.
"""
import re, unicodedata

VOWELS = ['ai', 'au', 'ā', 'ī', 'ū', 'ṝ', 'ḹ', 'e', 'o', 'a', 'i', 'u', 'ṛ', 'ḷ']
LONG = {'ai', 'au', 'ā', 'ī', 'ū', 'ṝ', 'ḹ', 'e', 'o'}
ASPIRATES = ['kh', 'gh', 'ch', 'jh', 'ṭh', 'ḍh', 'th', 'dh', 'ph', 'bh']
CONSONANTS = set('kgṅcjñṭḍṇtdnpbmyrlvśṣsh')


def tokens(s):
    """letters of s as phonemes: ('V', vowel) / ('C', cons) / ('M', anusvāra-visarga)"""
    s = unicodedata.normalize('NFC', s.lower())
    s = s.replace(':', 'ḥ')        # the e-texts sometimes write visarga as a colon
    out, i = [], 0
    while i < len(s):
        two = s[i:i + 2]
        if two in ('ai', 'au'):
            out.append(('V', two)); i += 2; continue
        if two in ASPIRATES:
            out.append(('C', two)); i += 2; continue
        c = s[i]
        if c in ('ṃ', 'ṁ', 'ḥ', 'ẖ', 'ḫ'):
            out.append(('M', c))
        elif c in 'āīūṝḹeoaiuṛḷ':
            out.append(('V', c))
        elif c in CONSONANTS:
            out.append(('C', c))
        i += 1
    return out


def weights(s):
    t = tokens(s)
    w = []
    for k, (kind, val) in enumerate(t):
        if kind != 'V':
            continue
        heavy = val in LONG
        # following non-vowels up to the next vowel
        j, cons = k + 1, 0
        while j < len(t) and t[j][0] != 'V':
            if t[j][0] == 'M':
                heavy = True
            else:
                cons += 1
            j += 1
        if cons >= 2:
            heavy = True
        if j >= len(t) and cons >= 1:
            heavy = heavy or False     # a final single consonant: syllable stays as is
        w.append('G' if heavy else 'L')
    return ''.join(w)


def morae(w):
    return sum(2 if c == 'G' else 1 for c in w)


# ---- anuṣṭubh -------------------------------------------------------------
def anustubh_half(w):
    """w = weights of a half-verse (two pādas). True if it is a regular śloka
    half: 16 syllables, second pāda with ⏑–⏑ in syllables 5–7, first pāda
    pathyā or one of the usual vipulās, no ⏑⏑ in syllables 2–3 of either pāda."""
    if len(w) != 16:
        return False
    a, b = w[:8], w[8:]
    if b[4:7] != 'LGL':
        return False
    if a[1:3] == 'LL' or b[1:3] == 'LL':
        return False
    p = a[4:7]
    if p == 'LGG':                       # pathyā
        return True
    if p == 'LLL' and (a[1] == 'G' or a[3] == 'G'):   # na-vipulā
        return True
    if p == 'GLL' and a[3] == 'G':       # bha-vipulā
        return True
    if p == 'GGG' and a[3] == 'G':       # ma-vipulā
        return True
    if p == 'GLG' and a[3] == 'G':       # ra-vipulā
        return True
    return False


def anustubh_loose(w):
    """a half that is nearly a śloka half: 16 syllables with ⏑–⏑ at 13–15, or
    15/17 syllables ending ⏑–⏑x (a hypermetric or defective pāda)"""
    if len(w) == 16 and w[12:15] == 'LGL':
        return True
    if len(w) in (15, 17) and w[-4:-1] == 'LGL':
        return True
    return False


# ---- syllable-counted metres -----------------------------------------------
# pāda patterns (x = anceps); ardhasama pairs listed as (odd, even)
SAMA = {
    'indravajrā': 'GGLGGLLGLGx', 'upendravajrā': 'LGLGGLLGLGx',
    'rathoddhatā': 'GLGLLLGLGLx', 'svāgatā': 'GLGLLLGLLGx', 'śālinī': 'GGGGGLGGLGx',
    'vaṃśastha': 'LGLGGLLGLGLx', 'indravaṃśā': 'GGLGGLLGLGLx', 'drutavilambita': 'LLLGLLGLLGLx',
    'bhujaṅgaprayāta': 'LGGLGGLGGLGx', 'toṭaka': 'LLGLLGLLGLLx', 'pramitākṣarā': 'LLGLGLLLGLLx',
    'praharṣiṇī': 'GGGLLLLGLGLGx', 'rucirā': 'LGLGLLLLGLGLx', 'mañjubhāṣiṇī': 'LLGLGLLLGLGLx',
    'vasantatilakā': 'GGLGLLLGLLGLGx', 'mālinī': 'LLLLLLGGGLGGLGx', 'mandākrāntā': 'GGGGLLLLLGGLGGLGx',
    'śikhariṇī': 'LGGGGGLLLLLGGLLLx', 'hariṇī': 'LLLLLGGGGLGLLGLGx', 'pṛthvī': 'LGLLLGLGLLLGLGGLx',
    'śārdūlavikrīḍita': 'GGGLLGLGLLLGGGLGGLx', 'sragdharā': 'GGGGLGGLLLLLLGGLGGLGGx',
}
ARDHASAMA = {
    'puṣpitāgrā': ('LLLLLLGLGLGx', 'LLLLGLLGLGLGx'),
    'viyoginī': ('LLGLLGLGLx', 'LLGGLLGLGLx'),
    'aupacchandasika': ('LLGLLGLGLGx', 'LLGGLLGLGLGx'),
}


def match(w, pat, slack=0):
    if len(w) != len(pat):
        return False
    bad = sum(1 for c, p in zip(w, pat) if p != 'x' and c != p)
    return bad <= slack


def upajati(w):
    """indravajrā/upendravajrā mixed: the pāda differs only in syllable 1"""
    return len(w) == 11 and match(w[1:], 'GLGGLLGLGx')


def vrtta_pada(w):
    for name, pat in SAMA.items():
        if match(w, pat):
            return name
    if upajati(w):
        return 'upajāti'
    return None


def vrtta_half(w):
    """name of a syllable-counted metre this half-verse (two pādas) fits, else None"""
    n = len(w)
    if n % 2 == 0 and 18 <= n <= 44:
        a, b = w[:n // 2], w[n // 2:]
        ma, mb = vrtta_pada(a), vrtta_pada(b)
        if ma and mb:
            return ma if ma == mb else 'upajāti' if {ma, mb} <= {'indravajrā', 'upendravajrā', 'upajāti'} else ma + '/' + mb
        # same unknown pattern twice: a samavṛtta we do not list
        if n >= 20 and sum(1 for x, y in zip(a[:-1], b[:-1]) if x != y) <= 1 and 'L' in a and 'G' in a:
            return 'samavṛtta?'
    for name, (o, e) in ARDHASAMA.items():
        if n == len(o) + len(e) and match(w[:len(o)], o) and match(w[len(o):], e):
            return name
    return None


def arya_half(w, first=True):
    """āryā: 30 morae in the first half, 27 in the second (final syllable anceps)"""
    m = morae(w)
    want = 30 if first else 27
    return want - 1 <= m <= want + 1 and 10 <= len(w) <= 26


def anustubh_pada(w):
    """a single śloka pāda (when commentary splits a half-verse): 'odd'/'even'/None"""
    if len(w) != 8 or w[1:3] == 'LL':
        return None
    if w[4:7] == 'LGL':
        return 'even'
    if w[4:7] in ('LGG', 'LLL', 'GLL', 'GGG', 'GLG'):
        return 'odd'
    return None


def classify_half(text):
    """('anustubh'|metre name|'arya1'|'arya2'|'loose'|None, weights)"""
    w = weights(text)
    if anustubh_half(w):
        return 'anuṣṭubh', w
    v = vrtta_half(w)
    if v:
        return v, w
    if arya_half(w, True):
        return 'āryā1', w
    if arya_half(w, False):
        return 'āryā2', w
    if anustubh_loose(w):
        return 'loose', w
    p = anustubh_pada(w)
    if p:
        return 'pāda-' + p, w
    if 7 <= len(w) <= 9:
        return 'pāda?', w
    return None, w
