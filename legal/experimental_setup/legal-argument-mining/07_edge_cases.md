# 07 — Edge cases and troubleshooting

Each section = one problem seen in real runs, what the tool does about it, and what you must do.
The status line printed by `am_tools.py segment` (and the `#` header lines of every `*.units.txt`) tells you which sections apply.

## 1. No `THE LAW` heading — where does the legal reasoning start?

`segment` looks for the start in this order and reports the source as `scope=<source>@<char>`:

| source | meaning | what is hidden | what you do |
|---|---|---|---|
| `law-heading` / `law-heading-inline` / `assessment-heading` | a `THE LAW`, `AS TO THE LAW`, `IN LAW` or "The Court's assessment" heading (also found inside flattened text) | everything before it | nothing — trust it |
| `excerpt` | no judgment preamble at all (no "CASE OF…", "PROCEDURE", "THE FACTS", "Application no.…"): the file is an **excerpt that already starts in the reasoning** (typical for 700/1000/2000-word experiment files) | nothing | annotate **from the first unit** |
| `issue-heading` | a heading such as `II. ALLEGED VIOLATION OF ARTICLE 8` was found but no `THE LAW` | nothing (a `>>>` marker shows the suggestion) | reasoning normally starts at/just before the marker; look at the units above it |
| `cue` | first paragraph with phrases like "The Court notes/reiterates/considers…", "alleges a violation of Article…" | nothing (a `>>>` marker) | decide yourself; the real start may be a paragraph or two earlier (e.g. a paragraph stating the scope of the case) |
| `none` | no signal | nothing | decide yourself (see below); if the whole file is facts, annotate nothing and say so in the report |

**How to decide yourself (facts vs reasoning).** Legal reasoning begins at the first paragraph that (a) states what the complaint under
which Article is ("The applicant alleges a breach of Article 8…", "The sole complaint declared admissible was…"), or (b) records a
submission / the Commission's opinion / the Court's assessment about *how a norm applies*. Fact and procedure paragraphs are chronological
("On 12 March… the applicant…", "The Commission declared the application admissible on…", "The Chamber relinquished jurisdiction…"),
describe domestic law ("Section 31 of the Act provides…") or list who appeared. Once the argument has started, keep going to the end of the
reasoning — do **not** switch back to "facts" for a paragraph that narrates facts while evaluating them (§5).

If you must override the tool's start, re-run `segment <file> <work> --region-start <char>` (single file) so the header reflects it; the
validator then warns about spans before it.

## 2. Paragraph breaks flattened (whole file on one line, or blank lines missing)

The tool builds **paragraph blocks from the judgment's own paragraph numbers** (`33.`, `34.` …): a numbered paragraph plus its continuation
lines is one block. If a long block contains the *sequential* numbers `34. … 35. … 36. …` inline, it is split at them — so a flattened
file recovers its paragraphs.
* The status line shows the number of paragraphs; **`WARNING: only n paragraph(s)… looks flattened`** means recovery failed (no usable
  numbers). Then there is nothing to enforce "spans stay inside a paragraph": keep spans short (≤ ~1,500 characters), end them at sentence
  boundaries, and start a new span at every change of speaker.
* Headings glued into flattened text are not recognised as headings, except all-capital ones (flag `H`). Do not put a heading's words into a
  span: end the previous span at the last full sentence (use `{"end_before": "…"}` if the heading sits inside a unit).
* Unnumbered documents with real blank lines between paragraphs are split on the blank lines; unnumbered documents with neither get one block per line.

## 3. Encoding artifacts (`â€™`, `â€“`, `Ã©`) and Windows line endings

* **Mojibake** (UTF-8 text that was decoded as cp1252 and saved again) is **repaired automatically**: `â€™` → `’`, `â€“` → `–`,
  `Ã©` → `é`, `Â£` → `£`. The status line says `REPAIRED n mojibake`. The output offsets then refer to the repaired text (`"repairs": n` in the JSON).
  Your quoted anchor phrases must be copied from the **unit table** (already repaired), not from the original file. `--no-repair` turns it off.
