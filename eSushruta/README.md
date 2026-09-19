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
