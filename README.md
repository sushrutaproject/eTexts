# eTexts

Digital reading editions of classical Sanskrit medical treatises, with
their commentaries, in IAST, published at
**https://sushrutaproject.github.io/eTexts/** with one combined search
across the whole collection.

| Directory | Text | Published at |
|---|---|---|
| `eCaraka/` | Carakasaṃhitā, with Cakrapāṇidatta | `/eTexts/eCaraka/` |
| `eSushruta/` | Suśrutasaṃhitā, with Ḍalhaṇa | `/eTexts/eSushruta/` |
| `eHrdaya/` | Aṣṭāṅgahṛdaya, with Aruṇadatta and Hemādri | `/eTexts/eHrdaya/` |
| `eMadhava/` | Mādhavanidāna, with the Madhukośa and Ātaṅkadarpaṇa | `/eTexts/eMadhava/` |
| `eSharngadhara/` | Śārṅgadharasaṃhitā, with Āḍhamalla and Kāśīrāma | `/eTexts/eSharngadhara/` |

Each directory was formerly its own repository in the `sushrutaproject`
organization; their full commit histories were carried over
(`git log -- eSushruta/` shows them).

## How it fits together

```
texts.yml                 register of hand-built texts (and order/overrides for TEI texts)
build.rb                  builds everything into _site/
tools/tei2site.py         converts a folder holding a TEI file into a reading site
tools/tei-template/       layouts, CSS etc. used for every TEI-generated text
Gemfile                   one Gemfile for every build (Jekyll 3.10)
.github/workflows/pages.yml   builds and deploys on every push to main
portal/                   the collection home page, combined search, About
eCaraka/ eSushruta/ ...   one complete Jekyll site per text (unchanged in design)
```

`build.rb` builds each text as its own Jekyll site into `_site/<id>/`,
then builds the portal into `_site/`. Each text keeps its own layouts,
CSS and reading controls. Two values are injected into each text at
build time: `corpus_root` (the collection's URL, used by the "eTexts /"
link and the header search box) and `text_id` (its directory name).

### Search

There is a single search page, `portal/search.html` (at `/eTexts/search/`).
Its *Search in* menu offers all texts, any single text, or any single
sthāna of a text. The header box on every text page searches that text
(or the sthāna being read) and lands on this page, where the scope can be
widened. Each text's old `search/` URL now forwards there, so existing
links and bookmarks keep working.

The search reads the per-sthāna index files that every text produces
(`<id>/search-index/<sthāna>.json`); the list of sthānas comes from each
text's `_data/sthanas.yml`. Each chapter in an index is a list of
segments in reading order, tagged `m` (mūla: `<div class="mula">`), `c`
(commentary: any other top-level `<div>`) or `n` (note: each item of
`<section class="notes">`), which is what lets the search look in the
mūla, commentaries and notes separately. The segments are made by
`_includes/search-entry.json`, one identical copy in each text.

Shared by every text and served from the portal: `assets/css/shared.css`
(search-hit highlight colour, `--hit-bg`) and
`assets/js/search-highlight.js` (highlighting hits on a chapter page).

Searching runs in the browser. The indexes for the whole collection come
to about 17 MB (about 5 MB as actually sent, compressed). To keep this
quick: the search page starts downloading them as soon as it opens (and
the home page as soon as the search box is used); results are shown as
each part arrives, in reading order; and the browser keeps the indexes in
its Cache Storage, so each is downloaded only once. Each index URL carries
a fingerprint of its contents (`?v=…`, added by `build.rb`), so adding or
correcting one text makes readers re-download only that text.

## Adding a new text from a TEI file (automatic)

1. Make a new folder at the top of the repository, named as the text
   should appear in its web address, e.g. `eBhela/`
   (→ `https://sushrutaproject.github.io/eTexts/eBhela/`).
2. Put the TEI file in it (any file name ending in `.xml`).
3. Commit and push (or, on github.com: **Add file → Upload files**, and
   drag the folder in).

That is all. The GitHub Action converts the TEI file into a reading site
(chapters, mūla and commentary, notes, a TEI download and an About page
built from the `<teiHeader>`), adds it to the home page, the menus and the
combined search, and publishes it a few minutes later. To correct the
text, edit the TEI file and push again: the site is always regenerated
from it, and nothing generated is stored in the repository.

