#!/usr/bin/env python3
"""
build_tei.py -- generate unified TEI P5 downloads for the Suśruta Project
e-text sites (eSushruta, eCaraka, eHrdaya, eMadhava, eSharngadhara).

Run from the root of any of the four repositories:

    python3 build_tei.py                      # write assets/tei/*.xml
    python3 build_tei.py --validate tei_all.rng   # ... and validate with jing

It reads the published Jekyll chapter files (the _<collection>/*.html
files, i.e. the IAST text as the site shows it) and writes two files:

    assets/tei/<slug>-mula.xml   root text only
    assets/tei/<slug>-full.xml   root text with commentary

The repository is identified from `baseurl` in _config.yml.  No
third-party Python packages are required; validation needs `jing`
(e.g. `pip install jingtrang`, which provides `pyjing`) or Java + jing.jar.
"""

import argparse
import datetime
import glob
import html
import os
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser

# ---------------------------------------------------------------------------
# Per-text configuration
# ---------------------------------------------------------------------------

CC0 = ("https://creativecommons.org/publicdomain/zero/1.0/",
       "CC0 1.0 Universal (public domain dedication) -- see LICENSE in the repository.")

CONFIGS = {
    "/eSushruta": dict(
        slug="susrutasamhita", idprefix="su",
        site="e-Suśruta", site_url="https://sushrutaproject.github.io/eSushruta/",
        repo="https://github.com/sushrutaproject/eSushruta",
        work="Suśrutasaṃhitā",
        authors=[("susruta", "Suśruta")],
        comm_title="with Ḍalhaṇa's Nibandhasaṅgraha",
        commentaries={"bhasya": dict(key="nibandhasangraha", resp="#dalhana")},
        commentators=[("dalhana", "Ḍalhaṇa", "Nibandhasaṅgraha")],
        digital=("NIIMH e-Samhita: Suśrutasaṃhitā",
                 "http://niimh.res.in/ebooks/esushruta/"),
        digital_org="National Institute of Indian Medical Heritage (NIIMH), CCRAS, Government of India",
        print_ed=("Yādavaśarman Trivikrama Ācārya", "1938",
                  "https://sushrutaproject1.github.io/Sushrutasamhita_Saktumiva2/06-su.ut-27-37-kumara/06-ut-vulgate-1938-27-37.xml?facs=1"),
        licence=None,
        notes_desc="The foot-of-chapter notes (pāṭhāntarāḥ) of the source record variant readings and comments from the printed edition.",
        extra=[],
    ),
    "/eCaraka": dict(
        slug="carakasamhita", idprefix="ca",
        site="e-Caraka", site_url="https://sushrutaproject.github.io/eCaraka/",
        repo="https://github.com/sushrutaproject/eCaraka",
        work="Carakasaṃhitā",
        authors=[("caraka", "Caraka")],
        comm_title="with Cakrapāṇidatta's Āyurvedadīpikā",
        commentaries={"bhasya": dict(key="ayurvedadipika", resp="#cakrapanidatta")},
        commentators=[("cakrapanidatta", "Cakrapāṇidatta", "Āyurvedadīpikā")],
        digital=("NIIMH e-Samhita: Carakasaṃhitā",
                 "http://niimh.res.in/ebooks/ecaraka/"),
        digital_org="National Institute of Indian Medical Heritage (NIIMH), CCRAS, Government of India",
        print_ed=("Yādavaśarman Trivikrama Ācārya", "1941",
                  "https://n2t.net/ark:/13960/t48q2f20n/"),
        licence=CC0,
        notes_desc="The foot-of-chapter notes (pāṭhāntarāḥ) of the source record variant readings and comments from the printed edition.",
        extra=["In Cikitsāsthāna the first two adhyāyas (Rasāyana and Vājīkaraṇa) "
               "are each divided into four pādas in the source; these are encoded "
               "as div[@type='pada'] within their adhyāya."],
    ),
    "/eHrdaya": dict(
        slug="astangahrdaya", idprefix="ah",
        site="e-Vāgbhaṭa", site_url="https://sushrutaproject.github.io/eHrdaya/",
        repo="https://github.com/sushrutaproject/eHrdaya",
        work="Aṣṭāṅgahṛdaya",
        authors=[("vagbhata", "Vāgbhaṭa")],
        comm_title="with Aruṇadatta's Sarvāṅgasundarā and Hemādri's Āyurvedarasāyana",
        commentaries={
            "aruna": dict(key="sarvangasundara", resp="#arunadatta"),
            "hemadri": dict(key="ayurvedarasayana", resp="#hemadri"),
        },
        commentators=[("arunadatta", "Aruṇadatta", "Sarvāṅgasundarā"),
                      ("hemadri", "Hemādri", "Āyurvedarasāyana")],
        digital=("e-Vāgbhaṭa: Aṣṭāṅgahṛdaya (vedotpatti.in)",
                 "https://vedotpatti.in/samhita/Vag/ehrudayam/"),
        digital_org="vedotpatti.in (IAIM/FRLHT), using the NIIMH e-Samhita software",
        print_ed=("Kunte et al.", "1939", "https://n2t.net/ark:/13960/t12p44f4h/"),
        licence=CC0,
        notes_desc="The source has no footnote or variant-reading apparatus.",
        extra=["Each commentary block opens with the siglum used in print "
               "(Sa. for the Sarvāṅgasundarā, Ā. rā. for the Āyurvedarasāyana), "
               "encoded as label[@type='siglum'].",
               "Hemādri's Āyurvedarasāyana is present in the source only for all of "
               "Sūtrasthāna and Kalpasiddhisthāna, the first six adhyāyas of "
               "Nidānasthāna and the first seven of Cikitsāsthāna; it is absent from "
               "Śārīrasthāna and Uttarasthāna. Its absence elsewhere reflects the "
               "source, not an encoding gap."],
    ),
    "/eMadhava": dict(
        slug="madhavanidana", idprefix="mn",
        site="e-Mādhavanidāna", site_url="https://sushrutaproject.github.io/eMadhava/",
        repo="https://github.com/sushrutaproject/eMadhava",
        work="Mādhavanidāna",
        authors=[("madhavakara", "Mādhavakara")],
        comm_title="with the Madhukośa and Ātaṅkadarpaṇa commentaries",
        commentaries={
            "bhasya-madhukosha": dict(key="madhukosa", resp="#vijayaraksita #srikanthadatta"),
            "bhasya-atankadarpana": dict(key="atankadarpana", resp="#vacaspati"),
        },
        commentators=[("vijayaraksita", "Vijayarakṣita", "Madhukośa"),
                      ("srikanthadatta", "Śrīkaṇṭhadatta", "Madhukośa"),
                      ("vacaspati", "Vācaspati", "Ātaṅkadarpaṇa")],
        digital=("NIIMH e-Samhita: Mādhavanidāna",
                 "http://niimh.res.in/ebooks/madhavanidana/"),
        digital_org="National Institute of Indian Medical Heritage (NIIMH), CCRAS, Government of India",
        print_ed=("Yādavaśarman Trivikrama Ācārya", "1955",
                  "http://n2t.net/ark:/13960/s218hd9qx7t"),
        licence=CC0,
        notes_desc="The foot-of-chapter notes (pāṭhāntarāḥ) of the source record variant readings from the printed edition.",
        extra=["The work has no sthāna division; the 70 adhyāyas are direct children of body.",
               "A note with no anchor in the text (it records a variant of the chapter title) "
               "is placed in the chapter head.",
               "One passage in adhyāya 21 (Ātaṅkadarpaṇa) is untagged in the source and "
               "could not be transliterated; it is kept in the source's ASCII romanization "
               "as seg[@type='untransliterated']."],
    ),
    "/eSharngadhara": dict(
        slug="sarngadharasamhita", idprefix="sd",
        site="e-Śārṅgadhara", site_url="https://sushrutaproject.github.io/eSharngadhara/",
        repo="https://github.com/sushrutaproject/eSharngadhara",
        work="Śārṅgadharasaṃhitā",
        authors=[("sarngadhara", "Śārṅgadhara")],
        comm_title="with Āḍhamalla's Dīpikā and Kāśīrāma's Gūḍhārthadīpikā",
        commentaries={
            "adhamalla": dict(key="dipika", resp="#adhamalla"),
            "kasirama": dict(key="gudharthadipika", resp="#kasirama"),
            "vyakhya": dict(key="unattributed", resp=None),
        },
        commentators=[("adhamalla", "Āḍhamalla", "Dīpikā"),
                      ("kasirama", "Kāśīrāma", "Gūḍhārthadīpikā")],
        digital=("CCRAS e-books: Śārṅgadharasaṃhitā",
                 "http://ccras.res.in/ccras_ebooks/readSam"),
        digital_org="Central Council for Research in Ayurvedic Sciences (CCRAS), Ministry of Ayush, Government of India",
        print_ed=None,
        licence=CC0,
        division=("khanda", "khaṇḍas"),
        note_type="editorial",
        notes_desc="The source embeds the editor's notes (variant readings marked pā., remarks on the "
                   "Calcutta printing, passages judged interpolated, etc.) in the running text; the web "
                   "edition gathers them as numbered notes at the foot of each chapter.",
        extra=["The work is divided into three khaṇḍas, encoded as div[@type='khanda'].",
               "Each commentary block opens with a siglum (Dī. for the Dīpikā, Gū. for the "
               "Gūḍhārthadīpikā), normalized from the source's own abbreviations and encoded as "
               "label[@type='siglum'].",
               "Two comments that carry no siglum in the source and whose attribution is uncertain "
               "(Uttarakhaṇḍa 3 and 4) are encoded as ab[@type='commentary'][@subtype='unattributed'] "
               "without @resp.",
               "A stray line of the Carakasaṃhitā at the end of Pūrvakhaṇḍa 7 in the source is omitted."],
    ),
}

