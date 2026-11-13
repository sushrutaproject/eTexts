#!/usr/bin/env python3
"""
Builds the e-Śārṅgadhara Jekyll site from the raw CCRAS data saved by
scrape_sharngadhara.py in sharngadhara_data/raw/.

What it does to the raw text:
  - removes duplicate rows (the server sometimes repeats a passage);
  - groups rows by passage (adhi_no): root text first, then Āḍhamalla's
    Dīpikā, then Kāśīrāma's Gūḍhārthadīpikā;
  - tells the two commentaries apart by the label the source puts at the
    head of each ("dIpikA -" / "dI0 -" for Āḍhamalla, "gU0 -" for
    Kāśīrāma), strips that label and puts the site's own in its place;
  - lifts the editor's embedded notes (#foot@ ... #) out into numbered
    notes at the foot of the chapter, dropping empty placeholders
    ("padya link data N");
  - converts the CCRAS romanization to IAST (rts_iast.py) and checks the
    conversion against the Devanagari chapter titles the server supplies.

Usage (from the repo root):
    python3 build_sharngadhara.py
"""

import json
import re
import unicodedata
from pathlib import Path

from rts_iast import rts_to_iast, deva_to_iast

RAW = Path("sharngadhara_data/raw")
OUT_DIR = Path(".")

KHANDAS = {  # CCRAS sthana_id -> (slug, display name, subtitle)
    1: ("purvakhanda", "Pūrvakhaṇḍa", "Fundamentals and Diagnosis"),
    2: ("madhyamakhanda", "Madhyamakhaṇḍa", "Pharmaceutical Preparations"),
    3: ("uttarakhanda", "Uttarakhaṇḍa", "Therapeutic Procedures"),
}

# The commentator's abbreviation at the head of each comment, in all the
# spellings the source uses: dIpikA, dI0, di0, "dI -"; gU0, "gU 0".
LABEL = r"(dIpikA(?=\s*[-–—])|d[Ii]\s*0|dI(?=\s*[-–—])|gU\s*0)\s*[-–—]*\s*"
LABEL_AT_START = re.compile(LABEL)
# ...or, occasionally, after a short introductory phrase: "...Aha - dI0 - ..."
LABEL_AFTER_INTRO = re.compile(r"\s[-–—]\s*" + LABEL)

# Cases the rules above cannot settle, decided by hand from the raw data.
# Key: (chapter file stem, adhi_no, opening words of the raw comment).
# Value: "adhamalla", "kasirama", "mula" (root text misfiled as comment),
# or "drop" (stray matter that does not belong to this text).
OVERRIDES = {
    # no label, but stands in the Dīpikā's usual place before Gū0
    ("k1_a02", "54", "idAnIM doShANAmakAle ~api"): "adhamalla",
    # stray first line of the Carakasaṃhitā at the end of the chapter
    ("k1_a07", "230", "athAto dIrgha~njIvitIyamad"): "drop",
    # two unlabelled comments on the yūṣa verse; taken in the usual Dī/Gū order
    ("k2_a02", "107", "ayaM dravyakRutayUSho~api "): "adhamalla",
    ("k2_a02", "107", "atha yUShaH | yUShe rulkad"): "kasirama",
    # root-text verses (śvitra lepas) filed in the commentary field
    ("k3_a11", "12", "Svitre lepAH |\nsuvarNapuSh"): "mula",
    # no label, but stands in the Dīpikā's usual place before Gū0
    ("k3_a12", "13", "idAnIM raktasrute: kiM tyA"): "adhamalla",
}

# Root-text rows that do not belong to this work.
STRAY_ROOT = [
    "athAto dIrgha~njIvitIyamadhyAyaM",   # Carakasaṃhitā, Sū. 1.1, end of Pūrva 7
]

NOTE_RE = re.compile(r"#foot@(.*?)#", re.S)
VERSE_RE = re.compile(r"(\|\|\s*[\d,\-–]+\s*\|\|)")


def read_labels():
    cfg = (OUT_DIR / "_config.yml").read_text(encoding="utf-8")
    def get(key, default):
        m = re.search(rf'^{key}:\s*"(.*?)"', cfg, re.M)
        return m.group(1) if m else default
    return {"adhamalla": get("label_adhamalla", "Dī."),
            "kasirama": get("label_kasirama", "Gū."),
            "vyakhya": None, "mula": None}


def escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def tidy(s):
    s = re.sub(r"\$\d+", "", s)            # end-of-record markers
    s = s.strip().strip('"').strip()
    return re.sub(r"\s+", " ", s)


