---
layout: default
title: About
permalink: /about/
---
<div class="prose">

# About this site

This site presents the **Suśrutasaṃhitā**, with the commentaries of
Ḍalhaṇa (*Nibandhasaṅgraha*) and, where present, Gayadāsa
(*Nyāyacandrikā*), in IAST (romanized, diacritic) transliteration.

## Source

The text and its transliteration are drawn from the
[NIIMH e-Samhita](http://niimh.res.in/ebooks/esushruta/), a project of the
National Institute of Indian Medical Heritage (NIIMH), part of the Central
Council for Research in Ayurvedic Sciences (CCRAS), Government of India.
This site is a static, IAST-only mirror of that resource's Suśrutasaṃhitā
text, restructured for offline reading and hosting.

## How it was made

The original site serves its text through a form-driven interface backed
by client-side JavaScript, rather than through static, linkable pages. Its
content was extracted with a headless browser (chapter by chapter, in
"full chapter" mode) and converted to this static Jekyll site. The
extraction and conversion approach was checked chapter by chapter against
the number of word-level text nodes actually rendered, to catch any
silently dropped content.

## Known limitations

- Only the IAST (diacritical) rendering is included here; the original
  site also offers Devanagari and several other Indic scripts.
- Only "full chapter" view was captured; the original site's per-passage
  (sub-chapter) navigation is not reproduced.
- The root text, commentary, and footnotes/variant readings for each
  adhyāya are presented as continuous running text, without the distinct
  visual separation (e.g. by font or indent) the original site gives
  them, since that structural markup was not preserved during extraction.
- This is a first-pass conversion. If you notice missing or garbled
  passages, please compare against the [original
  site](http://niimh.res.in/ebooks/esushruta/) and open an issue.

</div>
