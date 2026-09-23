# e-Suśruta

A static Jekyll reading edition of the **Suśrutasaṃhitā**, a Sanskrit
treatise on medicine and surgery, with **Ḍalhaṇa's** commentary, the
*Nibandhasaṅgraha*, in IAST. Content drawn from the
[NIIMH e-Samhita](http://niimh.res.in/ebooks/esushruta/); see `about.md`
for provenance and limitations.

## Structure

- `_sutrasthana/`, `_nidanasthana/`, `_sharirasthana/`, `_cikitsasthana/`,
  `_kalpasthana/`, `_uttaratantra/` — one Jekyll collection per sthāna,
  one file per adhyāya. Root text is in `<div class="mula">`, Ḍalhaṇa's
  commentary in `<div class="bhasya">`, variant readings in
  `<section class="notes">`.
- `_data/sthanas.yml` — display names, subtitles, chapter counts.
- `_layouts/`, `_includes/`, `assets/css/style.css` — design, the
  commentary show/hide control, and search-hit highlighting.
- `search.html` + `search-index/*.json` — client-side search. The index
  files are Liquid templates that regenerate at build time, so edits to
  the text are picked up automatically.
- `esushruta_data_v2/` — the raw scraped source data (kept for
  reproducibility; excluded from the built site).
- `build_site_v2.py` — regenerates the chapter files and
  `_data/sthanas.yml` from `esushruta_data_v2/`. Needed only if the
  source data changes. It also applies the ISO→IAST conversion, so that
  is no longer a separate step.
- `esushruta_data/`, `build_site.py` — superseded v1 data and builder,
  kept only as a fallback; safe to delete.

## Local preview

```
bundle install
bundle exec jekyll serve
```

Then open <http://localhost:4000/eSushruta/>.

## Deploying

Push to `main`; GitHub Pages builds it with the `github-pages` gem pinned
in the `Gemfile`. No plugins beyond Jekyll's built-ins are used.
`baseurl` is set to `/eSushruta` for the project-page URL.

## TEI download

The home page offers the complete text as two unified TEI P5 files, in
`assets/tei/`: root text only (`*-mula.xml`) and root text with commentary
(`*-full.xml`). They are generated from the chapter files by
`build_tei.py`. After any change to the text, regenerate and re-validate:

    python3 build_tei.py --validate path/to/tei_all.rng

(`pip install jingtrang` provides the validator; `tei_all.rng` is in the
TEI release at https://github.com/TEIC/TEI/releases.)
