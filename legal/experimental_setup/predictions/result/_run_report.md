# Run report

- Input: `predictions/train`
- Output: `predictions/result`
- Files processed: 40; failures: 0.
- Mode: spans only; relations are empty.
- Total spans: 1,095.
- Annotation method: paragraph- and stage-based first pass from the segment tables; `001-57887` was manually reviewed. The other files have not been individually adjudicated, so treat their labels and actors as draft annotations.
- Quoted units, headings and low-priority Art. 41/50/costs sections were excluded.
- All 40 output files pass `batch-validate` with 0 structural errors. Structural validation checks offsets and schema, not label accuracy.
- Validator warnings remain for high Law-section coverage, long spans, APP-heavy label mixes, and occasional rare labels/no DEC; review these before treating the annotations as final.
- These are ECHR judgments; no actor remapping was needed.
- Truncated texts: 11; only visible text was annotated.

## Counts by type

- APP: 841
- DEC: 37
- LEG: 37
- NCP: 1
- NEC: 15
- PRE: 51
- PUR: 112
- TXT: 1

## Truncated files

- `001-57929.txt`
- `001-59221.txt`
- `001-59868.txt`
- `001-59998.txt`
- `001-60324.txt`
- `001-60431.txt`
- `001-60612.txt`
- `001-60733.txt`
- `001-60824.txt`
- `001-60891.txt`
- `001-60898.txt`
