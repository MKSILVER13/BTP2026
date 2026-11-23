# 02 — Argument-type labels: what they mean and how they are actually used

There are **16 types**. The scheme looks like a rich typology, but in practice annotators use **about eight labels**, and which one
they pick is decided mostly by **where in the judgment the paragraph sits** (its *stage*), not by the words in it.
Work in this order: **(1) find the stage → (2) check the few strict overrides → (3) otherwise use the stage label.**

## 0. Priors — how the labels are really distributed

Real corpus (373 judgments, **15,205 spans**) and, for comparison, the 10 fully annotated judgments used to tune this skill (267 spans):

| Label | Corpus count | Corpus share | 10-doc share | What it is in practice |
|---|---|---|---|---|
| `APP` | 8,688 | **57.1 %** | 57 % | the default: scope of the case, applicability, interference, parties'/Commission's submissions, "the Court agrees", "no need to examine" |
| `PRE` | 2,015 | 13.3 % | 6 % | Court-voiced general doctrine restated from earlier judgments |
| `NEC` | 1,958 | 12.9 % | 12 % | the *necessity / proportionality / fair-balance* step of the justification test |
| `DEC` | 1,236 | 8.1 % | 7 % | the Court's own closing holding (short) |
| `LEG` | 513 | 3.4 % | 10 % | the *legal-basis / "in accordance with the law"* step |
| `PUR` | 271 | 1.8 % | 4 % | the *legitimate-aim* step |
| `NCP` | 264 | 1.7 % | 1.5 % | stand-alone "not contested / common ground" |
| `DIS` | 88 | 0.58 % | 0.7 % | contrasting with a named earlier case |
| `MOA` | 67 | 0.44 % | 1.1 % | margin of appreciation as the subject |
| `TEL` | 50 | 0.33 % | 0.7 % | object and purpose / living instrument |
| `SUI` | 25 | 0.16 % | 0 | suitability (rational connection) |
| `CMP` | 13 | 0.09 % | 0 | comparative law |
| `TXT` | 10 | 0.07 % | 0.4 % | wording / language-version analysis |
| `SYS` | 5 | 0.03 % | 0 | systematic interpretation |
| `OVR` | 2 | 0.01 % | 0 | overruling |
| `HIS` | 0 | 0 | 0 | never |

