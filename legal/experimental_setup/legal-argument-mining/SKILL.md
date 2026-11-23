---
name: legal-argument-mining
description: Annotate court decisions (plain .txt, especially ECHR judgments) with legal argument spans, their argument type (16 labels), their actor (5 labels) and optionally relations between spans. Use when asked to do argument mining on legal texts, process a directory of judgments, or produce structured span annotations with character offsets.
---

# Legal argument mining skill

Converts each court-decision `.txt` file into one compact JSON file of argument spans (offsets + type + actor) and optional relations.

## Files in this skill — read in this order

| File | Read it for | When |
|---|---|---|
| `01_task_definition.md` | What argument mining is here; the subtasks; what is / is not a span; boundary rules | Always, first |
| `02_label_descriptions.md` | Label priors, the stage-first decision procedure, strict overrides, label cards | Always |
| `03_actor_labels.md` | The 5 actors and the voice rule for deciding whose span it is | Always |
| `04_relations.md` | Supports / attacks / elaborates rules and legal patterns | Only if relations are requested |
| `05_output_schema.md` | Exact JSON format, offset convention, validation | Always (before writing output) |
| `06_annotation_workflow.md` | Step-by-step procedure, chunking, self-check, run report, worked example | Always |
| `07_edge_cases.md` | Missing `THE LAW` heading, flattened paragraphs, mojibake/CRLF, truncated text, facts vs argument, what not to annotate | When the `segment` status line shows a warning, and whenever a paragraph is hard to classify |
| `08_calibration.md` | Reference statistics (spans per judgment, label/actor shares) | After Pass 1, as a sanity check |
| `scripts/am_tools.py` | `segment` (numbered sentence table with scope/tail/flags), `build` (unit ranges → exact offsets), `validate`, `batch-validate`, `rebase` | Always — you never write character offsets yourself |
| `scripts/eval_gold.py` | Score an output against a gold file (IoU ≥ 0.5, per label, actor accuracy if the gold has actors, `--diagnose`) | Only if gold is supplied |
| `examples/` | A tiny input, its unit table, and its correct output | For calibration |

## Task decomposition (summary)

| Subtask | Meaning | Handling |
|---|---|---|
| A. Span detection | where an argument starts/ends | **merged** with B and C into Pass 1 |
| B. Type classification | which of 16 legal argument types | **merged** (Pass 1) |
| C. Actor classification | ECHR / applicant / state / third party / commission-chamber | **merged** (Pass 1) |
| D. Relation mining | supports / attacks / elaborates between spans | Pass 2, optional |

## Run modes (default: `spans`)

* `spans` — Pass 1 only; `relations` is `[]`. Cheapest; use unless told otherwise.
* `spans+relations` — Pass 1 then Pass 2.
If the user does not say, use `spans`, and mention in the final message that relations can be added.

## Quick procedure

1. `python3 scripts/am_tools.py segment <input_dir> <work_dir>` → a numbered sentence table (`u1, u2, …`) per document and one status line each. Read the status line (scope, tail, warnings) before annotating.
2. For each document: read its `*.units.txt`, annotate (Pass 1, then Pass 2 if requested), and append rows to
   `<work_dir>/<stem>.jsonl` using **unit ranges**: `[1,"u7-u8","APP","APPL"]`. (Mid-sentence cut → add an anchor phrase.)
3. `python3 scripts/am_tools.py build …` (turns unit ranges into character offsets) then `validate … --show`; fix errors.
4. Output: `<output_dir>/<stem>.am.json` (one per input file, with `[id,start,end,type,actor]` spans), plus `_run_report.md` at the end.

## Non-negotiable rules

1. **Never write or count character offsets.** Mark spans as unit ranges (`"u7-u8"`); `build` produces the exact 0-based,
   end-exclusive offsets. For a mid-sentence boundary use an anchor phrase copied from the text, not a number.
2. **One type and one actor per span; spans are flat, non-overlapping, and stay inside one paragraph.**
3. **Do not store span text or explanations** in the output.
4. **Label by stage first** (`02_label_descriptions.md` §1): `APP` outside the justification test; `LEG`/`PUR`/`NEC` inside it, for every speaker; `DEC`, `NCP`, `PRE`, `MOA`, `DIS`, `TXT` only on their strict trigger; never `TEL/SYS/CMP/HIS/SUI`. When unsure, use the stage label — a wrong rare label costs more than a missed one.
5. **The actor is the voice carrying the span** (`03_actor_labels.md`): a reported submission carries the party's / Commission's actor; the Court's own sentences, including its reactions and narration, are `ECHR`; split at a speaker change.
6. **Process every `.txt` file; one output per file; skip files whose output already validates.**
7. **Annotate only the Law section** the table shows (facts, operative part, separate opinions, headings, quotations `Q`, and Art. 41/50 + costs `L` are not annotated); work paragraph by paragraph, one speaker + one label = one span; split at a change of speaker.
8. If a text isn't an ECHR judgment, keep the codes, map the actors (`01_task_definition.md` §8), and note it in the report.