TEI_RNG_URL = "http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng"

# ---------------------------------------------------------------------------
# Minimal HTML tree
# ---------------------------------------------------------------------------


class Node:
    def __init__(self, tag, attrs, parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []

    @property
    def classes(self):
        return self.attrs.get("class", "").split()

    def text(self):
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)


class TreeBuilder(HTMLParser):
    VOID = {"br", "hr", "img", "meta", "link", "input", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {})
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in self.VOID:
            self.cur = n

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse_html(s):
    b = TreeBuilder()
    b.feed(s)
    b.close()
    return b.root


# ---------------------------------------------------------------------------
# Source reading
# ---------------------------------------------------------------------------


def read_front_matter(path):
    t = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n", t, re.S)
    fm = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] == '"':
            v = v[1:-1].replace('\\"', '"')
        fm[k.strip()] = v
    return fm, t[m.end():]


def read_sthanas():
    """Ordered [(slug, name)] from _data/sthanas.yml, or None."""
    p = "_data/sthanas.yml"
    if not os.path.exists(p):
        return None
    out, key = [], None
    for line in open(p, encoding="utf-8"):
        m = re.match(r"^(\w+):\s*$", line)
        if m:
            key = m.group(1)
            continue
        m = re.match(r'^\s+name:\s*"?(.*?)"?\s*$', line)
        if m and key:
            out.append((key, m.group(1)))
    return out


