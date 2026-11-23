# 08 — Calibration: what a good annotation looks like (numbers from the corpus)

Use these as sanity targets after Pass 1. They come from two sources: the ECHR reference corpus (15,205 spans, 373 judgments) and 10 fully annotated judgments (267 spans) used to tune this skill (“10-doc” below). `am_tools.py validate` prints the same statistics for your output.

## Targets per judgment (Law section only)

| Quantity | Typical | Worry if |
|---|---|---|
| spans per judgment | 10-doc: 14–40 (≈ 1.5 per 1,000 chars of the annotatable Law section); corpus mean ≈ 41 | > 2× or < ½× |
| average span length | ≈ 570 characters (median ≈ 335) | < 250 → over-splitting |
| share of annotatable Law-section text inside spans (just-satisfaction/costs excluded) | 10-doc: 47–95 %, typically ≈ 75 % | < 40 % or > 90 % |
| paragraphs covered by exactly one whole-paragraph span | ≈ 58 % of annotated paragraphs | |
| share of `APP` | 57.1 % (corpus: 8,688 of 15,205), same in the 10-doc set | > 80 % (no justification steps found) or < 40 % |
| `NEC` | corpus 12.9 % (1,958), 10-doc 12 % | |
| `LEG` / `PUR` | corpus 3.4 % (513) / 1.8 % (271); 10-doc 10 % / 4 % (more in judgments with a qualified-right justification test) | |
| `PRE` | corpus 13.3 % (2,015), 10-doc 6 % | > 20 % → citations over-labelled as `PRE`; 0 in a judgment with general-principles paragraphs → under-used |
| `DEC` | corpus 8.1 % (1,236), 10-doc 7 % | > 15 % → closing sentences over-labelled |
| `NCP` | corpus 1.7 % (264) | |
| `DIS`, `MOA`, `TEL`, `SUI`, `CMP`, `TXT`, `SYS`, `OVR` | corpus 88, 67, 50, 25, 13, 10, 5, 2 spans of 15,205 (0.6 % … 0.01 %) | used without the strict trigger |
| `HIS` | 0 in the corpus | any use |
| actors | 10-doc: ECHR 60 %, Government 15 %, applicant 14 %, Commission 10 %, third party 0 %; corpus: ECHR 65 %, applicant 16 %, Government 16 %, third party 1.4 %, Commission 1.1 % | `ECHR` on a pure "The Government argued…" span; party/Commission actor on a sentence whose subject is the Court |

## Caveats on using this file

* Gold annotators skip some sentences entirely (and whole just-satisfaction sections); the skill copies the *systematic* skips (headings, quotations, Art. 41/50, costs) and otherwise annotates by the rules.
* The 10-doc figures were used to set the rules, so they are in-sample; treat them as priors, not as a test result.
* Numbers are for ECHR Law sections; short excerpts (< 3,000 chars) can differ widely.
