# 05 — Output format (token-lean JSON, one file per input file)

## Two layers: what you WRITE vs. what is PRODUCED

| Layer | File | Who makes it | Spans look like |
|---|---|---|---|
| **Scratch** (you write this) | `<work_dir>/<stem>.jsonl` | the model | `[1, "u7-u8", "APP", "APPL"]` — **unit ranges, no character numbers** |
| **Final** (the deliverable) | `<output_dir>/<stem>.am.json` | `am_tools.py build` | `[1, 258, 463, "APP", "APPL"]` — exact character offsets |

You **never type a character offset**. You say which sentence-units a span covers (numbers from the `u…` column of the
`*.units.txt` table); `build` looks up the exact offsets. Details of the scratch format are in §"Scratch format" below.

## File naming

Input `X.txt` in the input directory → output `X.am.json` in the output directory (default `argument_mining_output/`).
One output per input; same stem; never merge documents.

## Format

```json
{
  "schema": "lam-am/1.1",
  "file": "case1.txt",
  "n_chars": 1145,
  "offsets": "lf",
  "spans": [
    [1, 258, 463, "APP", "APPL"],
    [2, 468, 522, "NCP", "STATE"],
    [3, 523, 573, "NCP", "ECHR"],
    [4, 578, 789, "MOA", "ECHR"]
  ],
  "relations": [
    [4, 6, "S"]
  ]
}
```

### `spans`: array of `[id, start, end, type, actor]`

| Position | Name | Rule |
|---|---|---|
| 0 | `id` | Positive integer, unique within the file; use 1,2,3… in document order |
| 1 | `start` | 0-based index of the span's first character in the file |
| 2 | `end` | index **after** the last character (exclusive), so the span text is `text[start:end]` |
| 3 | `type` | one of the type codes below |
| 4 | `actor` | one of the actor codes below |