def baseurl():
    for line in open("_config.yml", encoding="utf-8"):
        m = re.match(r'^baseurl:\s*"?([^"\s]*)"?', line)
        if m:
            return m.group(1)
    sys.exit("baseurl not found in _config.yml")


def strip_number(title):
    return re.sub(r"^\s*\d+(?:/\d+)?\.\s*", "", title).strip()


# ---------------------------------------------------------------------------
# HTML -> TEI conversion
# ---------------------------------------------------------------------------

esc = lambda s: html.escape(s, quote=False)
attr = lambda s: html.escape(s, quote=True)


class Warn:
    items = []

    @classmethod
    def add(cls, msg):
        cls.items.append(msg)


def collect_notes(body_root):
    """id -> (number, text) from <section class='notes'>."""
    notes = {}
    for sec in iter_nodes(body_root):
        if sec.tag == "section" and "notes" in sec.classes:
            for li in iter_nodes(sec):
                if li.tag == "li" and "id" in li.attrs:
                    num, parts = "", []
                    for c in li.children:
                        if isinstance(c, str):
                            parts.append(c)
                        elif "note-num" in c.classes:
                            num = c.text().strip()
                        elif "note-back" in c.classes:
                            pass
                        else:
                            parts.append(c.text())
                    txt = re.sub(r"\s+", " ", "".join(parts)).strip()
                    txt = re.sub(r"^\.\s*", "", txt)  # stray leading '. ' in some sources
                    notes[li.attrs["id"]] = (num, txt)
    return notes


def iter_nodes(n):
    for c in n.children:
        if not isinstance(c, str):
            yield c
            yield from iter_nodes(c)


NOTE_TYPE = "variant"   # set per text from the config in main()


def note_xml(num, txt):
    return f'<note place="foot" type="{NOTE_TYPE}" n="{attr(num)}">{esc(txt)}</note>'


