---
layout: default
title: About
permalink: /about/
---
<div class="prose">

# About this site

This site presents the **Suśrutasaṃhitā**, a Sanskrit treatise on medicine
and surgery, together with **Ḍalhaṇa's** commentary on it, the
*Nibandhasaṅgraha*, in IAST (romanized, diacritic) transliteration.

## The two texts

The root text and the commentary are the work of different authors,
separated by many centuries, and the display distinguishes them: the
Suśrutasaṃhitā is set in larger type at the full measure, while Ḍalhaṇa's
commentary is set smaller and indented behind a rule. The commentary can
be hidden entirely with the control at the head of each chapter, leaving
the root text to be read continuously.

This division is not editorial guesswork on this site's part: the NIIMH
source marks every word of the text as belonging to one register or the
other, and that distinction has been carried through directly. The
judgement about where the boundaries fall is NIIMH's.

Other commentators — Cakrapāṇidatta, Gayadāsa, Bhāskara, Hāraṇacandra —
are frequently named, but as **citations within** Ḍalhaṇa's commentary.
Their own commentaries are not separate layers in this text.

The notes at the foot of each chapter (*pāṭhāntarāḥ*) record variant
readings and comments from the source edition.

## Source

The text and its transliteration are drawn from the
[NIIMH e-Samhita](http://niimh.res.in/ebooks/esushruta/), a project of the
National Institute of Indian Medical Heritage (NIIMH), part of the Central
Council for Research in Ayurvedic Sciences (CCRAS), Government of India.
This site is a static, IAST-only mirror of that resource's Suśrutasaṃhitā
text, restructured for offline reading, searching and hosting.

## How it was made

The original site serves its text through a form-driven interface backed
by client-side JavaScript, rather than through static, linkable pages. Its
content was extracted with a headless browser (chapter by chapter, in
"full chapter" mode) and converted to this static Jekyll site. The
extraction was checked chapter by chapter against the number of
word-level text nodes actually rendered, to catch silently dropped
content, and every footnote reference was verified to have a matching
note.

## Known limitations

- Only the IAST (diacritical) rendering is included here; the original
  site also offers Devanagari and several other Indic scripts.
- Only "full chapter" view was captured; the original site's per-passage
  (sub-chapter) navigation is not reproduced.
- Verse and chapter divisions follow the source edition.
- If you notice missing or garbled passages, please compare against the
  [original site](http://niimh.res.in/ebooks/esushruta/) and open an
  issue.

</div>
