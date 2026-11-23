# 01 — Task definition: what "argument mining" means here

Read this first. It defines the problem, splits it into subtasks, and says exactly what counts as a span.

## 1. The problem in one paragraph

Given the plain text of a court decision, find every **argument span** (a contiguous stretch of text in which
somebody — the court or a party — advances a legal argument), say **what kind of legal argument** it is
(`type`), say **whose argument it is** (`actor`), and optionally say **how spans relate** to each other
(`relations`). Everything else in the text (facts, procedure, headings, paragraph numbers, quotations of
statutory text with no argumentative use) stays unannotated, which is the implicit label `O` ("outside").

This is **not** the generic "premise / claim" model. Legal argumentation has a rich typology
(textual interpretation, proportionality test steps, precedent, margin of appreciation, ...) and that typology
is the label set (see `02_label_descriptions.md`). A span is therefore always *typed*, never just "premise".

## 2. The subtasks

| # | Subtask | Question answered | Where it lives |
|---|---------|-------------------|----------------|
| A | **Component detection** (span finding) | *Where* does an argument start and end? | this file §3–§5 |
| B | **Component classification (type)** | *Which of the legal argument types is it?* | `02_label_descriptions.md` |
| C | **Component classification (actor)** | *Whose argument is it?* | `03_actor_labels.md` |
| D | **Relation mining** | *Which span supports / attacks / elaborates which?* | `04_relations.md` |

### Merging for end-to-end work (recommended)

* **Pass 1 = A + B + C merged.** For each span you emit `start, end, type, actor` in one go. Detecting a
  boundary and choosing its label are the same decision in practice: a boundary exists *because* the type or
  the actor changes (see §5). Doing them separately wastes tokens and introduces inconsistencies.
* **Pass 2 = D** is run afterwards on the finished span list (you reason over span ids + a compact view of the
  text, not over raw offsets). It is optional; do it only if the user/run mode asks for relations
  (`SKILL.md`, "run modes").

## 3. What is the unit of annotation?

A **span** is a contiguous character range `text[start:end]` such that:

1. **It carries one legal argument move** — one `type` and one `actor` hold for the *whole* span.
2. **It is flat and non-overlapping.** No nesting, no overlap, no gaps required. Two spans may touch
   (`end` of one == `start` of next) but never overlap.
3. **It never crosses a paragraph boundary.** Legal arguments in judgments rarely span paragraphs; the
   segmenter gives you paragraph ids (`p…`), so a span's units must all share one `p`. A *paragraph* here is a
   **numbered judgment paragraph including its continuation lines** (second sub-paragraph, quoted lines…), exactly
   as in the source judgment — so a span MAY run over a line break inside one numbered paragraph (e.g. a
   Government submission that continues on a second line is still one span).
4. **It is independent of sentence boundaries in principle, but aligned to them in practice.** The corpus
   this scheme comes from annotates token spans, so a span may start or end mid-sentence. Do this *only*
   when a single sentence clearly contains two different moves (e.g. a precedent statement followed after a
   semicolon by the application of it, or "The applicant argued X, but the Court finds Y"). In >90% of cases
   a span = one or more complete consecutive sentences (units). Mid-sentence cuts are written with an
   **anchor phrase** (`05_output_schema.md`), not with character numbers.
5. **It excludes**: the paragraph number (`22.`), headings, leading/trailing whitespace. The segmenter already
   places offsets after the paragraph number.
6. **Typical size**: one numbered paragraph or a few sentences; mean ≈ 570 characters, median ≈ 335. About 58 % of annotated paragraphs are
   covered by **one single span** from first to last word. A span of >2,500 chars or <25 chars deserves a second look (the validator warns).

## 4. When is a sentence an argument span, and when is it `O`?

Mark a sentence as part of a span when it **does legal work toward a legal conclusion**:

* states or applies a norm, an interpretive method, a test step, a precedent, a doctrine;
* reports a party's (or the Commission's / Chamber's) *legal* contention or reasoning;
* records a point of agreement between the parties that lets the court skip an issue;
* states the court's conclusion on an issue.

Leave it `O` (no span) when it is:

| Not an argument | Examples |
|---|---|
| Bare facts of the case / chronology | "On 12 March 2004 the applicant was arrested." |
| Procedural history | "The application was lodged on…", "The Chamber relinquished jurisdiction…" |
| Headings and numbering | "A. The applicant's submissions", "I. ALLEGED VIOLATION OF ARTICLE 8", "22." |
| The quoted text of a provision or judgment (units flagged `Q`) | "1. Everyone has the right to respect for his private and family life…" |
| Bare list of domestic/international legal materials in a "Relevant law" section | statute extracts, treaty extracts |
| Judge names, signatures, dates, costs boilerplate with no reasoning | "Done in English and French…" |
| Mere re-statement of what a party *claims happened* (facts), not what the law requires | "The applicant says he was beaten." — but see the note below |
| Just satisfaction (Art. 41/50) and costs | flagged `L`; skipped by default |

