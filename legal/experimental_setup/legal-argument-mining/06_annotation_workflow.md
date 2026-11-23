# 06 — Step-by-step workflow for a directory of `.txt` files

Goal: for every `X.txt` in the input directory produce `X.am.json` (schema in `05_output_schema.md`).
Work **one document at a time**, and make the process **resumable**: skip any file whose output already exists and validates.

## Step 0 — Set up
```bash
IN=<input dir>            # directory with the .txt files
OUT=argument_mining_output
WORK=argument_mining_work
mkdir -p $OUT $WORK
python3 <skill>/scripts/am_tools.py segment $IN $WORK     # writes $WORK/<stem>.units.txt, prints one status line per file
```
(Windows: use `python` or `py` instead of `python3`. The script forces UTF-8 output itself; if a console still garbles
characters set `PYTHONUTF8=1`.)

**Read the status line for every file before annotating it.** It tells you, in one line: number of characters/units/paragraphs,
where the Law section starts (`scope=law-heading@…`), where the tail starts, and any of: `CRLF->LF` (fine), `REPAIRED n mojibake`
(fine — the text was cleaned), `TRUNCATED`, `SCOPE UNCERTAIN`, `WARNING: only n paragraph(s)… flattened`.
Anything in capitals is explained in `07_edge_cases.md`. If Python is unavailable, say so in the run report and do not
claim exact offsets.

## Step 1 — Read the unit table (not the raw file)
Open `$WORK/<stem>.units.txt`. Each line is:
```
u211 p100 ¶44 [30890-31091) | As to the general policy in relation to the disclosure …
u212 p100  [31092-31453) | The Government drew attention to paragraph 3 thereof …
```
`u` = unit id (sentence) — **this is the number you will use**; `p` = paragraph block (a numbered judgment paragraph with its
continuation lines — spans may not leave it); `¶44` = the judgment's own paragraph number (first unit only); `[s-e)` = exact
character range (information only; you never copy it); then flags: **`H`** heading (never annotate), **`Q`** inside a
quotation (usually the quoted provision/judgment → no span), **`L`** low-priority section (Art. 41/50 just satisfaction, costs, default interest → no span by
default), **`T`** truncated final unit.
Header lines (`# SCOPE`, `# TAIL`, `# WARNING`) say what is hidden: units before `THE LAW` (facts/procedure) and the operative
part + separate opinions at the end are hidden. If no `THE LAW` heading was found, **all** units are shown with a warning and
you decide the start (`07_edge_cases.md` §1).

For long documents (> ~250 units) work in **chunks of whole paragraphs (~80–120 units)**, and always re-read the last
2 paragraphs of the previous chunk plus the nearest section heading for context.

## Step 2 — Map the structure (cheap, once per document)
Note headings (`H` lines) and, for each section, which **stage** it is (`02_label_descriptions.md` §1). A typical ECHR "The Law" part:

1. *Alleged violation of Article N* — scope of the complaint, applicability, existence of an interference → `APP` for every speaker.
2. *Justification* (only for qualified rights, headings such as *In accordance with the law / Legitimate aim / Necessary in a democratic society /
   Compliance with paragraph 2*, or a "fair balance" test) → `LEG` → `PUR` → `NEC` for **every speaker**; standalone general doctrine → `PRE`;
   the Court's closing sentence → `DEC`.
3. *Other complaints* → `APP`, with `DEC` for an actual finding.
4. *Application of Article 41 / 50 (just satisfaction)* and *Costs and expenses* (flag `L`) — **not annotated by default**.
5. *Operative provisions* ("FOR THESE REASONS, THE COURT…") and *separate opinions*: **hidden, not annotated**.

The Commission's opinion, the Government's and the applicant's submissions are not a stage of their own: they take the label of the stage they speak to.

## Step 3 — Pass 1: spans + type + actor (merged)
For each paragraph, in order:
1. Decide for each unit: argument or `O` (`01_task_definition.md` §4).
2. Group consecutive argument units into spans: new span whenever the **speaker (actor) or the label changes** (`01_task_definition.md` §5).
3. For each span choose `type` (`02_label_descriptions.md`: stage first, then the strict overrides)
   and `actor` (`03_actor_labels.md`).