def classify(vya, where=None):
    """Return (kind, text-with-label-removed)."""
    if where is not None:
        norm = " ".join(vya.split())
        for (stem, adhi, start), forced in OVERRIDES.items():
            if (stem, adhi) == where and norm.startswith(" ".join(start.split())):
                return forced, vya.strip()
    body = vya.strip().lstrip('"').strip()
    m = LABEL_AT_START.match(body)
    if not m:
        m2 = LABEL_AFTER_INTRO.search(body[:200])
        if m2:
            m = m2
    if m:
        kind = "kasirama" if m.group(1).startswith("gU") else "adhamalla"
        return kind, (body[:m.start()] + (" - " if m.start() else "") + body[m.end():]).strip()
    # colophons and closing verses name their author
    if re.search(r"kASIrAm|gUDhArthadIpik", body):
        return "kasirama", body
    if re.search(r"[aA]~?a?Dhamal", body):
        return "adhamalla", body
    return "vyakhya", body


class Notes:
    def __init__(self):
        self.items = []

    def lift(self, raw):
        """Replace #foot@..# by a placeholder, collecting the note text."""
        def repl(m):
            body = m.group(1).strip().lstrip("-–").strip()
            if not body or re.fullmatch(r"padya link data\s*\d*", body):
                return " "
            self.items.append(body)
            return f"\x00{len(self.items)}\x00"
        return NOTE_RE.sub(repl, raw)


# Devanagari vowel signs that leaked into the romanized text as bare
# character codes ("#093E;" etc.). A sign after "a" replaces that inherent
# vowel (kaPavya#093E;pta -> kaPavyApta; tanmUlatvAta#094D; -> tanmUlatvAt);
# elsewhere it is dropped.
_SIGN = {"093E": "A", "093F": "i", "0940": "I", "0941": "u", "0942": "U",
         "0943": "Ru", "0944": "RU", "0947": "e", "0948": "ai", "094B": "o",
         "094C": "au", "094D": "", "0970": "0"}
_SIGN_RE = re.compile(r"(a?)#(09[0-9A-Fa-f]{2});")


def normalize_raw(s):
    def fix(m):
        v = _SIGN.get(m.group(2).upper())
        if v is None:
            return m.group(1)
        if m.group(2).upper() == "0970":
            return m.group(1) + v
        return v if m.group(1) else ""
    s = _SIGN_RE.sub(fix, s)
    # quotation marks: `` ... '' and ` ... '  ->  “ ... ”  and  ‘ ... ’
    # (the avagraha is written ~a in the source, so ' is always a quote)
    s = s.replace("``", "“").replace("''", "”").replace("`", "‘").replace("'", "’")
    return s


def render(raw, notes):
    text = notes.lift(normalize_raw(raw))
    text = escape(rts_to_iast(tidy(text)))
    text = VERSE_RE.sub(r'<span class="verse-marker">\1</span>', text)
    text = re.sub(r"\s*\x00(\d+)\x00\s*",
                  lambda m: f'<sup class="noteref" id="nref-{m.group(1)}">'
                            f'<a href="#note-{m.group(1)}">{m.group(1)}</a></sup> ', text)
    return text.strip()


def build_chapter(rows, labels, stats, stem=""):
    # de-duplicate, keep order
    seen, clean = set(), []
    for r in rows:
        key = (str(r.get("adhi_no")), r.get("pada") or "", r.get("vya_text") or "")
        if key in seen:
            stats["dupes"] += 1
            continue
        seen.add(key)
        clean.append(r)

    groups, order = {}, []
    for r in clean:
        a = str(r.get("adhi_no"))
        if a not in groups:
            groups[a] = {"mula": [], "adhamalla": [], "kasirama": [], "vyakhya": []}
            order.append(a)
        pada = r.get("pada") or ""
        if pada.strip():
            if any(" ".join(pada.split()).startswith(x) for x in STRAY_ROOT):
                stats["dropped"] += 1
            else:
                groups[a]["mula"].append(pada)
        vya = r.get("vya_text") or ""
        if re.search(r"[A-Za-z]", vya):          # skip empty and "-" rows
            kind, txt = classify(vya, (stem, a))
            if kind == "drop":
                stats["dropped"] += 1
                continue
            groups[a][kind].append(txt)
            if kind == "mula":
                stats["mula"] += 1

    # a comment field that merely repeats the root text is dropped
    for a in order:
        roots = {" ".join(p.split()) for p in groups[a]["mula"]}
        for kind in ("adhamalla", "kasirama", "vyakhya"):
            keep = []
            for t in groups[a][kind]:
                if " ".join(t.split()) in roots:
                    stats["dropped"] += 1
                else:
                    keep.append(t)
                    stats[kind] += 1
            groups[a][kind] = keep

    notes = Notes()
    body = []
    for a in order:
        g = groups[a]
        for kind in ("mula", "adhamalla", "kasirama", "vyakhya"):
            for raw in g[kind]:
                html = render(raw, notes)
                if not html:
                    continue
                lab = labels.get(kind)
                lab_html = f'<span class="commentator-label">{lab}</span> ' if lab else ""
                body.append(f'<div class="{kind}">{lab_html}{html}</div>')

    if notes.items:
        body.append('<section class="notes">\n<h2>Editor\'s notes</h2>\n<ol>')
        for i, n in enumerate(notes.items, 1):
            body.append(f'<li id="note-{i}"><span class="note-num">{i}</span> '
                        f'{escape(rts_to_iast(tidy(n)))} '
                        f'<a class="note-back" href="#nref-{i}">↩</a></li>')
        body.append("</ol>\n</section>")
        stats["notes"] += len(notes.items)

    kinds = {k for g in groups.values() for k, v in g.items() if v}
    return "\n".join(body), kinds