**Note on parties' submissions.** Submissions of parties that argue *how the law applies to the facts* are
spans (type usually `APP`, actor `APPL`/`STATE`). A party merely asserting a fact is `O`. When unsure inside a
"submissions" paragraph, ask: *is the sentence trying to persuade that a legal norm is (not) satisfied?* If yes → span.

**Lead-in sentences ARE spans.** The sentence that introduces a quotation by reporting a party's complaint or claim is
not part of the quotation: *"The applicant alleges a breach of Article 8 of the Convention, which is worded as follows:"*,
*"The applicant claimed just satisfaction under Article 50, which reads:"* → one short `APP` span (actor = the party);
the quoted provision after it is `O`. (The reference gold annotates these; skipping them is a missed span.)

**Facts inside the Law section.** Inside the Law section a sentence that restates facts *in order to apply or weigh a
norm* ("Out of forty-six contributors nineteen gave their consent and 65 out of 352 documents were released")
belongs to the surrounding argument span (`APP`/`NEC`). Only facts that are pure background with no evaluative link are `O`.
See `07_edge_cases.md` §5.

**Scope — where annotation starts and stops.**
* **Start:** the heading `THE LAW` / `AS TO THE LAW`. The segmenter hides everything before it (facts, procedure).
  No such heading → `07_edge_cases.md` §1.
* **Stop:** the operative part (`FOR THESE REASONS, THE COURT`) and everything after it (separate / dissenting
  opinions) are **not annotated** — the segmenter hides them (`--include-tail` shows them). Do not annotate the Court's
  operative "Holds that…" list as `DEC`.
* **Skip by default (flag `L`):** the whole *Application of Article 41 / 50 (just satisfaction)* section — claims, replies, the Court's reasoning on damage —
  and *Costs and expenses* / *Default interest*. In the reference annotations these sections are left unannotated in 7 of 10 judgments and never fully
  annotated, so annotating them costs precision. Annotate `L` units only if the user asks for full coverage.

## 5. Where do boundaries go? (span-finding rules)

Start a **new span** whenever *either* the `type` *or* the `actor` changes. Keep **one span** while both stay constant.

Concrete rules, in priority order:

1. **Change of actor** → split. "The Government submitted that … The applicant replied that …" are two spans.
2. **Change of argument type** → split, **when the change is a real change of move**. "The Court reiterates the
   principle … (PRE). In the present case the applicant was expelled without … (APP)" are two spans. But do **not**
   cut a coherent paragraph into sub-spans just because one sentence mentions "margin of appreciation", "fair balance",
   "legitimate aim" or cites a case (rule 4, and `02_label_descriptions.md` MOA/NEC). One paragraph of balancing
   reasoning is ONE `NEC` span; one paragraph of a party's argument is ONE span of that party.
3. **Same type, same actor, consecutive sentences → merge** into a single span, even across several
   sentences **and across line breaks inside the same numbered paragraph** (e.g. a three-sentence application of law to
   facts is one `APP` span; a Government argument that continues on a second line is still one span).
4. **Sentences that only add a citation or an example to the previous sentence's move are part of that
   span.** Do not create a one-line span for "(see Mamchur v. Ukraine, § 100)".
5. **Transition words** ("Accordingly,", "Moreover,", "Thus") belong to the span they introduce.
6. **Reported submissions** — the *actor* is the speaker whose argument is reproduced (`STATE`, `APPL`, `COMM`); the Court's own assessment starts where the Court takes its own position (`ECHR`).
   A paragraph that reports and then answers a submission in one span is `ECHR`. Full rules: `03_actor_labels.md`.
7. **Mid-sentence split only when unavoidable** (rule 4 of §3). Cut at a clause boundary (`;`, `, but`,
   `, whereas`), never inside a word; start the second span at the first non-space character.
8. **Interrupting parentheticals** stay inside the span.
9. When one sentence plausibly belongs to two types, pick the type that describes its **main function** (what
   the sentence is there to do), not the vocabulary it happens to contain. See `02_label_descriptions.md` §Disambiguation.
10. **Calibration targets** (the validator warns when you are far off): about **1.5 spans per 1000
    characters** of Law section (≈ 15–40 spans per judgment), mean span ≈ 570 characters, and roughly **75 %** of the Law
    section's text inside spans (the plain Law sections *before* just satisfaction are ≈ 90 % annotated). Twice as many spans as that means you are splitting sentence by sentence.
11. **Typical gold granularity:** one span per (numbered paragraph × speaker × stage-label). A paragraph with one voice and one
    label is one span (the whole paragraph, first word to last). It becomes two or more spans when the **speaker changes** (Court → Commission →
    Government → applicant) — even in the middle of a sentence ("…; the Government disagreed") — or when a stand-alone `PRE`, `NCP` or `DEC` sentence
    sits at its edge. A short `DEC` sentence is often cut off from the reasoning in front of it at "consequently / therefore / thus concludes".