def inline(node, notes, used, where):
    """Convert inline children of `node` to TEI; verse markers returned as ('M', n, text)."""
    out = []
    for c in node.children:
        if isinstance(c, str):
            out.append(esc(c))
            continue
        cl = c.classes
        if c.tag == "span" and "verse-marker" in cl:
            out.append(("M", c.text()))
        elif c.tag == "sup" and "noteref" in cl:
            a = next((x for x in iter_nodes(c) if x.tag == "a"), None)
            nid = a.attrs.get("href", "").lstrip("#") if a else ""
            if nid in notes:
                used.add(nid)
                out.append(note_xml(*notes[nid]))
            else:
                Warn.add(f"{where}: note reference {nid!r} has no note text")
        elif c.tag == "span" and "untransliterated" in cl:
            out.append(f'<seg type="untransliterated" rend="source-ascii-romanization">{esc(c.text())}</seg>')
        elif c.tag == "span" and "commentator-label" in cl:
            out.append(f'<label type="siglum">{esc(c.text().strip())}</label>')
        else:
            Warn.add(f"{where}: unexpected <{c.tag} class='{' '.join(cl)}'> -- kept as plain text")
            out.append(esc(c.text()))
    return out


def segment(parts):
    """Group inline parts into <seg n=...> units, each ending at a verse marker."""
    out, buf = [], []

    def flush_plain():
        s = "".join(buf)
        if s.strip():
            out.append(s)
        buf.clear()

    for p in parts:
        if isinstance(p, tuple):
            marker = p[1]
            n = re.sub(r"[|\s]", "", marker)
            body = "".join(buf)
            lead = body[: len(body) - len(body.lstrip())]
            body = body.lstrip()
            out.append(lead)
            nattr = f' n="{attr(n)}"' if n else ""
            out.append(f'<seg type="unit"{nattr}>{body}{esc(marker)}</seg>')
            buf.clear()
        else:
            buf.append(p)
    flush_plain()
    s = "".join(out)
    return re.sub(r"\s+", " ", s).strip()


def convert_chapter(path, cfg, with_comm, where):
    fm, body = read_front_matter(path)
    root = parse_html(body)
    notes = collect_notes(root)
    used = set()
    blocks = []
    for n in root.children:
        if isinstance(n, str):
            if n.strip():
                Warn.add(f"{where}: stray text outside blocks -- ignored: {n.strip()[:40]!r}")
            continue
        if n.tag == "section":
            continue
        if n.tag != "div":
            Warn.add(f"{where}: unexpected top-level <{n.tag}> -- ignored")
            continue
        cl = n.classes
        if "mula" in cl:
            blocks.append(f'<ab type="mula">{segment(inline(n, notes, used, where))}</ab>')
            continue
        key = next((k for k in cfg["commentaries"] if k in cl), None)
        if key is None:
            Warn.add(f"{where}: unrecognised block class {cl} -- ignored")
            continue
        if with_comm:
            c = cfg["commentaries"][key]
            resp = f' resp="{c["resp"]}"' if c.get("resp") else ""
            blocks.append(f'<ab type="commentary" subtype="{c["key"]}"{resp}>'
                          f'{segment(inline(n, notes, used, where))}</ab>')
        else:
            # record the notes as consumed so they are not reported as orphans
            inline(n, notes, used, where)
    orphans = [notes[k] for k in notes if k not in used]
    return fm, blocks, orphans


# ---------------------------------------------------------------------------
# Document assembly
# ---------------------------------------------------------------------------


def chapters_for(coll):
    files = sorted(glob.glob(f"_{coll}/*.html"))
    items = []
    for f in files:
        fm, _ = read_front_matter(f)
        items.append((float(fm.get("order", 0)), int(fm.get("pada", 0) or 0), f, fm))
    items.sort(key=lambda x: (x[0], x[1]))
    return items


