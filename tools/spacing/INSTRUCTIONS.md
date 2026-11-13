# Word-spacing task (Sanskrit, IAST, TEI/XML)

You add word spaces to a piece of {WORK}: root text (`<ab type="mula">`) and
commentary (`<ab type="commentary">`) alike.

- Input:  `{DIR}/in/NNN.xml`  (whole lines of the TEI file: one `<ab>` or `<head>` element per line)
- Output: `{DIR}/out/NNN.xml` (the same lines, word spaces added)

Read only your own input file(s) and this file. Do not open other pieces, other
agents' output, or the TEI file itself.

The owner's words: put spaces between words (not inside compounds), e.g. "ityeke" →
"ity eke". Not full lemmatization: separate words joined by consonants at the
junction (words that would be joined into a conjunct consonant in Devanāgarī).

## Rules

1. Only ADD spaces. Never change, add or delete a letter, punctuation mark, daṇḍa
   (`|`, `||`), number, hyphen, dash, quotation mark, apostrophe/avagraha, bracket,
   or any XML markup or attribute. Whitespace-stripped output must equal the
   whitespace-stripped input. Do not add spaces inside tags, and do not add or tidy
   spaces around daṇḍas, numbers or punctuation (`smṛtaḥ||12||` stays as it is).
   Leave existing spaces exactly as they are.
2. Keep sandhi forms; only insert the space: "tasminneva" → "tasminn eva",
   "tacchāstram" → "tac chāstram", "ityeke" → "ity eke", "rāmaśca" → "rāmaś ca",
   "dadyādbhavatāṃ" → "dadyād bhavatāṃ", "vakṣyāmyanativistarān" → "vakṣyāmy
   anativistarān". No pausa restoration.
3. Do NOT split where two vowels fused into one ("cāsya", "tathaiva",
   "nātyuṣṇaḥ", "evālavaṇaṃ", "smāhur", "rasāścaiva" → "rasāś caiva"). If a word
   has both a fusion and a consonant junction, split only at the consonant junction.
4. Do NOT split inside compounds, however long (drug lists, disease lists,
   dvandvas, bahuvrīhis, tatpuruṣas, avyayībhāvas such as yathāsvaṃ, yathāyatham,
   yathārhaṃ). Names of preparations (bṛhatkaṭphalādicūrṇam) are compounds.
5. samyak, kiñcit, punar, sadyas, muhur and the like: split them off when they
   qualify a verb, gerund, participle or adjective as a separate word ("samyak
   prayuktaḥ", "kiñcid uṣṇā"); keep them joined as the first member of a nominal
   compound ("samyagdhūmapīta…"). īṣat- stays compounded. tat/tad: split as a
   pronoun ("tat siddhaṃ", that, once cooked), joined as a compound member
   ("tatsiddhaṃ tailaṃ", oil cooked with those).
6. Split two separate words that the e-text runs together with no sandhi at all
   ("unmādetūro" → "unmāde tūro", "kūrcārajjavas" → "kūrcā rajjavas" when they are
   separate list items), but only when they are clearly separate words.
7. The owner's decisions: repeated words are split ("punaḥ punaḥ", "muhur muhuḥ",
   "śanaiḥ śanaiḥ", "ahar ahaḥ"), except where the vowels fuse ("alpālpam",
   "ekaika"); "tadyathā" → "tad yathā"; "ityādi" stays joined; a missing avagraha
   ("jātopi", "loke sminn") is left joined as it is; typos are left uncorrected.
8. Particles and connectives are separate words: "tathā ca", "tathā hi", "na tu",
   "na hi", "na ca", "api ca", "yad vā", "kiṃ ca" (also "tathāhy uktam" → "tathā hy
   uktam"). Kept joined: "ityādi", "kintu", "athavā", "itas tataḥ" only where the
   text spaces it.
9. Do not add a space before an avagraha/apostrophe ("sarve'pi", "khaṇḍo'yaṃ" stay as
   they are); that is decided for the whole text in one pass afterwards.
10. Leave alone: `<note n="§K"/>` (placeholders for editorial notes, which are not
   spaced), `<label type="siglum">…</label>`, attribute values. You may add a space
   in the text directly before or after a tag when a word boundary falls there.

## Method

Copy the input to `out/`, then add spaces with a Python script of explicit,
context-specific string replacements applied to each line (e.g. a list of
`(old, new)` pairs where `old` is long enough to be unique or every hit is meant).
Do not apply blind global token rules without checking each hit. Read every line
and decide, root text and commentary, verse and prose alike. Very long lines
can be handled by splitting the line text on spaces, mapping tokens, and rejoining
with the original spaces.

Verify with

    python3 {TOOLS}/check.py {DIR} NNN

Every piece must report `letters-ok xml-ok tags-ok lines-ok`. Fix until it does.

## Final report (under 150 words)

Per piece: spaces added and the check result, plus at most 5 genuinely uncertain
segmentations, each as `NNN l.LINE: <form as you left it> — <the doubt>`
(LINE = line number within your piece file).