4. Express the span as a **unit range**: first unit through last unit, e.g. `"u7-u8"` (or `"u9"` for one sentence).
   All units of a span must share one paragraph `p`.
5. Append the row to `$WORK/<stem>.jsonl`: `[id,"u7-u8","TYPE","ACTOR"]` (ids ascending). **Do not write character offsets** —
   `build` computes them.
6. **Only if a single sentence holds two different moves** (different type or actor on either side of a clause break),
   write two rows for that unit and add an anchor object to each: `[3,"u12","LEG","APPL",{"end_before":", but"}]` and
   `[4,"u12","LEG","ECHR",{"start_at":"the Court finds"}]`. The anchor is a short phrase copied exactly from the unit text
   and must occur once in that unit (`05_output_schema.md`).

Calibration reminders:
* Expect most spans to be `APP` (~57 %), then `NEC`, `LEG`, `DEC`, `PRE`, `PUR`. A judgment with only `APP`/`DEC` spans is suspicious
  if it contains a justification test (paragraph-2 / fair-balance headings).
* `TXT`, `MOA`, `DIS`, `NCP` need their strict trigger (`02_label_descriptions.md` §2); `TEL`, `SYS`, `CMP`, `HIS`, `SUI`, `OVR`: do not use.
* If a unit is borderline between `O` and an argument, include it only if it passes the "does legal work" test; boilerplate stays out.
* Don't produce one-sentence spans for every sentence when they share type and actor — merge them.
* **Work paragraph by paragraph, not sentence by sentence.** For each numbered paragraph ask: *who is speaking?* (Court / Commission /
  Government / applicant / third party) and *what is the move?* One speaker + one move = one span for the whole paragraph (all its
  lines). Split only at a change of speaker or a real change of move.
* Target size of the output: about **1.5 spans per 1000 characters of the annotatable Law section (≈ 15–40 per judgment)**. If your list is twice that,
  merge; if it is half, check you did not skip paragraphs (`validate` prints these numbers).
* Don't annotate: headings, `Q` units, the hidden tail, `L` sections, and — in the Law section — nothing else without a reason:
  the default for a paragraph of reasoning, submissions or the Commission's opinion is **to annotate it** (usually `APP`).

## Step 4 — Pass 2 (optional): relations
Only if the run mode includes relations (see `SKILL.md`). Follow `04_relations.md` §5; append rows
`[from,to,"S|A|E"]` to the same `.jsonl`.

## Step 5 — Build and validate
```bash
python3 <skill>/scripts/am_tools.py build $WORK/<stem>.jsonl $IN/<stem>.txt $OUT/<stem>.am.json
python3 <skill>/scripts/am_tools.py validate $IN/<stem>.txt $OUT/<stem>.am.json --show
```
`build` itself rejects bad unit ranges and anchors with line numbers (and writes nothing) — fix those lines first.
Then fix every **ERROR** `validate` reports (edit the `.jsonl`, rebuild). Read the `--show` listing as a sanity check: does each span's text start and end where an
argument starts and ends, and does the label fit the text? Review every **WARN**; keep it if you can justify it.

## Step 6 — Self-check (30 seconds per document)
- [ ] Every span lies after `THE LAW`, before the tail, outside `L` sections (Art. 41/50, costs), and inside one paragraph block.
- [ ] Lead-in sentences ("The applicant alleges a breach of Article 8, which reads:") have an `APP` span; the quotation itself does not.
- [ ] Inside a justification test every speaker's span carries the step label (`LEG`/`PUR`/`NEC`); outside it the same speaker is `APP`.
- [ ] `DEC` only for the Court's own short closing holdings (≈ 7 % of spans); "no need to examine" is `APP`.
- [ ] Paragraph numbers/headings not inside spans.
- [ ] Party-reported arguments carry the **party's** actor, not `ECHR`.
- [ ] Each section ends with a `DEC` span where the Court states its own conclusion.
- [ ] `APP` isn't swallowing proportionality passages inside the justification test.
- [ ] Bare citations inside applying/balancing sentences were *not* split off as `PRE`.
- [ ] No `TEL/SYS/CMP/HIS/SUI`; `TXT/MOA/DIS` only with their trigger.

