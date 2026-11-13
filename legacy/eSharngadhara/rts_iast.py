"""
Conversion of the CCRAS/Padma romanization (RTS-style: B = bh, K = kh,
S = ś, Sh = ṣ, Ru = ṛ, ~g = ṅ, ~j = ñ, ~a = avagraha, ...) to IAST,
plus a small Devanagari -> IAST converter used only to CHECK the first
against the Devanagari titles the server also supplies.
"""
import re
import unicodedata

# Longest tokens first. Lower-case aspirates (bh, gh...) occur in some
# footnotes, which use ordinary ITRANS; they are safe to accept globally.
_TOKENS = [
    ("lRU", "ḹ"), ("lRu", "ḷ"), ("RU", "ṝ"), ("Ru", "ṛ"),
    ("Sh", "ṣ"), ("Th", "ṭh"), ("Dh", "ḍh"),
    ("~h", "h"),   # plain h after a consonant: vAg~hasta = vāghasta, not vāgh-
    ("~g", "ṅ"), ("~j", "ñ"), ("~a", "'"), ("~M", "m̐"),
    ("ai", "ai"), ("au", "au"),
    ("bh", "bh"), ("gh", "gh"), ("kh", "kh"), ("jh", "jh"), ("ph", "ph"),
    ("th", "th"), ("dh", "dh"),
    ("A", "ā"), ("I", "ī"), ("U", "ū"),
    ("K", "kh"), ("G", "gh"), ("C", "ch"), ("J", "jh"),
    ("T", "ṭ"), ("D", "ḍ"), ("N", "ṇ"),
    ("P", "ph"), ("B", "bh"), ("S", "ś"),
    ("M", "ṃ"), ("H", "ḥ"),
]
_TOKEN_RE = re.compile("|".join(re.escape(t) for t, _ in _TOKENS))
_MAP = dict(_TOKENS)


def rts_to_iast(text):
    text = text.replace("^^", "")          # hiatus marker, e.g. varShA^^Rutu
    # abbreviation point: dI0, pA0 -> dī., pā. -- but a 0 inside a real
    # numeral (verse numbers such as 100) is left alone
    text = re.sub(r"(?<!\d)0(?!\d)", ".", text)
    return unicodedata.normalize("NFC", _TOKEN_RE.sub(lambda m: _MAP[m.group(0)], text))


# ---- Devanagari -> IAST (validation only) ----
_V = {"अ": "a", "आ": "ā", "इ": "i", "ई": "ī", "उ": "u", "ऊ": "ū", "ऋ": "ṛ", "ॠ": "ṝ",
      "ऌ": "ḷ", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au"}
_M = {"ा": "ā", "ि": "i", "ी": "ī", "ु": "u", "ू": "ū", "ृ": "ṛ", "ॄ": "ṝ", "ॢ": "ḷ",
      "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॊ": "o", "ॆ": "e"}
_C = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ṅ", "च": "c", "छ": "ch", "ज": "j",
      "झ": "jh", "ञ": "ñ", "ट": "ṭ", "ठ": "ṭh", "ड": "ḍ", "ढ": "ḍh", "ण": "ṇ", "त": "t",
      "थ": "th", "द": "d", "ध": "dh", "न": "n", "प": "p", "फ": "ph", "ब": "b", "भ": "bh",
      "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "ś", "ष": "ṣ", "स": "s",
      "ह": "h", "ळ": "ḷ", "ख़": "kh"}
_O = {"ं": "ṃ", "ः": "ḥ", "ँ": "m̐", "ऽ": "'", "।": "|", "॥": "||"}


def deva_to_iast(s):
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\u093C", "")           # drop nukta: the server writes ख़ for kh
    out, i = [], 0
    while i < len(s):
        ch = s[i]
        if ch in _C:
            out.append(_C[ch])
            nxt = s[i + 1] if i + 1 < len(s) else ""
            if nxt == "्":
                i += 2
                continue
            if nxt in _M:
                out.append(_M[nxt]); i += 2; continue
            out.append("a")
        elif ch in _V:
            out.append(_V[ch])
        elif ch in _O:
            out.append(_O[ch])
        elif "०" <= ch <= "९":
            out.append(str(ord(ch) - ord("०")))
        else:
            out.append(ch)
        i += 1
    return "".join(out)