def build_body(cfg, with_comm, stats):
    P = cfg["idprefix"]
    out = []

    def adhyaya_divs(coll, idbase, ind):
        items = chapters_for(coll)
        # group pāda files by adhyāya
        groups = []
        for order, pada, f, fm in items:
            a = fm.get("adhyaya", "")
            if pada and groups and groups[-1][0] == a and groups[-1][1]:
                groups[-1][2].append((pada, f, fm))
            else:
                groups.append((a, bool(pada), [(pada, f, fm)]))
        for a, has_pada, files in groups:
            stats["adhyaya"] += 1
            did = f"{idbase}.{a}"
            first_title = files[0][2].get("title", "")
            if has_pada:
                head = strip_number(first_title).split(" - ")[0]
                out.append(f'{ind}<div type="adhyaya" n="{attr(a)}" xml:id="{did}">')
                out.append(f"{ind}  <head>{esc(head)}</head>")
                for pada, f, fm in files:
                    where = f
                    _, blocks, orphans = convert_chapter(f, cfg, with_comm, where)
                    phead = strip_number(fm.get("title", ""))
                    phead = phead.split(" - ", 1)[1] if " - " in phead else phead
                    out.append(f'{ind}  <div type="pada" n="{pada}" xml:id="{did}.{pada}">')
                    out.append(f"{ind}    <head>{esc(phead)}{''.join(note_xml(*o) for o in orphans)}</head>")
                    out.extend(f"{ind}    {b}" for b in blocks)
                    out.append(f"{ind}  </div>")
                out.append(f"{ind}</div>")
            else:
                f, fm = files[0][1], files[0][2]
                _, blocks, orphans = convert_chapter(f, cfg, with_comm, f)
                for o in orphans:
                    Warn.add(f"{f}: unanchored note {o[0]} placed in chapter head")
                out.append(f'{ind}<div type="adhyaya" n="{attr(a)}" xml:id="{did}">')
                out.append(f"{ind}  <head>{esc(strip_number(fm.get('title', '')))}"
                           f"{''.join(note_xml(*o) for o in orphans)}</head>")
                out.extend(f"{ind}  {b}" for b in blocks)
                out.append(f"{ind}</div>")

    sthanas = read_sthanas()
    if sthanas:
        for i, (slug, name) in enumerate(sthanas, 1):
            stats["sthana"] += 1
            out.append(f'      <div type="{cfg.get("division", ("sthana",))[0]}" n="{i}" xml:id="{P}.{i}">')
            out.append(f"        <head>{esc(name)}</head>")
            adhyaya_divs(slug, f"{P}.{i}", "        ")
            out.append("      </div>")
    else:
        colls = [d[1:] for d in os.listdir(".")
                 if d.startswith("_") and os.path.isdir(d)
                 and d not in ("_site", "_layouts", "_includes", "_data", "_sass")]
        if len(colls) != 1:
            sys.exit(f"cannot determine chapter collection: {colls}")
        adhyaya_divs(colls[0], P, "      ")
    return "\n".join(out)


