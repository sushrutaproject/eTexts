# Running the word spacing on one text (instructions for a Claude Code session)

Paste this into a new Claude Code session opened in the eTexts repository, with
the text named on the first line, e.g.

    Do the word spacing and verse tagging for eHrdaya, following tools/spacing/SESSION.md.

The procedure has been run on the Śārṅgadharasaṃhitā (PR #2), the Mādhavanidāna
(PR #3) and the Carakasaṃhitā (PR #4). `tools/spacing/README.md` explains the
tools; `tools/spacing/pipeline.py` runs every step except the spacing itself,
which is done by agents. Work in your scratchpad directory (below: `$W`), never
inside the repository.

## 0. Before anything: cost

The spacing is done by one Opus agent per piece of about 28,000 characters; an
agent uses about 100–150 thousand tokens. The Mādhavanidāna (54 pieces) took about
6 million tokens, the Carakasaṃhitā (125 pieces) about 14 million, and ran into
the 5-hour usage limit three times. **After step 2, tell the user the number of
pieces and the token estimate that `pipeline.py prepare` prints, and wait for a
go-ahead before launching any agent.** Offer to spread the work over several usage
windows if the text is large.

## 1. Branch

    git fetch origin && git checkout -b <id>-spacing origin/main

(`<id>` = the folder name without the leading e, lower case, e.g. `hrdaya-spacing`.)
Check the TEI file has no `<lg>` yet and no "Word spaces have been added" note in
its `editorialDecl`: if it has, the text was done already (eSangraha was the
first, done before these tools); stop and tell the user.

## 2. Prepare

    python3 tools/spacing/pipeline.py prepare <folder>/<file>.xml $W --title "<work, with its commentaries>"

e.g. `--title "Vāgbhaṭa's Aṣṭāṅgahṛdaya, with Aruṇadatta's Sarvāṅgasundarā and Hemādri's Āyurvedarasāyana"`.
Read `$W/INSTRUCTIONS.md` once; add anything particular to this text under
"Conventions" (for example a commentary that uses an unusual siglum).
Report the estimate to the user (step 0).

## 3. Spacing agents

Launch general-purpose agents on Opus (`model: "opus"`), in the background, 12 at
a time, each with the prompt that

    python3 tools/spacing/pipeline.py prompt $W 001 002 …

prints for its piece. Each agent writes `out/NNN.xml` and `reports/NNN.txt` and
replies with one line (`NNN done, N spaces, check ok`). When one finishes, start
the next piece, so that about 12 run at a time. Do not read the agents' transcript
files.

- Keep track of progress with `pipeline.py status $W`.
- If agents fail with a usage-limit error ("You've hit your 5-hour limit"), their
  work so far is saved: when the limit resets (or the user says it has), resume
  each one with SendMessage to its agent id ("Continue piece NNN from where you
  stopped: …"), do not start new agents for those pieces. Tell the user plainly
  what happened and how much is left.
- If an agent reports something odd (a mix-up with another piece, a convention
  question that recurs), re-check those pieces with `check.py $W NNN` and, for a
  new convention, add it to `$W/INSTRUCTIONS.md` for the pieces still to come.
- A very low space count is normal for a very short piece; compare with the
  piece size in `$W/pieces.txt`.

## 4. Review

    python3 tools/spacing/pipeline.py review $W

This assembles the pieces, adds the avagraha spaces, and runs the consistency
check. It drafts `$W/rules.txt` (splits to make uniform) and writes
`$W/undecided.txt` and `$W/sweep.txt`. Then:

- read `rules.txt` line by line and delete anything that is not clearly right
  (a context-dependent tat/tad + noun, a compound, a technical term such as
  punarukta, which stays as the agents left it);
- read `sweep.txt` (candidate case or verb endings run into the next word; many
  are false: compounds such as dantyariṣṭa, words such as sthairya, pratyeka) and
  copy the real ones into `rules.txt`;
- look through `undecided.txt`; add a rule only where one form is clearly an
  error; the rest stays for the editor and is listed in the flagged file.

## 5. Proofread a sample

    python3 tools/spacing/pipeline.py sample $W 40

Read the passages; note misses. If a kind of miss recurs, look for it across the
text (a regex over `$W/spaced2.xml`) and add rules. Report the result honestly in
the PR (number of passages read, errors found, rough rate).

## 6. Finish

    python3 tools/spacing/pipeline.py finish $W --rng <path to tei_all.rng>

(`tei_all.rng` from https://tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng,
or a local copy, e.g. under `~/.lemminx/cache/`.) This applies `rules.txt`, tags the
verses, verifies the result against the original, writes the TEI file with notes
in its `editorialDecl` and `revisionDesc`, and writes `<name>-flagged.txt` and
`<name>-prose.txt` beside it. It refuses to write anything if verify.py fails.

Then read the head of the flagged file and edit the "Policy questions" section
into sentences the editor can answer (the counts are filled in). Look at the
prose file: it should hold headings, colophons, source references, real prose
and only a few half-verses that do not scan; if many verses are there, find out
why before going on.

## 7. Build and look

The repository's Gemfile pins Jekyll 3.10. If that is not installed, use a
separate Gemfile in the scratchpad containing `gem "jekyll", "4.3.2"`,
`gem "kramdown-parser-gfm"` and `gem "webrick"`:

    BUNDLE_GEMFILE=$W/../gem/Gemfile bundle exec ruby build.rb

Serve `_site` (e.g. `python3 -m http.server` from a folder holding a link
`eTexts -> <repo>/_site`) and take screenshots of two or three chapters: one with
root-text verses, one with verse split by commentary, one with prose. Send them to
the user.

## 8. Commit and PR

Commit the TEI file and the two text files. Then

    python3 tools/spacing/pipeline.py prbody $W

writes `$W/pr.md` (kept under GitHub's 65,536-character limit; long flagged lists
are cut there, not in the file). Fill in the two FILL IN lines, push, and
`gh pr create --body-file $W/pr.md`. In the final message give the user the
numbers, the policy questions and the PR link.
