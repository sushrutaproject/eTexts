# e-Mādhavanidāna

A static Jekyll reading edition of the **Mādhavanidāna**, a Sanskrit
compendium on the diagnosis of disease attributed to Mādhavakara, with
the **Madhukośa** and **Ātaṅkadarpaṇa** commentaries, in IAST. Content
drawn from the [NIIMH e-Samhita](http://niimh.res.in/ebooks/madhavanidana/);
see `about.md` for provenance and limitations.

## Structure

- `_nidanas/` — one Jekyll collection, one file per adhyāya (this text has
  no sthāna division, unlike the Suśrutasaṃhitā or Carakasaṃhitā). Root
  text is in `<div class="mula">`, the two commentaries in
  `<div class="bhasya bhasya-madhukosha">` / `<div class="bhasya bhasya-atankadarpana">`,
  variant readings in `<section class="notes">`.
- `_layouts/`, `_includes/`, `assets/css/style.css` — design, the
  commentary show/hide control, and search-hit highlighting.
- `search.html` + `search-index/nidanas.json` — client-side search. The
  index file is a Liquid template that regenerates at build time, so
  edits to the text are picked up automatically.
- `madhavanidana_data/` — the raw scraped source data (kept for
  reproducibility; excluded from the built site).
- `build_madhavanidana_site.py` — regenerates `_nidanas/*.html` from
  `madhavanidana_data/madhavanidana.json`. Needed only if the source data
  changes. It applies the ISO→IAST conversion itself.

## Local preview

```
bundle install
bundle exec jekyll serve
```

## Deploying

Push to `main`; GitHub Pages builds it with the `github-pages` gem pinned
in the `Gemfile`. **Before pushing**, set `baseurl` in `_config.yml` to
`/YourRepoName` if this is a project-page repo (`username.github.io/RepoName`)
— left blank, every CSS/JS/search-index link 404s and the site renders as
unstyled text. Leave it blank only for a user/org page repo
(`username.github.io`).

## Known open item

Adhyāyas 44 (bhagnanidāna) and 58 (nāsāroganidāna) currently have no
extracted text — confirmed empty across repeated scrape attempts, but not
yet confirmed by eye against the live NIIMH site. See `about.md`.

## TEI download

The home page offers the complete text as two unified TEI P5 files, in
`assets/tei/`: root text only (`*-mula.xml`) and root text with commentary
(`*-full.xml`). They are generated from the chapter files by
`build_tei.py`. After any change to the text, regenerate and re-validate:

    python3 build_tei.py --validate path/to/tei_all.rng

(`pip install jingtrang` provides the validator; `tei_all.rng` is in the
TEI release at https://github.com/TEIC/TEI/releases.)