def build_header(cfg, with_comm, stats, today):
    variant = ("root text with commentary" if with_comm else "root text only")
    sub = f"{cfg['comm_title']}" if with_comm else "root text (mūla) only"
    authors = "\n".join(
        f'        <author xml:id="{i}"><persName xml:lang="sa-Latn">{esc(n)}</persName></author>'
        for i, n in cfg["authors"])
    comms = ""
    if with_comm:
        comms = "\n".join(
            f'        <author xml:id="{i}" role="commentator"><persName xml:lang="sa-Latn">{esc(n)}</persName>'
            f' (<title xml:lang="sa-Latn">{esc(w)}</title>)</author>'
            for i, n, w in cfg["commentators"])
    lic = cfg["licence"]
    availability = (f'<licence target="{lic[0]}">{esc(lic[1])}</licence>' if lic else
                    f"<p>See the licence information in the repository: {esc(cfg['repo'])}</p>")
    print_bibl = ""
    if cfg.get("print_ed"):
        ed, year, link = cfg["print_ed"]
        print_bibl = f"""
        <bibl type="print">
          <title xml:lang="sa-Latn">{esc(cfg['work'])}</title>
          <editor>{esc(ed)}</editor>
          <date when="{year}">{year}</date>
          <ptr target="{attr(link)}"/>
        </bibl>"""
    extent = f"{stats['adhyaya']} adhyāyas" + (f" in {stats['sthana']} {cfg.get('division', ('sthana', 'sthānas'))[1]}" if stats["sthana"] else "")
    comm_decl = ""
    if with_comm:
        comm_decl = ("<p>Root text and commentary follow the source's own division of every word "
                     "into registers. Root-text blocks are ab[@type='mula']; commentary blocks are "
                     "ab[@type='commentary'], with @subtype naming the commentary and @resp pointing "
                     "to its author(s) in the titleStmt.</p>")
    else:
        comm_decl = ("<p>This file contains the root text only: all commentary blocks, and the "
                     "notes anchored in them, have been omitted. Root-text blocks are ab[@type='mula'].</p>")
    extras = "".join(f"\n          <p>{esc(e)}</p>" for e in cfg["extra"])
    return f"""  <teiHeader xml:lang="en">
    <fileDesc>
      <titleStmt>
        <title type="main" xml:lang="sa-Latn">{esc(cfg['work'])}</title>
        <title type="sub">{esc(sub)}: a TEI edition derived from {esc(cfg['site'])}</title>
{authors}
{comms}
        <respStmt>
          <resp>digitization and transliteration of the source</resp>
          <orgName>{esc(cfg['digital_org'])}</orgName>
        </respStmt>
        <respStmt>
          <resp>web edition and TEI conversion</resp>
          <orgName>The Suśruta Project</orgName>
        </respStmt>
      </titleStmt>
      <editionStmt>
        <edition>Unified TEI file, {esc(variant)}, generated <date when="{today}">{today}</date> by build_tei.py</edition>
      </editionStmt>
      <extent>{esc(extent)}</extent>
      <publicationStmt>
        <publisher>The Suśruta Project</publisher>
        <pubPlace><ref target="{cfg['site_url']}">{esc(cfg['site_url'])}</ref></pubPlace>
        <date when="{today}">{today}</date>
        <availability>
          {availability}
        </availability>
      </publicationStmt>
      <sourceDesc>
        <bibl type="digital">
          <title>{esc(cfg['digital'][0])}</title>
          <orgName>{esc(cfg['digital_org'])}</orgName>
          <ptr target="{attr(cfg['digital'][1])}"/>
        </bibl>{print_bibl}
      </sourceDesc>
    </fileDesc>
    <encodingDesc>
      <projectDesc>
        <p>A plain, archival TEI rendering of the text published on {esc(cfg['site'])}
          ({esc(cfg['repo'])}), itself built from the digital edition named in the sourceDesc.
          The file is generated automatically from the site's chapter pages.</p>
      </projectDesc>
      <editorialDecl>
        <p>The text is given in IAST as it appears on the web edition. Chapter and verse
          divisions follow the source edition. Each stretch of text ending in one of the
          source's verse or section numbers (e.g. ||12||) is encoded as seg[@type='unit']
          with that number in @n; the number itself is retained in the text.</p>
        {comm_decl}
        <p>{esc(cfg['notes_desc'])} Notes are placed at their point of reference as
          note[@place='foot'][@type='{cfg.get("note_type", "variant")}'], with the source's note number in @n.</p>{extras}
      </editorialDecl>
    </encodingDesc>
    <profileDesc>
      <langUsage>
        <language ident="sa-Latn">Sanskrit, in IAST transliteration</language>
        <language ident="en">English</language>
      </langUsage>
      <textClass>
        <keywords>
          <term>Āyurveda</term>
        </keywords>
      </textClass>
    </profileDesc>
    <revisionDesc>
      <change when="{today}">Generated from the Jekyll chapter files by build_tei.py.</change>
    </revisionDesc>
  </teiHeader>"""


def build(cfg, with_comm, today):
    stats = {"sthana": 0, "adhyaya": 0}
    body = build_body(cfg, with_comm, stats)
    header = build_header(cfg, with_comm, stats, today)
    header = re.sub(r"\n\s*\n", "\n", header)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<?xml-model href="{TEI_RNG_URL}" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="sa-Latn">
{header}
  <text>
    <body>
{body}
    </body>
  </text>
</TEI>
"""


def validate(path, rng):
    for cmd in (["pyjing", rng, path], ["jing", rng, path]):
        if shutil.which(cmd[0]):
            r = subprocess.run(cmd, capture_output=True, text=True)
            ok = r.returncode == 0
            print(f"  {'valid' if ok else 'INVALID'}: {path}")
            if not ok:
                print((r.stdout + r.stderr)[:3000])
            return ok
    print("  (jing not found -- skipping validation)")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", metavar="TEI_ALL_RNG", help="path to tei_all.rng")
    ap.add_argument("--outdir", default="assets/tei")
    a = ap.parse_args()
    b = baseurl()
    if b not in CONFIGS:
        sys.exit(f"no configuration for baseurl {b!r}")
    cfg = CONFIGS[b]
    global NOTE_TYPE
    NOTE_TYPE = cfg.get("note_type", "variant")
    today = datetime.date.today().isoformat()
    os.makedirs(a.outdir, exist_ok=True)
    ok = True
    for with_comm, suffix in ((False, "mula"), (True, "full")):
        Warn.items = []
        xml = build(cfg, with_comm, today)
        path = os.path.join(a.outdir, f"{cfg['slug']}-{suffix}.xml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(xml)
        print(f"wrote {path} ({len(xml.encode('utf-8')) / 1e6:.1f} MB)")
        for w in dict.fromkeys(Warn.items):
            print("  warning:", w)
        if a.validate:
            ok &= validate(path, a.validate)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