Actors in the corpus: `ECHR` 9,950 (65.4 %), `APPL` 2,471 (16.3 %), `STATE` 2,399 (15.8 %), `THIRD` 212 (1.4 %), `COMM` 173 (1.1 %). (`COMM` is common only in old judgments that reproduce the Commission's report.)

Per judgment expect **~15–40 spans**, about **1.5 per 1,000 characters** of Law section, **mean ≈ 570 characters** (median ≈ 335), with ≈ 75 % of the Law section inside spans.

**How to use the priors:** a label with a share below 1 % (`DIS MOA TEL SUI CMP TXT SYS OVR`) is right about as often as it is wrong *when you are tempted by it*; the cost of a false positive on a
rare label is a lost `APP`/`NEC`. Use them only on their strict trigger (§2). The five interpretation labels together are ≈ 0.7 % of spans: interpretive reasoning about how the Article applies is `APP`.
`PRE` is the one mid-frequency label that tuning data under-represents (13 % in the corpus): do use it for authority-introduced Court doctrine (§2), but not for citations inside applying sentences.

---

## 1. Step 1 — find the stage of the paragraph

An ECHR Law section has a recurring shape. Decide which stage each paragraph is in (headings help; so do the phrases in the third column).

| # | Stage | Recognise it by | Label for **every speaker** (Court, Commission, applicant, Government, third party) |
|---|---|---|---|
| 1 | **Complaint / scope** | "The applicant alleged a breach of Article X, which provides:", "The sole complaint declared admissible was…", "The Government disputed this / the Commission agreed" | `APP` |
| 2 | **Engagement of the right** | applicability, "family/private life", "civil right", victim status, whether there is an **interference**, positive vs negative obligation, exhaustion, "scope of the Article" | `APP` |
| 3 | **Justification of an interference / of a positive-obligation balance** | headings *In accordance with the law*, *Legitimate aim*, *Necessary in a democratic society*, *Compliance with paragraph 2*, *Proportionality*; "paragraph 2 of Article 8", "second paragraph of Article 1 of Protocol No. 1", "fair balance has to be struck", "pressing social need" | **the step label** `LEG` → `PUR` → `NEC` (see below) |
| 4 | **Conclusion** of a section | "There has therefore been a violation / no violation", "the Court thus concludes", "no interference", the sum awarded | `DEC` (the Court's own sentence only) |
| 5 | **Other complaints** (another Article, not pursued, absorbed, not examined) | "The Court does not consider it necessary to examine…", "the complaint was not pursued" | `APP` (and `DEC` only for an actual finding) |
| 6 | **Just satisfaction (Art. 41/50), costs** | headings *Application of Article 50 / 41*, *Damage*, *Costs and expenses* | **not annotated by default** — see §5 |

**Stage 3 — which step?** Label by the *question the passage answers*, whoever is speaking:
* is the measure based on domestic law that is accessible, foreseeable, of adequate quality? → **`LEG`**
* does it pursue a legitimate aim, and which? → **`PUR`**
* is it necessary / proportionate / a fair balance / are there safeguards / is there a less restrictive means / is the burden excessive? → **`NEC`**
Submissions inside a step take that step's label: *the applicant's argument that the measure pursued no legitimate aim*, *the Government's reply*,
*the Commission's view*, and *the Court's finding* are all `PUR`. A one-line party-position sentence ("The Government disagreed.",
"The Commission accepted it.") also takes the label of the stage it sits in.
When a paragraph covers two steps, label it by its **main part**, do not split it (split only at a change of speaker).

A positive-obligation case (the State is said to have *failed to act*) has no heading "paragraph 2", but once the Court announces that it
"will have regard to the fair balance" the following paragraphs are stage 3 (aim → `PUR`; adequacy of procedure / balance → `NEC`).
An Article 6 or other non-qualified-right discussion (e.g. is there a right of access to court, was Article 6 applicable) has no stage 3: it is `APP`
throughout, except `PRE`/`DEC`/`NCP` overrides.

## 2. Step 2 — the strict overrides (check in this order, sentence by sentence)

Each override needs its **trigger**. No trigger → keep the stage label.

| Label | Trigger (all must hold) | NOT |
|---|---|---|
| **`DEC`** | The **Court's own** sentence that closes an issue: finds / does not find a violation, an interference, applicability; "thus concludes"; "awards … on an equitable basis"; "finding of a violation is sufficient just satisfaction". Short (≈ 50–300 chars), usually the last sentence of a paragraph or section. | "does not consider it necessary to examine…" → `APP`. A party's or the Commission's conclusion. The operative part. A step inside the reasoning ("the measure was therefore lawful") — that stays in its `LEG/PUR/NEC` span. |
| **`NCP`** | A **stand-alone** sentence (or two) whose whole content is that something is **not contested / common ground / agreed**: "It is common ground that…", "The Government did not dispute this", "Neither party contested…". | The same words tacked onto a reasoning sentence inside a longer span (they stay in it). A party merely agreeing with the Commission's conclusion → `APP`. |
| **`PRE`** | A sentence or paragraph, **in the Court's voice**, that states **general doctrine taken from earlier judgments**, detached from the facts of this case, usually introduced by an authority marker: "The Court reiterates / recalls that", "According to its established case-law", "As the Court held / pointed out in the X judgment", "has consistently held". A block quotation from such a judgment that continues the Court's sentence is part of the same `PRE` span. | A sentence that **applies or weighs** and only contains "(see X v. Y)" — a citation does not make a span `PRE` (≈ 3 of 4 citation-bearing spans are not `PRE`). One-sentence statement of the test inside stage-3 analysis ("to be necessary, an interference must correspond to a pressing social need (see …)") that flows straight into the application → keep it in the `NEC` span. A party's or the Commission's quotation of a precedent → part of that reported view. |
| **`MOA`** | A sentence or short paragraph **whose own subject** is how much discretion States have ("margin of appreciation", "the State enjoys a wide/narrow margin", "better placed than an international court"). | Margin mentioned in passing inside a balancing or applying paragraph (stays in `NEC`/`APP`). |
| **`DIS`** | The Court or a party **contrasts the present case with a named earlier case** and says the earlier ruling therefore does not transfer ("unlike in X", "differs from X in that"). | Citing a case for similarity (`PRE`/`APP`). Contrasting the parties' positions. |
| **`TXT`** | The span is *about the wording* of the provision: comparing language versions ("the French text", "the English text"), or parsing the ordinary meaning of specific words in the Article. | General "interpretation" talk, preamble, object and purpose, rule of law, other Articles, Vienna Convention, relationship between Articles, travaux → `APP`. |

Everything else: **the stage label**.

## 3. Label cards

### `APP` — Application to the concrete case (default)
Reasoning about *this* case that is not a justification step: scope, applicability, existence of an interference, positive/negative obligation, victim
status; what each party and the Commission argue about those points; the Court's response ("The Court agrees / does not share this view / sees no reason to disagree");
the Court's decision not to examine something; the Court's interpretation of the Article as it applies here. It is the right answer for most of the Law section.
Invented example: *"The applicant company complained that it had no access to a court. It alleged a violation of Article 6 § 1."*

### `LEG` — Legal basis ("prescribed by law" / "in accordance with the law")
Stage-3 passage on whether the measure had a basis in domestic law and whether that law is accessible, foreseeable, precise, safe from arbitrariness; submissions on it.
Invented example: *"The Court notes that the measure was based on section 12 of the Act, which was published and sufficiently precise."*

### `PUR` — Legitimate purpose
Stage-3 passage on whether the measure pursued a legitimate aim and which one (national security, economic well-being, prevention of disorder or crime,
protection of health, morals, rights of others, general interest of the community); submissions on it.
Invented example: *"The Government said the restriction served the prevention of disorder; the Court accepts that this was a legitimate aim."*

### `NEC` — Necessity / proportionality
Stage-3 passage on necessity, "pressing social need", fair balance, relevant and sufficient reasons, less restrictive alternatives, adequacy of safeguards or
procedure, weight of the individual's interest against the public interest — **by anyone**, including the Government's explanation of why the measure was needed,
the applicant's reply, the Commission's view, and the Court's weighing, including its final "…cannot be regarded as necessary in a democratic society".
Invented example: *"The applicant pointed out that less intrusive means were available. The Court considers that the authorities did not strike a fair balance."*

### `DEC`, `NCP`, `PRE`, `MOA`, `DIS`, `TXT` — see the override table (§2).

### `TEL`, `SYS`, `CMP`, `HIS`, `SUI`, `OVR` — avoid
`TEL` (object and purpose, living instrument), `SYS` (read with other Articles / international law), `CMP` (laws of other States, European consensus), `HIS`
(travaux), `SUI` (rational connection), `OVR` (overruling precedent) are essentially never chosen by annotators for passages that look like them;
the Court's reasoning there is `APP`, or `NEC`/`PRE`/`DEC` by the stage rules. If you are tempted, write `APP` — unless the span is a *dedicated explicit statement* that the
Court is overruling its own case-law (`OVR`), in which case you may use it.

## 4. Confusable pairs — what separates them, with worked "why not" examples

All examples are invented. Format: **text → label; why not the other one.**

**4.1 `APP` vs `NEC` (the most common confusion; experts themselves often cannot tell without context).**
The difference is *when* in the argument the paragraph sits, not the vocabulary.
* *Scope stage:* "The applicant submits that the prohibition on meeting his daughter amounted to an interference with his family life; the Government contend there was none." → **`APP`**. Why not `NEC`: the Court has not yet reached the question whether the measure was justified; the dispute is whether Article 8 is engaged at all.
* *Justification stage:* "The applicant submits that the prohibition was out of proportion, because a supervised-contact arrangement would have served the same goal." → **`NEC`**. Why not `APP`: the heading/test is already "necessary in a democratic society", and the submission is an argument about less restrictive means and balance.
* *Same words, different label:* "The Government argued that the situation was exceptional." is `APP` in the applicability discussion and `NEC` once the fair-balance test has begun.
* Positive-obligation case with no "paragraph 2" heading: the passage becomes `NEC` once the Court has announced that it will look at whether a fair balance was struck; the paragraphs before (was there a duty? is the right engaged?) are `APP`.

**4.2 `APP` vs `LEG`.** `LEG` is only about the *legal basis* of the measure (a law, accessible, foreseeable, precise).
* "The Court notes that the order was taken under section 12 of the Act, which is published and worded clearly enough for the applicant to foresee its consequences." → **`LEG`**. Why not `APP`: it answers the "in accordance with the law" question.
* "The Court notes that the applicant was served with the order on 3 May and appealed the next day." → **`APP`/`O`**. Why not `LEG`: it is about what happened, not about the quality of the law.
* A party asserting "the law was not accessible" **inside the justification test** is `LEG`; the same party asserting "there was no interference" is `APP`.

**4.3 `LEG` vs `NEC`.** Quality of the law (foreseeability, safeguards written into the law) can look like proportionality.
* "The statute gave the authorities an unfettered discretion and set no limit on the duration of the measure." → **`LEG`** when the Court is testing whether the law protects against arbitrariness ("in accordance with the law"). Why not `NEC`: the question is the quality of the rule.
* The same facts used to ask whether *this* interference, on these facts, was proportionate ("less intrusive means were available") → **`NEC`**. Why not `LEG`: the question is the weighing, not the quality of the rule.
* Heading decides: under *In accordance with the law* → `LEG`; under *Necessary in a democratic society* → `NEC`.

**4.4 `PUR` vs `NEC`.** `PUR` answers "which legitimate aim, if any?"; `NEC` answers "was the measure needed and balanced for that aim?".
* "The Government said the restriction served the prevention of disorder; the Court accepts that this was a legitimate aim." → **`PUR`**. Why not `NEC`: it names and accepts the aim and says nothing about whether the measure was needed.
* "While the aim of preventing disorder was legitimate, a ban of this breadth went further than needed." → **`NEC`** (the first clause is an aside). Why not `PUR`: the main claim is about the measure's breadth.
* A paragraph that does both: label by its **main** part; do not split.

**4.5 `PRE` vs `APP` / `NEC` (a citation does not make `PRE`; ≈ 3 in 4 citation-bearing spans are not `PRE`).**
* "The Court reiterates that Article 6 § 1 secures to everyone the right to have any claim relating to his civil rights brought before a court (see X v. Y, § 36)." → **`PRE`**. Why not `APP`: it states a general rule as settled law, in the Court's voice, before applying it.
* "Applying that right to this case, the Court observes that the applicant was refused leave to appeal (see X v. Y, § 36)." → **`APP`**. Why not `PRE`: the citation is a reference attached to an applying sentence.
* "To be necessary, an interference must meet a pressing social need (see X v. Y, § 48); here the ban applied to all students, whatever the circumstances." → **`NEC`**. Why not `PRE`: the doctrine sentence flows straight into the application and is not a free-standing statement.
* "The Government cited X v. Y for the proposition that…" → part of the **party's** span. Why not `PRE`: a party's reliance on a precedent is reported speech, not the Court's doctrine.

**4.6 `PRE` vs `MOA`.** If the sentence's *own subject* is the width of the margin, it is `MOA`, even with a citation.
* "The Contracting States enjoy a certain margin of appreciation in assessing whether, and to what extent, differences in otherwise similar situations justify different treatment (see…)." → **`MOA`**. Why not `PRE`: its whole content is the discretion of States.
* "…and the Court will weigh the margin together with the fact that the measure concerned a core aspect of private life." → stays in **`NEC`**. Why not `MOA`: the margin is mentioned while balancing.

**4.7 `DEC` vs `APP` vs a step label.**
* "There has accordingly been a violation of Article 8." → **`DEC`**. Why not `APP`: it is the Court's own closing finding.
* "The Court therefore does not consider it necessary to examine the complaint under Article 13." → **`APP`**. Why not `DEC`: it records a decision *not* to examine; no finding is made.
* "The Court concludes that the interference was therefore in accordance with the law." (closing sentence of the legal-basis step) → **`DEC`** if it stands as its own short closing sentence; if it is the last clause of a longer `LEG` analysis, it **stays in the `LEG` span**. Why not always `DEC`: `DEC` is a short own sentence (≈ 50–300 chars) that closes a whole issue, and it is often cut off after "consequently / therefore / thus".
* "The Commission concluded that Article 8 had been violated." → **`APP`/`COMM`**. Why not `DEC`: it is someone else's conclusion.
* The operative part ("For these reasons, the Court holds…") is **not annotated**.

**4.8 `NCP` vs `APP`.**
* "It is common ground that the applicant was detained from 3 to 9 May." (stand-alone) → **`NCP`**. Why not `APP`: its whole job is to record agreement so the point needs no discussion.
* "The Government accepted the Commission's conclusion on Article 8." → **`APP`**. Why not `NCP`: it reports a party's position on the outcome rather than saying that a point is uncontested.
* "…it is not disputed that there was an interference, and the Court sees no reason to find otherwise, as the measure clearly affected his correspondence." → stays in the reasoning (**`APP`**). Why not `NCP`: the agreement is a clause inside a longer reasoning sentence.

**4.9 `TXT` vs `APP` (and the other interpretation labels).**
* "In the French text the word is 'contestation', which means a genuine dispute; the English 'determination' does not alter that." → **`TXT`**. Why not `APP`: it analyses the wording of the provision.
* "Reading the Article in light of its preamble and the rule of law, the Court finds that access to a court is implicit." → **`APP`** here. Why not `TEL`/`SYS`: even though it talks about preamble and context, the reference annotations place this reasoning, about how the Article applies, in `APP`.
* "Comparing the laws of the member States, the Court notes that most allow…" → **`APP`** (rarely `CMP`). Why not `CMP`: only ≈ 0.1 % of spans are `CMP`; keep `APP` unless the passage is *entirely* a survey of other legal systems.

**4.10 `DIS` vs `PRE` / `APP`.**
* "Unlike in X v. Y, where the applicant had been heard, here no hearing took place; that precedent therefore does not apply." → **`DIS`**. Why not `PRE`: the earlier ruling is expressly set aside because of an essential factual difference.
* "As in X v. Y, the Court finds that the applicant was heard." → **`APP`**. Why not `DIS`: the cases are compared for *similarity*.

**4.11 `SUI` vs `NEC`.** "The ban was apt to achieve its aim" (rational connection) is `SUI`; in practice it is almost always folded into the `NEC` passage. Keep it in `NEC` unless the span is only about whether the means can achieve the aim.

**4.12 `OVR` vs `DEC` / `PRE`.** Only a dedicated, explicit statement that the Court is departing from its own earlier case-law is `OVR` (two spans in 15,205). "The Court is not bound by its previous decisions but finds no reason to depart" is not `OVR` (it is `PRE`/`APP`).

---

## 5. What is *not* labelled

Headings; the quoted text of the Convention, Protocols, statutes, regulations, circulars, domestic judgments (units flagged `Q`); the operative
part and separate opinions (hidden tail); signatures. By default also **not annotated: Article 41 / 50 "just satisfaction"** (claims, replies, reasoning, awards) and **costs and
expenses** — in 7 of the 10 reference judgments these sections have no spans at all (and the other 3 annotate only a part). Annotate them only if the user asks for full coverage; then use
`APP` for claims and replies and `DEC` for the Court's award or its "finding of a violation is sufficient satisfaction".
Exception to the quotation rule: a block quotation from an ECtHR precedent that is part of the Court's own `PRE` sentence stays inside that span.

## 6. If you are still unsure

1. Stage label (APP in stages 1, 2, 5; the step label in stage 3).
2. If the choice is between a rare label and the stage label → the stage label.
3. If a paragraph tempts you to use three labels, use one (its main move) and split only where the **speaker** changes or where a short `DEC` / stand-alone `PRE` / stand-alone `NCP` sentence sits at its edge.