## Step 7 — Run report
After the last file run `python3 <skill>/scripts/am_tools.py batch-validate $IN $OUT` and write `$OUT/_run_report.md`:
files processed / skipped / failed, total spans per type (from the validator stats), the mode used, any assumptions (e.g. non-ECHR actor mapping, missing `THE LAW` headings), and
files that need human review.

## Step 8 — Optional: score against a gold file
If the user supplies gold annotations (corpus JSON with `annotations: [{start,end,label}]`):
```bash
python3 <skill>/scripts/eval_gold.py gold.json $OUT/<stem>.am.json $IN/<stem>.txt --diagnose --sweep
```
It prints span and span+label P/R/F1 at IoU ≥ 0.5, a per-label table, and with `--diagnose` lists every predicted span as
matched / near-miss / **not in gold** and every gold span nobody matched — use it to see *why* precision or recall is low (typically:
spans in the tail, over-splitting, `APP`↔`NEC`). If an older output was made on raw CRLF text it is converted automatically.

## Efficiency rules (to keep tokens low)
* Never echo the document text in your answer or in the output file.
* Never write explanations into the JSON. Reasoning stays in your head/scratch.
* Don't re-read a document once its output validated.
* For many files, process them sequentially; keep only the current document's unit table in context.

## Worked example (the test case shipped with the skill: `examples/`)

Unit table excerpt (toy example; its tiny spans trigger the over-splitting WARNs on purpose-built 1,145-character text — real judgments should follow `08_calibration.md`):
```
u7  p7  [258-389) | In the applicants' submission, the refusal to grant a new residence permit … infringed Article 8 of the Convention.
u8  p7  [390-463) | They stressed that regular contact with his daughter had been maintained.
u9  p8  [468-522) | The Government accepted that Article 8 was applicable.
u10 p8  [523-573) | It is not disputed that there was an interference.
u11 p9  [578-789) | The Court reiterates that the Contracting States enjoy a certain margin of appreciation … (see Abdulaziz …, § 67).
u12 p9  [790-884) | Here, the expulsion order had a basis in the Aliens Act, so it was in accordance with the law.
u13 p10 [889-976) | The Court is not convinced that the interference was necessary in a democratic society.
u14 p10 [977-1087)| A fair balance was not struck between the interests of the community and the applicants' right to family life.
u15 p11 [1092-1144)| There has accordingly been a violation of Article 8.
```
Reasoning → scratch rows (`examples/case1.jsonl`):
* u7+u8: applicants' argument on how Article 8 applies to their facts → `[1,"u7-u8","APP","APPL"]` (same type & actor → one span).
* u9 vs u10: the Government's acceptance that the Article applies is a party position in the scope stage → `[2,"u9","APP","STATE"]`; u10 is the Court's own stand-alone "not disputed" sentence → `[3,"u10","NCP","ECHR"]`.
* u11: a general statement about the margin, with a citation → `[4,"u11","MOA","ECHR"]` (main point: width of discretion; the citation does not make it `PRE`).
* u12: tests basis in domestic law → `[5,"u12","LEG","ECHR"]`.
* u13+u14: "necessary in a democratic society", "fair balance" → `[6,"u13-u14","NEC","ECHR"]`.
* u15: bottom-line holding → `[7,"u15","DEC","ECHR"]`.

`build` turns these into the final `examples/case1.am.json`, e.g. row 1 becomes `[1,258,463,"APP","APPL"]`.

### Mid-sentence example

Unit `u2` = *"The applicant argued that the law was unclear, but the Court finds that it was foreseeable."*
Two actors in one sentence, so:
```
[1,"u2","LEG","APPL",{"end_before":", but"}]
[2,"u2","LEG","ECHR",{"start_at":"the Court finds"}]
```
