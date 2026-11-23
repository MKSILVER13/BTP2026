# Legal argument extraction experiments

This directory contains the second-stage experiments for detecting argumentative spans and assigning one of the 16 ECHR argument classes. The notebooks are intentionally prepared but do not contain result values: run them after installing the dependencies and then record runtime, memory, metrics, and observations in the metadata cells.

## Contents

| Notebook | Model | Purpose |
|---|---|---|
| `01_saul_7b_instruct.ipynb` | `Equall/Saul-7B-Instruct-v1` | Individual zero-shot and fixed few-shot evaluation |
| `02_saullm_54b_instruct.ipynb` | `Equall/SaulLM-54B-Instruct` | Individual evaluation; Transformers or optional vLLM |
| `03_law_chat.ipynb` | `AdaptLLM/law-chat` | Individual evaluation |
| `04_paper_llama3_8b_instruct.ipynb` | `meta-llama/Meta-Llama-3-8B-Instruct` | The instruction-tuned model selected from the compact-prompting paper |
| `05_ensemble.ipynb` | all four outputs | Fusion, validation-weighted voting, and LLM refinement |

The fourth model is an explicit assumption: the cited paper evaluates several open-weight models and highlights Llama-3-8B-Instruct. Change `MODEL_ID` in notebook 04 if a different paper model is required.

## Recommended extractor

`src/pdf_text.py` uses PyMuPDF (`fitz`) first. It preserves page boundaries and is fast for born-digital PDFs. Pages with too little extractable text can optionally be sent through Tesseract OCR. OCR is opt-in because it is slower and may introduce recognition noise.

## Data and labels

Clone or download the companion repository into a local directory:

```text
https://github.com/trusthlt/mining-legal-arguments
```

The notebooks are preconfigured with the local checkout path. The loader reads the repository's official XMI annotations and maps its `train`, `val`, and `test` directories to the experiment's `train`, `dev`, and `test` names.

When the first notebook cell runs, it creates `processed_echr/`. Each document has a unique `.txt` input file and matching `.json` annotation file, plus `manifest.json`. The prompt receives only the `.txt` content; the annotation file is used for evaluation. Output audits record the input and annotation filenames.

The 16 canonical labels are defined in `src/labels.py`. They are flat, non-overlapping, single-label span classes; relations and actor tags are deliberately excluded from this stage.

## Installation

```powershell
python -m venv .venv-experiments
.\.venv-experiments\Scripts\Activate.ps1
pip install -r experimental_setup\requirements.txt
```

For the 54B model, use a suitable GPU and optionally install vLLM separately. The notebooks default to Transformers and support 4-bit loading where available.

## Evaluation protocol

1. Use the repository's official train/dev/test split.
2. Run zero-shot and fixed few-shot prompts with the same schema and generation settings.
3. Use train only to select demonstrations, dev only to choose ensemble weights/settings, and test once after choices are frozen.
4. Compare span detection, exact/overlap span matching, class F1, and joint span+class F1.
5. Preserve raw model output and parsed JSON for auditability.

All result, runtime, memory, and error fields are left blank by design.

## References

- Saul-7B model card: https://huggingface.co/Equall/Saul-7B-Instruct-v1
- SaulLM-54B model card: https://huggingface.co/Equall/SaulLM-54B-Instruct
- law-chat model card: https://huggingface.co/AdaptLLM/law-chat
- Compact Prompting paper: https://arxiv.org/abs/2603.03095
- Mining Legal Arguments repository: https://github.com/trusthlt/mining-legal-arguments
- Label taxonomy source: `../Literature/s10506-023-09361-y.pdf`