* Other encodings: UTF-8 BOM is removed; UTF-16 and cp1252/latin-1 files are decoded (a note appears in the header).
* **CRLF**: every `\r\n` counts as **one** character in all offsets. This matches Python's text-mode `open(...).read()` — i.e. how gold files and
  evaluators on Windows see the text. Outputs made on raw CRLF offsets: `am_tools.py rebase`.
* **Console errors** such as `UnicodeEncodeError: 'charmap' codec can't encode…` on Windows: fixed in the scripts (UTF-8 output is forced). If you
  still see garbled characters in your own terminal, set `PYTHONUTF8=1`; the files themselves are always written as UTF-8.

## 4. Truncated text (file ends in the middle of a sentence)

The header shows `# WARNING … TRUNCATED` and the last unit carries flag `T`.
* Annotate the truncated last unit like any other: if it is part of an argument, include it in the span (`"u41"` covers the partial sentence).
  Do **not** invent the missing words and do **not** drop the span because the sentence is unfinished.
* Decide the label from what is there plus the paragraph's job (a half-finished Court sentence after "The Court considers that…" is still the Court's
  own position). If you cannot tell, use `APP`.
* Mention truncation in the run report. Truncation never changes the offset rules.
* A file truncated *before* the Law section (e.g. only the first 2,000 words of a long judgment) contains no reasoning: annotate nothing and report it.

## 5. Facts versus legal argument

Inside the Law section, ask of each paragraph: **what is this sentence doing for the legal conclusion?**

| If the sentence… | then |
|---|---|
| states what the complaint/claim/scope is (even briefly) | span (`APP`) |
| reports someone's argument, or the Commission's opinion, about how a norm applies | span (party's / `COMM` actor) |
| narrates a fact **and** the surrounding text uses it to apply or weigh the norm ("Out of forty-six contributors nineteen consented and 65 of 352 documents were released") | part of the argument's span (`APP`/`NEC`) |
| narrates domestic procedure or chronology with no evaluation ("The High Court heard the application on 22 February 1980") | `O`, if it stands alone; if it sits in the middle of a span keep it in |
| quotes a provision or earlier judgment verbatim (flag `Q`) | `O` — but the sentence **introducing** it ("…which reads:") is a span if it reports a claim |
| is a heading, signature, or part of the Art. 41/50 / costs sections (flag `L`) | `O` |

Because the Law section before just satisfaction is mostly reasoning (≈ 90 % of its plain sentences are inside spans in the tuning judgments), the default is to annotate; `O` needs a reason from the table.

## 6. Ambiguous labels

* `APP` vs `LEG`/`PUR`/`NEC` — use the **stage** of the paragraph (`02_label_descriptions.md` §1): before the justification test → `APP`; inside it → the step label, for every speaker.
* `APP` vs `PRE` — what is the sentence's job: announcing a general rule as settled law in the Court's own voice (`PRE`) or dealing with this case (stage label)? A citation never turns an applying sentence into `PRE`.
* Interpretation-looking passages (object and purpose, other Articles, travaux, comparative law, Vienna Convention) → `APP`, not `TEL/SYS/HIS/CMP`.
* Still tied → pick the label of the **paragraph's main move**, annotate the **whole paragraph** with it, and move on. Do not split a paragraph to
  hedge between two labels (that doubles the false positives).

## 7. Actor attribution when the Court reports submissions

See `03_actor_labels.md` ("Reported speech — common traps"). In one line: the speaker of the *reasoning* is the actor, not the author of the sentence;
the switch back to the Court's own voice starts a new span.

## 8. What not to annotate (checklist)

Headings (`H`) · quoted provisions/judgments (`Q`; except a quoted ECtHR precedent that continues the Court's own `PRE` sentence) · paragraph numbers · facts/procedure before the Law section · Art. 41/50 just satisfaction and costs (`L`) ·
the operative part "FOR THESE REASONS…" · separate / dissenting opinions · signatures · footnotes.
If the user explicitly wants these annotated, run `segment --include-tail` and annotate `L` units, and say so in the report.
