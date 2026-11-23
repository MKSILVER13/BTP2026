# Experiment protocol and record sheet

## Research question

Can instruction-tuned legal language models identify argumentative spans in ECHR judgments and map each span to the 16-category taxonomy from `s10506-023-09361-y.pdf` without fine-tuning? Argument relations and actor tags are out of scope.

## Input and expected output

Before inference, each notebook exports the official XMI data into `processed_echr/<split>/texts/<document-id>.txt` and `processed_echr/<split>/annotations/<document-id>.json`. The shared `manifest.json` records the pairing. The prompt uses the text file; the annotation JSON is retained as ground truth and is never sent to the model. Each audit record stores both filenames.

Each example supplies the full judgment text. The model must return JSON only:

```json
{"arguments": [{"text": "exact copied text", "label": "one canonical label"}]}
```

Predicted text is aligned back to character offsets in the input. Unmatched or unknown-label predictions are retained in the audit file and excluded from valid span scoring.

## Models and architecture

The Saul models are legal-domain causal language models: Saul-7B is Mistral-derived and SaulLM-54B is Mixtral-derived. law-chat is a Llama-2-based legal chat model. Notebook 04 uses `meta-llama/Meta-Llama-3-8B-Instruct`, selected from the instruction-tuned open models discussed in the compact-prompting paper. These are used as frozen generators with a chat prompt, not fine-tuned classifiers. The generation-as-structured-output design is inspired by “Compact Prompting in Instruction-tuned LLMs for Joint Argumentative Component Detection” (arXiv:2603.03095).

## Prompt conditions

- zero-shot: task instructions and the fixed label list;
- fixed few-shot: the same prompt plus demonstrations selected from train only;
- deterministic generation by default (`temperature=0`, fixed seed);
- exact copied spans, one label per span, no relations or actors.

## Splits and leakage control

Use the official Mining Legal Arguments train/val/test split; the code exposes `val` as `dev`. Train selects demonstrations. Dev selects ensemble weights and any thresholds. Test is evaluated once after decisions are frozen. Do not use test examples as demonstrations.

## Metrics

Report exact joint span+class precision/recall/F1 as the primary measure; exact span-only and overlap span-only as diagnostic measures; overlap joint F1; per-class macro/micro F1 and confusion matrix when the dataset adapter exposes all labels. Also record valid JSON rate, unmatched-span rate, unknown-label rate, average latency, total runtime, generated tokens, and peak memory.

## Blank run record

| Field | Value |
|---|---|
| Date / operator | |
| Dataset commit/version | |
| Split and number of documents | |
| Model revision | |
| Architecture / backend | |
| Prompt condition/version | |
| Demonstration IDs | |
| Quantization / device | |
| Generation settings | |
| Runtime / peak memory | |
| Exact joint P/R/F1 | |
| Overlap joint P/R/F1 | |
| Span-only P/R/F1 | |
| Per-class results | |
| Errors / invalid outputs | |
| Observations | |

## Reproducibility

Save raw outputs, parsed outputs, prompts/configuration, model revision, and the environment package versions. The notebooks intentionally leave output fields blank until the experiments are actually run.
