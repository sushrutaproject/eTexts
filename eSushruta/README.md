# e-Suśruta

A static Jekyll reading edition of the Suśrutasaṃhitā (with Ḍalhaṇa's and,
where present, Gayadāsa's commentaries), in IAST. Content and
transliteration are drawn from the [NIIMH
e-Samhita](http://niimh.res.in/ebooks/esushruta/); see `about.md` for
provenance and known limitations.

## Structure

- `_sutrasthana/`, `_nidanasthana/`, `_sharirasthana/`, `_cikitsasthana/`,
  `_kalpasthana/`, `_uttaratantra/` -- one Jekyll collection per sthāna,
  one file per adhyāya (chapter).
- `_data/sthanas.yml` -- display names, subtitles, and chapter counts used
  throughout the templates.
- `_layouts/`, `_includes/`, `assets/css/style.css` -- site design.
- `esushruta_data/` -- the raw scraped JSON this site was generated from
  (kept for reproducibility; excluded from the built site itself).
- `build_site.py` -- regenerates the `_<sthana>/*.html` files and
  `_data/sthanas.yml` from `esushruta_data/*.json`. Only needed again if
  the source data changes.

## Local preview

Requires Ruby + Bundler.

```
bundle install
bundle exec jekyll serve
```

Then open <http://localhost:4000>.

## Deploying to GitHub Pages

1. Push this folder to a new GitHub repository.
2. In the repo's Settings -> Pages, set the source to the branch you
   pushed (e.g. `main`) and the root folder.
3. GitHub Pages will build it automatically using the `github-pages` gem
   pinned in the `Gemfile` -- no extra configuration needed, since
   everything here uses only Jekyll's built-in features (no custom
   plugins) that GitHub Pages supports natively.
4. If you're publishing at `https://<user>.github.io/<repo>/` (a project
   page, not a user/org page), set `baseurl: "/<repo>"` in `_config.yml`
   first, or links between pages will point to the wrong path.