## 5b. Span-detection tricks (from the annotation protocol, published error analyses and the 10 reference judgments)

**Protocol facts (the reference annotators' rules):** spans are flat, non-overlapping, one type + one actor each, never cross a paragraph, only the Law section is annotated; annotators were told that
arguments rarely extend beyond one paragraph; ECHR precedent citations that sit *inside* an `APP`/`NEC` span are **not** split off as `PRE`; spans are token-aligned and independent of sentences in principle,
but 96 % of reference boundaries fall on sentence boundaries.

**Procedure that works:**
1. **Work paragraph by paragraph.** Default = one span for the whole paragraph (first word after the number → final full stop). 58 % of annotated paragraphs are exactly that.
2. Then look for the **only five reasons to cut a paragraph** into more than one span:
   (a) the **speaker changes** (Court → Commission → Government → applicant), even mid-sentence at "but / whereas / while / and the Commission …";
   (b) a **stage change** that changes the label (principle → application only when the doctrine is a free-standing `PRE` sentence; scope → justification step);
   (c) a short **closing sentence** that is the Court's own finding (`DEC`), typically after "consequently / therefore / accordingly / thus";
   (d) a stand-alone **"not contested"** sentence (`NCP`);
   (e) a **lead-in sentence** before a quoted provision ("…alleged a breach of Article 8, which provides:") — a short `APP` span of its own; the quotation is outside.
   No other reason: not a citation, not a change of topic inside one move, not a one-sentence aside.
3. **Cut-or-merge asymmetry (matching uses IoU ≥ 0.5):** if you merge two gold spans you still match the larger one; if you wrongly split one long gold span in two, **both halves usually fail** (one TP lost, two FPs).
   So **when unsure, merge**; cut only on the five reasons above.
4. **Trim only what is not argument:** heading words, paragraph numbers, the quotation itself, and — at a start — nothing else. A few words more or less at an edge does not change a match; a wrong *scope* does.
5. **Do not turn a sentence into a span just because it begins "The Court considers that…"**: ask what legal work it does (states a norm, applies it, reports a contention, records agreement, concludes). Procedural or
   narrative sentences with such a lead-in (e.g. "The Court notes that the hearing took place on…") that stand alone are `O`; inside a reasoning paragraph they are part of its span.
6. **Context beyond the paragraph decides the label, not the boundary.** Read the heading and the previous paragraph before labelling (the largest published confusion is `NEC` vs `APP`).
7. **Expect drift on unfamiliar Articles/judgment types** (published models lost ~12 macro-F1 points moving from Article 8 to Article 3 cases): keep to the structural rules (stage, speaker, paragraph) rather than topic words.

## 6. Reading context matters

The authors found that expert annotators — and models — often cannot tell `Necessity/Proportionality` from
`Application to the concrete case` or `Legal basis` from a single paragraph. Therefore:

* Always read the **section heading**, the **previous paragraph** and the **next paragraph** before deciding
  a label.
* Judgments follow a recurring shape: *parties' submissions* → *(third parties)* → *the Court's assessment*
  (general principles → application → conclusion). Use that shape (see `06_annotation_workflow.md` §Structure
  of an ECHR judgment) as a prior. The **stage** of the paragraph (scope → engagement → justification steps → conclusion) decides the label far more
  often than the wording does — see `02_label_descriptions.md` §1.

## 7. Output of this task

A JSON file per input document (specified in `05_output_schema.md`) containing, for each span,
`[id, start, end, type, actor]` and, if requested, a list of relations `[from_id, to_id, rel]`.
Offsets are **0-based, end-exclusive, Unicode code-point indices into the cleaned text**: UTF-8, line endings
normalised to `\n` (a Windows `\r\n` counts as **one** character — the same as Python's `open(path).read()` and the corpus gold files),
mojibake repaired (`07_edge_cases.md` §3). You do not compute them: you mark spans as **unit ranges** (`"u7-u8"`) from the segmenter's sentence table,
and `am_tools.py build` converts them to exact offsets (`05_output_schema.md`).

## 8. Generalising beyond the ECHR

The scheme was designed for European Court of Human Rights judgments. The 16 argument types are standard in
legal theory and transfer to other courts (constitutional courts, supreme courts) with small changes; the
**actor** set must be adapted (e.g. replace `COMM` with whatever "lower body whose reasoning is reproduced"
exists). If a text is not an ECHR judgment, keep the same codes, map actors as closely as possible
(`APPL` = the party bringing the claim/appeal, `STATE` = the opposing/respondent party or public authority,
`THIRD` = interveners / amicus, `ECHR` = **the deciding court itself**, `COMM` = a lower court/body whose
reasoning the deciding court reproduces), and say so in the run report.
