# 03 — Actor labels (whose voice is the span in?)

Every span gets **exactly one actor** in addition to its type. The two are **orthogonal**: the actor is decided by *who is speaking*, the type by the *stage and move*
(`02_label_descriptions.md`). Never infer one from the other: a Government paragraph inside the justification test is `NEC`/`STATE`; the Court's weighing of the same point is `NEC`/`ECHR`.

| Code | Meaning | Corpus count (share) / 10-doc tuning set |
|---|---|---|
| `ECHR` | **The deciding court itself**: its own reasoning, findings, principles, conclusions, and its own narration of facts and of what the parties said. | 9,950 (65.4 %) / 60 % |
| `STATE` | **The respondent** (the Government). | 2,399 (15.8 %) / 15 % |
| `APPL` | **The applicant(s)** (also "the applicant company"). | 2,471 (16.3 %) / 14 % |
| `COMM` | **The Commission / Delegate** (or the Chamber in a Grand Chamber judgment): reasoning that is reproduced by the Court. | 173 (1.1 %) / 10 % |
| `THIRD` | Admitted third parties (other States, NGOs, interveners). | 212 (1.4 %) / 0 % |

**Caution:** the 10 tuning judgments are old (Commission era) and so show 10 % `COMM`; in the whole corpus `COMM` is only 1.1 %. Use `COMM` **only** when the text reproduces the Commission's/Chamber's report or opinion; a judgment without a
Commission has none. `THIRD` (1.4 %) appears only in judgments with an "intervener / third-party" section: attribute by that section and by "the third-party interveners / [NGO] submitted".

## The rule: the actor is whose voice carries the span

Read the span as a whole and ask **who is making this statement** — not who is merely mentioned.

1. **Reported submission, whole span** → that party. A span that consists of what a party argued (usually opened by "The Government submitted / contended / maintained / disputed…",
   "In the applicant's submission…", "According to the Government…", "Before the Commission, the applicant alleged…", "In their view…") is `STATE` / `APPL`; the same for the Commission
   ("The Commission considered / observed / was of the opinion…", "In its report…", "The Delegate…") → `COMM`.
   * Attribution **carries on** through the following sentences of the paragraph ("They also stressed…", "It further pointed out…", "Firstly… Secondly…") until the Court's own voice returns.
   * A **party's one-line reaction** ("The Government disagreed.", "The Government agreed.", "The Commission accepted it.") → that party; it is a span of its own.
   * Facts or domestic law that a party explains **in support of its argument** ("The process involves… From this the Government drew the conclusion that…") → the party.
   * A quotation of a precedent inside a reported submission stays in the **reporter's** actor (a precedent quoted by the Commission's Delegate is `COMM`).
2. **The Court's own voice → `ECHR`.** This includes
   * "The Court considers / notes / observes / finds / reiterates / agrees…", "In the Court's view", impersonal conclusions ("There has accordingly been a violation"),
   * general principles and their application,
   * the Court's **own narration** of facts, of domestic proceedings and of domestic bodies' decisions,
   * the Court's **reaction** to a party ("The Court agrees with the Commission", "Like the Government, the Court notes…", "As the Government rightly pointed out, …").
   The **grammatical subject / agent** decides: a sentence whose subject is the Court is `ECHR` even if a party or the Commission is named in it ("Like the Commission, the Court considers…", "Having regard to what the applicant has abandoned, the Court…").
3. **Mixed span, one span only** (you did not split): the Court's response wins. A paragraph that reports a submission and then answers it in its own words ("The Government's argument is X. As the Commission stressed, that is not in keeping with…")
   is `ECHR`. Likewise a Court paragraph that merely *lists* what the parties cited ("The Government and the Commission have cited examples…, but the Court…") is `ECHR`.
4. **Two speakers in one sentence** ("The Government disputed this, but the Commission agreed."): split at the clause break with anchors when the halves are ≥ a few words each (the reference splits most of these),
   one span per speaker. If you do not split, use the **first-named** speaker.
5. **Joint attribution** ("both the Government and the applicant…", "the Government and the Commission considered…") and the Court's summary of a **common position** → `ECHR` when the sentence is the Court's own summary;
   a pair "party A … whereas party B …" → split as in 4.
6. **Not-contested statements (`NCP`)**: "The applicant company did not contest the aim" → `APPL`; "The Government accepted that Article 8 applied" → `STATE`; "It is common ground / not disputed that…" or
   "The Government did not dispute this" said by the Court as a finding → `ECHR`. "Neither the Government nor the applicant contested…" → the first-named party.
7. **A conclusion (`DEC`)** is `ECHR` (the Court's own). A party's or the Commission's conclusion is not `DEC`; it is part of its reported view (`APP`/step label).
8. **Court narrating what happened before the Commission** ("Before the Commission, the applicant also alleged a breach of Article 10", "The applicant had also relied on…") → the party who alleged it.
   **Narrating what a domestic court or authority did** → `ECHR` (domestic bodies are not an actor in this scheme).
9. Section headings help only as a prior ("The applicant's submissions" → `APPL`, "The Court's assessment" → `ECHR`); the sentence's own voice overrides them.

## What is *not* decided here

* The type of a reported submission is the **stage** label, not `APP`-because-reported: the Government's argument that a measure pursued no legitimate aim is `PUR`/`STATE`
  (`02_label_descriptions.md` §1). In the plain scope/applicability stage a reported submission is `APP`.
* A change of actor starts a **new span** even when the type is unchanged (`01_task_definition.md` §5).
* Common confusion to avoid: marking `STATE` because the word "Government" occurs in the span. Look at the subject of the sentence.

## Examples (invented)

| Text | Type | Actor |
|---|---|---|
| "In the applicants' submission, the refusal to renew the permit infringed Article 8." | `APP` | `APPL` |
| "The Government replied that the measure rested on section 12 of the Act." (justification stage) | `LEG` | `STATE` |
| "The Delegate of the Commission considered that the measure had been disproportionate." (justification stage) | `NEC` | `COMM` |
| "The Government disputed this, | but the Commission agreed." | `APP` / `APP` | `STATE` / `COMM` |
| "Like the Commission, the Court finds that the interference pursued a legitimate aim." | `PUR` | `ECHR` |
| "The Court notes that the Government stressed the applicant's earlier conviction, but this cannot outweigh…" | `NEC` | `ECHR` |
| "There has accordingly been a violation of Article 8." | `DEC` | `ECHR` |

## Outside the ECHR

If the text is from another court, apply the mapping in `01_task_definition.md` §8 and write the mapping you used in the run report.
