# Word spacing and verse tagging of the e-texts

Tools used to add word spaces and `<lg>`/`<l>` verse markup to the TEI master
files (first the Aṣṭāṅgasaṅgraha, then the Śārṅgadharasaṃhitā). They work on
the files of this repository as they are made: one `<ab>` (or `<head>`) per line
inside `<body>`.

The spacing itself is done by language-model agents following
[INSTRUCTIONS.md](INSTRUCTIONS.md) (the rules agreed with the editor); the
scripts cut the file into pieces, check every piece, put the file together
again, and check the whole. Verse tagging is done by a script, by metre.

| file | what it does |
|---|---|
| `INSTRUCTIONS.md` | the spacing rules and method, given to every agent (template; `prepare.py` fills in the paths) |
| `prepare.py` | cuts the TEI into pieces of ~28k characters of text (whole chapters; long chapters cut at a line), masks the notes |
| `check.py` | checks one agent's output: only spaces added, tags identical, well-formed, same lines |
| `assemble.py` | puts the spaced pieces back into the file, restores the notes |
| `avagraha.py` | `te'pi` → `te 'pi` throughout, in one uniform pass (`ā'` stays joined) |
| `consistency.py` | strings joined in one place and split elsewhere (`--orig`: count only added spaces); `--particles` for joined `yacca`, `tadeva`… |
| `fix.py` | applies a list of consistency fixes (`tathāhi => tathā hi`, `tad anu => tadanu`) to whole tokens outside notes |
| `verse.py`, `metre.py` | metre-based verse tagging of the root text (`--commentary`: verses in the commentaries too) |
| `verify.py` | whole-file check against the original: letters, tags, notes, xml:ids, well-formed, valid |

## Running it on another text (e.g. eMadhava)

Work outside the repository, e.g. `W=/tmp/madhava`. Everything below is run
from the repository root.

1. Cut the file into pieces:

       python3 tools/spacing/prepare.py eMadhava/madhavanidana-full.xml $W --work-title "Mādhava's Mādhavanidāna, with the Madhukośa and Ātaṅkadarpaṇa"

   It lists the pieces (about 1 per 28,000 characters of text; `--target` changes
   that) and writes `$W/INSTRUCTIONS.md`. Notes are masked as `<note n="§K"/>`
   (the owner decided notes are not spaced); `--keep-notes` leaves them in.
   Look at `$W/INSTRUCTIONS.md` and add anything particular to the text.

2. Run one agent per piece, about 8 at a time (Claude Code: general-purpose
   subagents on Opus, in the background), each with the prompt

       Read $W/INSTRUCTIONS.md and carry it out for piece NNN (in/NNN.xml →
       out/NNN.xml in that work directory). Follow the rules exactly; run
       check.py until it passes; end with the short report the instructions ask for.

   Collect the uncertain spots each agent reports into `$W/flagged.txt`.
   For the Śārṅgadharasaṃhitā (56 pieces, 1.46 M characters of text outside the
   notes) an agent took 2–7 minutes and 80–150k tokens per piece, 6.3 M tokens
   in all; with 8–12 agents at a time the whole text took about two hours.
   When agents disagree on a convention, add it to the instructions for the
   remaining pieces and align the finished ones in step 4.

3. Check and reassemble:

       python3 tools/spacing/check.py $W all
       python3 tools/spacing/assemble.py $W $W/spaced.xml
       python3 tools/spacing/avagraha.py $W/spaced.xml $W/spaced2.xml

4. Consistency:

       python3 tools/spacing/consistency.py $W/spaced2.xml --orig eMadhava/madhavanidana-full.xml --top 200
       python3 tools/spacing/consistency.py $W/spaced2.xml --particles

   Fix only clear cases, as rules in a file for `fix.py`
   (`python3 tools/spacing/fix.py $W/spaced2.xml $W/spaced3.xml rules.txt`; a join
   rule may only remove a space that was added: `verify.py` catches the others).
   Context-dependent cases (tat/tad + noun, rule 5) stay as the agents left them.
   Keep new policy questions for the editor. The Śārṅgadhara rules are listed at
   the end of `eSharngadhara/sarngadharasamhita-flagged.txt`.

5. Verses:

       python3 tools/spacing/verse.py $W/spaced2.xml $W/final.xml --commentary --report $W/prose.txt

   `prose.txt` lists the root-text segments left as prose: read it to see that
   only headings, colophons and real prose are there. Root text: every half-verse
   (up to `|` or `|| n ||`) that scans becomes an `<l>`, the half-verses of a
   verse that stand together in one `<ab>` or `<seg>` an `<lg>`; a verse broken by
   commentary becomes `<lg part="I">` … `<lg part="F">` (a single pāda split off
   is `<l part="I">` / `<l part="F">`). The reading pages indent the first line of
   a continued verse. Commentaries (`--commentary`): only runs of two or more
   half-verses that scan strictly.

6. Verify against the original (the file as committed before the work) and validate:

       python3 tools/spacing/verify.py eMadhava/madhavanidana-full.xml $W/final.xml --rng tei_all.rng

   (`tei_all.rng` from https://tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng),
   copy `final.xml` over the TEI file, add a note to its `editorialDecl` and
   `revisionDesc` (see the Śārṅgadhara file), build (`ruby build.rb`, see the main
   README) and look at a few chapters. Put the flagged spots and `prose.txt`
   beside the TEI file (`<name>-flagged.txt`, `<name>-prose.txt`).

7. Proofread a random sample of lines and report the error rate.