def slugify(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    t = re.sub(r"^atha\s+", "", t)
    return re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower() or "chapter"


def build():
    labels = read_labels()
    structure = json.loads((RAW / "structure.json").read_text(encoding="utf-8"))
    stats = {"dupes": 0, "dropped": 0, "mula": 0, "adhamalla": 0, "kasirama": 0, "vyakhya": 0, "notes": 0}
    title_problems, summary, coverage = [], {}, {}

    for kh in structure["khandas"]:
        slug, name, sub = KHANDAS[int(kh["sthana_id"])]
        coll = OUT_DIR / f"_{slug}"
        coll.mkdir(exist_ok=True)
        for old in coll.glob("*.html"):
            old.unlink()

        for ch in kh["chapters"]:
            num = int(ch["adhyaya_id"])
            title = rts_to_iast(ch["adh_itrans"]).strip()
            check = deva_to_iast(ch.get("adh_unic", "")).strip()
            if check and check != title:
                title_problems.append(f"{slug} {num}: {title}  vs  {check}")

            src = RAW / f"k{int(kh['sthana_id'])}_a{num:02d}.json"
            if not src.exists():
                print(f"WARNING: missing {src}")
                continue
            rows = json.loads(src.read_text(encoding="utf-8"))
            html, kinds = build_chapter(rows, labels, stats, src.stem)
            coverage.setdefault(slug, []).append(
                (num, "adhamalla" in kinds, "kasirama" in kinds, "vyakhya" in kinds))

            front = (f'---\ntitle: "{num}. {title}"\nadhyaya: {num}\norder: {num}\n---\n')
            (coll / f"{num:02d}-{slugify(title)}.html").write_text(
                front + html + "\n", encoding="utf-8")

        summary[slug] = (name, sub, len(kh["chapters"]))
        print(f"{slug}: {len(kh['chapters'])} chapters")

    lines = []
    for sid in sorted(KHANDAS):
        slug, name, sub = KHANDAS[sid]
        n = summary.get(slug, (name, sub, 0))[2]
        lines += [f"{slug}:", f'  name: "{name}"', f'  subtitle: "{sub}"', f"  count: {n}"]
    (OUT_DIR / "_data").mkdir(exist_ok=True)
    (OUT_DIR / "_data" / "sthanas.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nComment blocks: Āḍhamalla {stats['adhamalla']}, Kāśīrāma {stats['kasirama']}, "
          f"unlabelled {stats['vyakhya']}, root text moved from comment field {stats['mula']}. "
          f"Duplicate rows dropped: {stats['dupes']}; stray/duplicate comments dropped: {stats['dropped']}. "
          f"Editor's notes: {stats['notes']}.")
    print("Coverage per chapter (Ā = Āḍhamalla, K = Kāśīrāma, ? = unlabelled):")
    for slug, rows in coverage.items():
        print(f"  {slug}: " + " ".join(
            f"{n}:{'Ā' if a else '-'}{'K' if k else '-'}{'?' if u else ''}" for n, a, k, u in rows))
    if title_problems:
        print("\nTitle check (romanization vs Devanagari) -- please look at these:")
        for t in title_problems:
            print("  " + t)
    else:
        print("\nTitle check: all chapter titles agree with the Devanagari.")


if __name__ == "__main__":
    build()