Offset rules:
* Indices count **Unicode code points of the cleaned text**: UTF-8 (BOM removed), **line endings normalised to `\n` — a Windows `\r\n` counts as ONE character** (identical to Python's `open(p, encoding="utf-8").read()` and to the corpus gold files), mojibake such as `â€™` repaired to `’`. `n_chars` is the length of that cleaned text and `"offsets": "lf"` records the convention (a `"repairs": N` key appears if mojibake was repaired).
* Older outputs made on the raw CRLF text (`n_chars` = raw length) are converted with `am_tools.py rebase old.am.json text.txt new.am.json`; `validate` detects them and says so.
* Reading the text yourself in another tool? Use `open(p, encoding="utf-8").read()` in Python (text mode), **not** `newline=""` or `rb`, or your offsets will drift by one per line break on CRLF files.
* Spans sorted by `start`; **no overlaps**; each span inside **one paragraph**; no leading/trailing whitespace; never start/end inside a word.
* **Never count or type characters yourself.** The final offsets are produced by `am_tools.py build` from the unit ranges (and anchors, for mid-sentence cuts) you wrote in the scratch file.
* **The span text is not stored** (to save tokens); recover it with `text[start:end]` (or `am_tools.py validate --show`).

### Unit flags that `build` enforces

`H` (heading): a span may not contain a heading unit (error). `L` (low-priority section) and units in the hidden tail: allowed but
`build` prints a warning, because the corpus does not annotate them.

### `relations`: array of `[from_id, to_id, rel]`

`rel` ∈ `S` (supports), `A` (attacks), `E` (elaborates). Direction and rules: `04_relations.md`. Empty list `[]` if relations were not requested or none are justified.

### Type codes (16)

| Code | Label | Code | Label |
|---|---|---|---|
| `NCP` | Procedural — non-contestation by the parties | `PUR` | Proportionality — legitimate purpose |
| `TXT` | Interpretation — textual | `SUI` | Proportionality — suitability |
| `HIS` | Interpretation — historical | `NEC` | Proportionality — necessity/proportionality |
| `SYS` | Interpretation — systematic | `OVR` | Institutional — overruling |
| `TEL` | Interpretation — teleological | `DIS` | Institutional — distinguishing |
| `CMP` | Interpretation — comparative law | `MOA` | Institutional — margin of appreciation |
| `LEG` | Proportionality — legal basis | `PRE` | Precedents of the ECHR |
| `DEC` | Decision of the ECHR | `APP` | Application to the concrete case |

### Actor codes (5)

`ECHR` · `APPL` (applicant) · `STATE` (respondent) · `THIRD` (third parties) · `COMM` (Commission/Chamber)

## Scratch format (`.jsonl`) — this is what you actually write

One JSON array per line, appended to `<work_dir>/<stem>.jsonl` as you annotate (lines starting with `#` are comments).

### Span rows: `[id, "unit-range", "TYPE", "ACTOR"]`

```
[1,"u7-u8","APP","APPL"]
[2,"u9","NCP","STATE"]
[3,"u10","NCP","ECHR"]
```
* `"u7-u8"` = every sentence-unit from `u7` through `u8` inclusive; `"u9"` = a single unit. `u` is optional (`"7-8"` also works).
* All units in a range must be in the **same paragraph** (same `p` in the table). A passage that runs over several paragraphs
  becomes one span per paragraph.
* Units are numbered in the `*.units.txt` table; use exactly those numbers.

### Mid-sentence boundaries: add an anchor object as a 5th item

Use only when **one sentence contains two different moves** (e.g. different actor or type either side of ", but").
An anchor is a **short, exact phrase copied from the sentence**; it must occur **exactly once inside the unit**
(first unit for a start anchor, last unit for an end anchor). `build` finds the position for you.

| Key | Effect |
|---|---|
| `"start_at": "phrase"` | span starts at the first character of `phrase` |
| `"start_after": "phrase"` | span starts right after `phrase` |
| `"end_before": "phrase"` | span ends right before `phrase` |
| `"end_after": "phrase"` | span ends right after `phrase` |

Use at most one start key and one end key per span. Whitespace at the cut is trimmed automatically.

Example — unit `u2` is *"The applicant argued that the law was unclear, but the Court finds that it was foreseeable."*:
```
[1,"u2","LEG","APPL",{"end_before":", but"}]
[2,"u2","LEG","ECHR",{"start_at":"the Court finds"}]
```
Result: span 1 = "The applicant argued that the law was unclear"; span 2 = "the Court finds that it was foreseeable."

A span may also begin inside one unit and end at the end of a later one, e.g. `[2,"u2-u3","LEG","ECHR",{"start_at":"the Court finds"}]`.
Cuts must not fall inside a word and must leave a non-empty span (`build` reports an error otherwise).

### Relation rows: `[from_id, to_id, "S|A|E"]`

```
[4,6,"S"]
```

### Build

```bash
python3 scripts/am_tools.py build work/case1.jsonl input/case1.txt argument_mining_output/case1.am.json
```
`build` resolves every unit range/anchor to exact offsets, sorts the spans and writes the final schema above. It stops with a
numbered list of problems (and writes nothing) if any row is invalid: unit does not exist, range runs backwards, range crosses a
paragraph, anchor not found or ambiguous, bad JSON. Fix the listed `.jsonl` lines and run it again. (Old-style rows with raw
offsets `[id, start, end, "TYPE", "ACTOR"]` are still accepted for backwards compatibility but should not be written.)

## Validation

```bash
python3 scripts/am_tools.py validate input/case1.txt argument_mining_output/case1.am.json --show
python3 scripts/am_tools.py batch-validate input argument_mining_output
```
`validate` checks the **final** file against the text. Errors (must fix in the `.jsonl`, then rebuild): bad offsets,
whitespace/mid-word boundaries, paragraph crossing, overlap, unknown codes, dangling relation ids, `n_chars` mismatch. Warnings (look, then decide): very long/short spans, over-use of `APP`,
rare labels, no `DEC`, `S`-cycles.

## Optional alternative formats

If the user wants another container, convert the same content without changing semantics:
* **JSONL / CSV**: one span per row with columns `file,id,start,end,type,actor`; relations in a second table `file,from,to,rel`.
* **XML**: `<doc file="…" n_chars="…"><span id="1" start="258" end="463" type="APP" actor="APPL"/>…<rel from="4" to="6" type="S"/></doc>`.
Default is the JSON above because arrays are the cheapest for an LLM to emit.
