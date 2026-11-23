# 04 — Relations between argument spans (optional Pass 2)

> Relations are best-effort and high-precision: **a missing relation is better than a doubtful one.** The tuning judgments carry no relations, so this layer is not scored in `eval_gold.py`; only emit it when asked.

Run this pass **after** span annotation is finished and validated. You work on the list of spans (their ids,
types, actors and short texts), not on character offsets.

## 1. What a relation is

A relation is a directed edge `[from_id, to_id, rel]` meaning **"the `from` span bears on the `to` span"**.
Convention: **`from` is the premise/reason; `to` is the claim/target** (arrows point towards the conclusion).

| Code | Name | Meaning | Test sentence |
|---|---|---|---|
| `S` | **supports** | `from` gives a reason, rule, evidence or step that makes `to` more acceptable. | "*to* is true/holds **because** *from*." |
| `A` | **attacks** | `from` opposes `to`: rebuts it, denies its premise, or blocks its transfer/applicability. | "*from* **argues against** *to*." |
| `E` | **elaborates** | `from` specifies, narrows or illustrates `to` without adding an independent reason. Use sparingly. | "*from* is **a more detailed version of** *to*." |

Use the **same direction** for all three. Stance is expressed by the code, not by flipping direction.

## 2. When two spans may be related

* Both are in the **same document**, and normally in the **same section/issue** (same Article, same heading).
* Distance: usually within ~15 spans; never across different Articles/complaints unless text explicitly refers back.
* **No self-relations, no duplicate pairs, no cycles of `S`.**
* A span may have 0, 1 or several outgoing relations; many spans legitimately have **none** (e.g. a lone `NCP`).
* Do not link spans just because they are adjacent or on the same topic.

## 3. Legally typical patterns (use as priors, confirm in the text)

| Pattern | Relation |
|---|---|
| General rule/principle (`PRE`) → the span that **uses** it (`APP`, `NEC`, `LEG`, `PUR`, `MOA`) | `S` |
| Interpretive method (`TXT`, `HIS`, `SYS`, `TEL`, `CMP`) → the span stating the resulting interpretation (often `PRE`-like rule sentence or `DEC`) | `S` |
| Proportionality step (`LEG`, `PUR`, `SUI`, `NEC`) → the section's conclusion (`DEC`) | `S` |
| `MOA` (width of discretion) → the `NEC` span it conditions | `S` |
| `APP` (court's application of law to facts) → the `DEC` that concludes the section | `S` |
| `NCP` (agreement) → the span that relies on it (usually the next `APP`/`DEC`) | `S` |
| Court span that **accepts** a party's argument → that party span | `S` (see §4) |
| Court span that **rejects** a party's argument → that party span | `A` (see §4) |
| Later party reply (e.g. `STATE`) → the earlier opposing party claim (e.g. `APPL`) on the same point | `A` |
| `DIS` → the `PRE` (or party span) whose transfer it blocks | `A` |
| `OVR` → the `PRE` span (precedent) it abandons | `A` |
| Second sentence-span repeating the same point with an example | `E` |

## 4. Court responses to party arguments (the most common cross-actor case)

The court's treatment of a submission is expressed **from the court's span to the party's span**, because the
court's span is the *reaction*:

* Court **agrees** with the party → `[court_span, party_span, "S"]`.
* Court **disagrees** → `[court_span, party_span, "A"]`.
* Court merely **reports** the argument without taking a position → no relation.

(Reason: the court span "supports/attacks the claim made by the party span". This keeps a single rule for
direction: *from = the span that comments, to = the span being commented on* — while for ordinary reasoning
`from = premise`, `to = conclusion`. Both rules coincide with "from bears on to".)

## 5. Procedure for Pass 2

1. Print the span list compactly: `id | type | actor | first ~100 chars`. Group by heading/issue.
2. For each `DEC` span, find the spans of the same issue that lead to it → add `S` edges (prefer *chains*:
   `PRE → APP → DEC`, not a star of ten edges into `DEC`). Link a premise directly to `DEC` only if it is the
   immediate reason.
3. For each party span, check whether a later court span explicitly responds → add `S`/`A` per §4.
4. For `DIS`, `OVR` look back for the precedent (`PRE`) they refer to by case name.
5. Add `MOA → NEC`, `NCP → user` links when textually evident.
6. Delete any relation you cannot justify with a quotable cue ("accordingly", "since", "unlike", "agrees with", "dismisses").
7. Re-run the validator.

## 6. Worked mini-example

```
1 APP  APPL  "In the applicants' submission, the refusal … infringed Article 8."
2 NCP  STATE "The Government accepted that Article 8 was applicable."
3 MOA  ECHR  "The Court reiterates that States enjoy a certain margin of appreciation …"
4 LEG  ECHR  "… the expulsion order had a basis in the Aliens Act, so it was in accordance with the law."
5 NEC  ECHR  "The Court is not convinced that the interference was necessary … A fair balance was not struck …"
6 DEC  ECHR  "There has accordingly been a violation of Article 8."
```
Relations: `[3,5,"S"]` (margin conditions the balance), `[4,6,"S"]`, `[5,6,"S"]` (steps → conclusion),
`[5,1,"S"]` (the court's finding agrees with the applicants' claim in span 1).
Not linked: span 2 (agreement on applicability does not bear on the necessity argument here).