**Optional settings.** A file `text.yml` next to the TEI file can set the
title, blurb, section names, commentary names and so on, where the TEI
header doesn't give what you want. `tools/text.yml.example` lists every
setting. Listing the folder in `texts.yml` (just `- id: eBhela`) fixes its
place in the order on the home page; otherwise TEI texts come after the
listed ones, alphabetically.

**What the converter understands.** It is meant to cope with TEI from
different projects (our own downloads, SARIT, private transcriptions);
it was tested on all 83 SARIT texts and on the five eTexts TEI files
(converting the e-Suśruta TEI reproduces the original site's search
results exactly). In brief:

- *Structure*: sections and chapters from the `<div>`s in `<body>`,
  recognised by `@type`/`@subtype` (sthāna, khaṇḍa, adhyāya, chapter,
  paṭala...) or, failing that, by nesting and size. Chapter titles from
  `<head>`.
- *Mūla and commentary*: from `@type`, `@subtype` or `@ana` on block
  elements (`div`, `ab`, `p`, `lg`, `quote`...): `mula`, `base-text`,
  `root`, `sūtra`... versus `commentary`, `commentary1`, `bhāṣya`, `ṭīkā`,
  `vyākhyā`... Untyped paragraphs beside an explicit mūla block count as
  commentary; otherwise untyped text is mūla. Each commentary gets its own
  show/hide switch.
- *Notes*: every non-empty `<note>`, and the readings of `<app>`, become
  numbered footnotes (searchable as "Notes"). Empty `<note/>` markers are
  treated as word breaks.
- *Other markup*: verse lines, page breaks (shown small, left out of the
  search), `<supplied>` ⟨…⟩, `<gap>`, `<unclear>`, `<choice>` (shows
  `corr`/`reg`), `<del>`/`<add>`. Unfamiliar elements keep their text and
  are listed in the conversion report.
- *Script*: Devanagari is transliterated to IAST, so the text can be
  searched with the others.

**When something goes wrong**, the rest of the collection is still
published, and the problem is shown at the top of the workflow run's
summary page on GitHub (**Actions** tab): a red *error* if the text was
left out (e.g. two `.xml` files in the folder and no `text.yml` saying
which to use), a yellow *warning* if it was published with a caveat (e.g.
the XML was not well-formed and was read in recovery mode). The full
conversion report for every TEI text is in the build log, and also at the
bottom of the text's own About page.

To try a TEI file before pushing it:
`python3 tools/tei2site.py eBhela /tmp/eBhela-site` (needs
`pip install -r tools/requirements.txt`) prints the same report.

## Adding a hand-built text

A text can also be a complete Jekyll site of its own, as the first five
are. Put the site in its own folder; it then needs:

- `_data/sthanas.yml`: one entry per section collection
  (`slug: {name, subtitle, count}`); a text with no sthāna division has a
  single entry, as in `eMadhava/`;
- its chapter HTML as top-level `<div class="mula">` blocks, other
  top-level `<div>`s for commentary, and an optional
  `<section class="notes">` list, as in the existing texts;
- `_includes/search-entry.json` (copy it from another text) and
  `search-index/<slug>.json` for each section (copy one from another text
  and change the collection name);
- in `_layouts/default.html` and `_layouts/chapter.html`, the links to
  the shared `shared.css` and `search-highlight.js`, as in the others;
- in `_includes/header.html`, the "eTexts /" link and the header search
  form pointing at `{{ site.corpus_root }}/search/` with
  `scope` = `{{ site.text_id }}`, as in the existing texts;
- `search.html` replaced by the short forwarding page used in the others;
- an entry in `texts.yml` (id, site_title, work, commentary, blurb,
  source, tei), since a hand-built site has no TEI header to read these
  from.

## Building locally

```sh
bundle install
pip install -r tools/requirements.txt
bundle exec ruby build.rb            # writes _site/ for base path /eTexts
cd _site && python3 -m http.server   # then open http://localhost:8000/
```

For a local preview at the server root use `--base ""`; to preview at
`/eTexts/` serve the folder that contains a link named `eTexts` pointing
to `_site`.

## Deployment

The workflow in `.github/workflows/pages.yml` runs on every push to
`main`. One-time setup on GitHub: **Settings → Pages → Build and
deployment → Source: GitHub Actions**. The workflow takes the base path
from GitHub Pages, so renaming the repository needs no code change.
