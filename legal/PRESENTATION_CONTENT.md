# Legal Argument Mining for NCLAT Decisions

Slide-ready content for the upcoming evaluation.

## Slide 1 — Title

### Building an Argument-Mining and Legal-Research Assistant for NCLAT Decisions

**Project objective:** Convert Indian tribunal decisions into structured legal arguments and use those arguments to support faster, evidence-grounded case preparation.

**Presenter:** `<name>`  
**Date:** `<evaluation date>`

---

## Slide 2 — Problem statement and project aims

### PS1 — Reliable argument mining for NCLAT

Build an LLM-based architecture to extract and classify different argument components from NCLAT data.

### PS2 — Evidence-grounded legal assistant

Use the structured NCLAT arguments to build a chatbot that helps lawyers retrieve relevant documents and evidence, compare arguments, trace answers to source passages, and prepare cases more efficiently.

---

## Slide 3 — Proposed system pipeline

```text
Legal websites and tribunal repositories
                ↓
Document collection and metadata extraction
                ↓
PDF/text cleaning and normalization
                ↓
Human annotation of argumentative components
                ↓
Training and evaluation dataset
                ↓
Argument-mining model or LLM ensemble
                ↓
Structured arguments with source offsets
                ↓
Evidence-grounded retrieval and chatbot
```

The most important design principle is traceability: every extracted argument must remain linked to the exact source document and text span from which it was obtained.

---

## Slide 4 — Work completed: legal-document collection

### Part A — Indian Kanoon and NCLT/NCLAT

#### Indian Kanoon

**Advantages**

- Documents could be downloaded directly in text format.
- Judgment pages included hyperlinks to laws and authorities used in the case.
- The website provided a useful document-level classification of sections such as facts, issues, arguments, and conclusions.
- This classification was useful for exploration, but not reliable enough to serve as a benchmark or gold-standard annotation.

**Major limitation**

- The downloaded text was heavily corrupted and ambiguous.
- The corruption was serious enough to affect preprocessing, span alignment, and downstream model evaluation.
- As a result, Indian Kanoon was rejected as the primary source for the final dataset.

Source: [Indian Kanoon](https://indiankanoon.org/)

#### NCLT/NCLAT

- The NCLT/NCLAT order-and-judgment interface provided a relevant source for tribunal decisions.
- It had useful date-wise and bench-wise retrieval properties similar to the document repositories considered for the project.
- However, the site required CAPTCHA-protected interaction.
- Documents could not be collected through a fully automated web-scraping workflow.

Source: [NCLT order and judgment search](https://nclt.gov.in/order-judgement-date-wise)

**Part A conclusion:** Indian Kanoon was useful for understanding document structure and available classifications, but its text quality was insufficient. NCLT/NCLAT was relevant but not automatically accessible because of CAPTCHA protection.

### Part B — IBBI

#### IBBI order repository

**Advantages**

- Provides high-quality case documents in PDF format.
- The PDFs are substantially clearer and more suitable for text extraction than the Indian Kanoon text downloads.
- Paginated tribunal sections can be traversed systematically.
- PDF links and metadata such as order date, subject, remark, source URL, and local filename can be collected.
- A unified CSV was created to support searching, filtering, and later dataset construction.

**Limitations**

- The documents do not provide argument-mining labels.
- The website does not directly provide hyperlinks to all laws used in each case.
- Some PDFs are very short because they describe matters that were closed, disposed of, or placed on hold.
- These short documents contain too little argumentative material for the training dataset.

**Filtering decision**

- A minimum PDF-size filter was introduced to remove documents that were too short to contain useful argumentative content.
- This simple filter addressed the main data-quality problem without creating a major loss of useful cases.

Sources: [IBBI orders](https://ibbi.gov.in/orders), [IBBI NCLAT orders](https://ibbi.gov.in/orders/nclat)

**Part B conclusion:** IBBI was selected as the most practical primary source because its PDFs are clear and downloadable at scale. Its missing annotations and law hyperlinks will be addressed during the annotation and metadata-enrichment stages.

---

## Slide 5 — Expert validation and annotation platform

### Planned role of legal experts

Law experts will be involved in two parts of the project:

- validate a representative sample of the model outputs from the experiments;
- annotate and validate selected NCLAT documents for the project’s argument-mining dataset.

The expert-validated NCLAT annotations can be divided into:

- few-shot training examples for prompt-based experiments;
- validation examples for comparing model variants;
- held-out test examples for final evaluation.

This creates a human-checked reference standard instead of relying only on automatically generated labels.

### Annotation-platform review

To support the annotation workflow, two platforms were considered:

- [INCEpTION](https://inception-project.github.io/)
- [Doccano](https://github.com/doccano/doccano)

Both platforms are capable of supporting the required annotation task.

<!-- ### Platform comparison

**INCEpTION — preferred platform**

- Provides a more solid annotation structure.
- Better suited to multiple annotation layers and more complex legal argument schemes.
- Easier to organize a structured annotation project as the task grows.
- Better fit for expert validation, adjudication, and future argument relations.

**Doccano — practical alternative**

- Easy to install, access, and use.
- Provides a simple workflow for importing data and downloading annotations.
- Suitable for a quick pilot or a relatively simple span-labeling task. -->

### Decision

- INCEpTION is preferred because it provides stronger structure and better supports the expected legal annotation use cases.
- Doccano remains a valid alternative when quick setup and straightforward data export are the main priorities.

---

## Slide 6 — Literature review: manually annotated legal arguments

### Paper introduction

The paper [Mining Legal Arguments in Court Decisions](https://doi.org/10.1007/s10506-023-09361-y) studies how legal arguments can be identified and classified in European Court of Human Rights (ECHR) judgments.

The authors argue that legal argumentation is richer than a simple distinction between claims and premises. Legal decisions contain different types of interpretive, procedural, institutional, proportionality, precedent, and case-application arguments.

### Dataset, annotation, and models

- The authors compiled 373 ECHR decisions containing approximately 2.3 million tokens and 15,205 argument spans.
- The annotation scheme contains 16 legal argument types, represented in BIO format and released in UIMA-XMI format with span offsets and labels.
- The dataset was divided into 299 training, 37 development, and 37 test decisions.
- The annotated data were used to train and evaluate RoBERTa-Large, Legal-BERT, Leg-RoBERTaL-13k, and Leg-RoBERTaL-15k.

### Why this paper and dataset are important for this project

The dataset gives us a reliable legal reference for training, testing, and comparing encoder models and LLMs, while also showing how legal-domain pretraining can improve argument-mining performance.

The ECHR dataset is being used as a methodological reference and experimental benchmark while the NCLAT corpus is being developed. The final NCLAT system will require a new expert-validated dataset because ECHR and NCLAT use different legal domains and may require different argument categories.

### Reference resources

- Paper: [Mining Legal Arguments in Court Decisions](https://doi.org/10.1007/s10506-023-09361-y)
- Earlier preprint: [arXiv:2208.06178](https://arxiv.org/abs/2208.06178)
- Code and data: [trusthlt/mining-legal-arguments](https://github.com/trusthlt/mining-legal-arguments)
- Related corpus: [ECHR: Legal Corpus for Argument Mining](https://aclanthology.org/2020.argmining-1.8/)

---

## Slide 7 — Literature review: ILDC for court judgment prediction and explanation

### Paper introduction

The paper [ILDC for CJPE: Indian Legal Documents Corpus for Court Judgment Prediction and Explanation](https://arxiv.org/abs/2105.13562) studies how Indian Supreme Court judgments can be used to predict case outcomes and generate explanations for those predictions.

This paper does not directly solve the argument-mining task, but it provides a useful direction for our project: structured or argument-related information can support downstream prediction and explanation tasks on Indian legal documents.

### Dataset, task, and methods

- ILDC contains approximately 35,000 Indian Supreme Court cases; a separate test portion contains expert-written explanations.
- The task is Court Judgment Prediction and Explanation (CJPE): predict the case outcome and identify the text that supports the prediction.
- The paper compares classical models such as regression and SVMs, hierarchical models for long judgments, transformer models, ensembles, and a hierarchical occlusion-based explanation method.

### Relevance to this project

The paper shows how structured information from Indian legal documents can support prediction and explanation, giving us a direction for using NCLAT argument-mining outputs in judgment analysis, case comparison, and evidence-grounded chatbot responses.

### Future work

- Revisit whether Indian Kanoon preprocessing can recover useful metadata or law links for auxiliary analysis.
- Consider the [WebAnno framework](https://webanno.github.io/webanno/) as another platform for structured legal annotation.

### Reference

- [ILDC for CJPE — arXiv:2105.13562](https://arxiv.org/abs/2105.13562)

---

## Slide 8 — Literature review: generative argument detection

The paper [Compact Prompting in Instruction-tuned LLMs for Joint Argumentative Component Detection](https://arxiv.org/abs/2603.03095) reframes argumentative component detection as text generation.

Instead of asking for an unrelated JSON schema, the model reproduces the input and inserts tags such as:

```text
<premise>supporting or attacking evidence</premise>
<claim>central assertion</claim>
```

The associated code is available in [sofianeElguendouz/ITFACD](https://github.com/sofianeElguendouz/ITFACD).

### Encoder and decoder representations

For an encoder model, the input is paired with BIO token labels:

```text
Input text:       The government should fund healthcare because people need it
BIO labels:       B-C I-C I-C I-C I-C B-P I-P I-P I-P
Encoder pair:     (text, BIO-labelled text)
```

For a decoder or text-generation model, the same annotation can be represented as tagged text:

```text
<claim>The government should fund healthcare</claim><premise>because people need it</premise>
Decoder pair:     (text, tagged output)
```

The encoder predicts labels for tokens, while the decoder generates the text with argument tags inserted.

### Relevance to this project

This approach gives us a clear alternative to forcing an instruction-tuned model to produce JSON: generate tagged text, preserve the original response, and align the tagged spans back to the source document. The final NCLAT taxonomy will still need to reflect tribunal-specific legal components.

---

## Slide 9 — Additional literature: LLM benchmarking and ensembles

| Paper | Main contribution | Relevance to this project |
|---|---|---|
| [A comprehensive study of LLM-based argument classification](https://link.springer.com/article/10.1007/s00521-026-12125-9) | Benchmarks multiple modern LLMs on argument-classification datasets and compares their performance. | Provides guidance for fair model comparison, prompt design, and evaluation of our candidate models. |
| [LLM Chain Ensembles for Scalable and Accurate Data Annotation](https://arxiv.org/abs/2410.13006) | Routes easy examples to earlier models and sends uncertain examples to later, stronger models; combines outputs using confidence scores. | Provides a possible architecture for our ensemble while reducing the cost of running every model on every document. |
| [Argument Component Segmentation with Fine-Tuned Large Language Models](https://aclanthology.org/2026.findings-eacl.272/) | Focuses mainly on Argument Component Classification (ACC) and also addresses Argument Component Segmentation (ACS) using paired tags. | Supports separating span detection from classification: first identify the component boundaries, then assign the argument label. |

**Key terms:** ACC classifies an already identified argument component; ACS identifies argument boundaries in unsegmented text.

---

## Slide 10 — Models evaluated so far

The initial experiments used zero-shot prompting without fine-tuning.

| Model | Source | Role in experiments |
|---|---|---|
| Saul-7B-Instruct-v1 | [Hugging Face](https://huggingface.co/Equall/Saul-7B-Instruct-v1) | Legal-domain instruction model |
| SaulLM-54B-Instruct | [Hugging Face](https://huggingface.co/Equall/SaulLM-54B-Instruct) | Larger legal-domain model planned for comparison |
| law-chat | [Hugging Face](https://huggingface.co/AdaptLLM/law-chat) | Legal-domain instruction model |
| Llama-3-8B-Instruct | [Hugging Face](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct) | Instruction-tuned generative baseline |

The experiments were designed to compare individual models first, followed by a possible ensemble.

---

## Slide 11 — Experimental findings so far

### Experiment 1: Saul-7B with the full document

- The full document was sent in one prompt.
- The response was ambiguous, sometimes unrelated, and often not valid JSON for the requested task.

**Finding:** Full-document prompting was unreliable.

### Experiment 2: Saul-7B with chunks

- The document was split into 1,000-word chunks with 100-word overlap.
- JSON quality improved and some classifications were correct.
- The model often repeated the same label, and overlap caused duplicate spans.

**Output snapshot:**

```json
{
  "arguments": [
    {
      "text": "On 21 November 2005 B was arrested and detained ...",
      "label": "Test of the principle of proportionality—Legal basis"
    },
    {
      "text": "On 20 December 2005 the State Attorney's Office indicted B ...",
      "label": "Test of the principle of proportionality—Legal basis"
    }
  ]
}
```

**Finding:** Chunking improved the response, but deduplication, prompt refinement, and label calibration are still needed.

### Experiment 3: law-chat with chunked text

- The model followed the JSON structure more closely.
- The response contained placeholder values:

```json
[
  {
    "text": "exact copied span",
    "label": "one allowed label"
  }
]
```

- No actual span or useful label was produced.

**Finding:** Correct formatting alone does not demonstrate successful argument mining. The prompt must match the model’s instruction-tuning objective.

---

## Slide 12 — PDF text extraction with OCR fallback

The project already includes a [PDF text extractor](E:/Docs/intern/AAintern/legal/experimental_setup/backup_before_inline_refactor/src/pdf_text.py) that:

- extracts page-level text and metadata;
- uses OCR for pages with little or no extractable text;
- processes PDF directories in batches and saves structured JSON.

This provides the preprocessing layer for converting IBBI and future NCLAT PDFs into text for cleaning, annotation, chunking, and argument mining. The implementation uses PyMuPDF (`fitz`) with `pytesseract` OCR fallback.

---

## Slide 13 — Current technical lessons

- A long legal document cannot be assumed to fit reliably into one model prompt.
- Chunking must preserve document offsets and support duplicate removal.
- JSON validity is not the same as extraction quality.
- Placeholder outputs must be detected explicitly.
- A model can produce well-formed output while returning no useful prediction.
- Legal-domain labels need clear definitions and examples.
- ECHR labels cannot be transferred to NCLAT without legal and annotation analysis.
- Model outputs must be evaluated at both span level and label level.
- The source document must remain available for every generated result.

---

## Slide 14 — Future work: dataset and model selection

1. Build a proper NCLAT dataset from the IBBI documents.
2. Divide the data into train, validation, and test sets while preserving the frequency of important case outcomes, such as dismissed cases, accepted appeals, and cases where the applicant or defendant succeeds.
3. Decide the argument-component classes according to the project’s use cases, while identifying a core set that can be applied more generally across legal domains.
4. Systematically compare encoder and decoder LLM capabilities and select the models most useful for NCLAT argument mining.
5. Study additional approaches beyond standard LLM prompting, including LLM ensembles, instruction-tuned models, SVMs, occlusion-based models, and other architectures that may produce significant results.

---

## Slide 15 — Future work: architecture, validation, and project direction

6. Build a proper pipeline or agentic architecture combining multiple LLMs and specialized components for NCLAT argument mining.
7. Involve qualified legal experts to review the dataset and validate the automatically generated argument annotations.
8. Refine the second-stage problem statement after the NCLAT argument-mining task and the available evidence structure are better understood.

The refined second stage will define how the validated argument representation supports the legal-research assistant and case-preparation workflow.

---

## Slide 16 — Evaluation and reliability criteria

### Argument-mining evaluation

- Exact span precision, recall, and F1.
- Overlap span precision, recall, and F1.
- Per-class precision, recall, and F1.
- Macro-F1 to expose rare-class performance.
- Confusion matrix for argument types.
- Inter-annotator agreement as a human reference.

### Chatbot evaluation

- Retrieval recall and precision.
- Citation correctness.
- Evidence completeness.
- Answer faithfulness to cited documents.
- Legal-expert usefulness rating.
- Hallucination and unsupported-claim rate.
- Time saved during case preparation.

### Safety requirement

The system should clearly distinguish retrieved legal authority, model-generated synthesis, and unresolved uncertainty. Final legal decisions remain with qualified legal professionals.

---

## Slide 17 — Expected contribution

The project aims to contribute:

- a cleaned and searchable NCLAT legal-document collection;
- a legally motivated annotation scheme for NCLAT argument mining;
- a reproducible comparison of legal and general instruction-tuned models;
- an argument representation linked to original evidence;
- an evaluation protocol for span, label, and evidence quality;
- a prototype chatbot for evidence-grounded legal research.

### Closing message

The project moves from document collection to structured legal reasoning: first identifying the arguments in NCLAT decisions, then using those structured arguments to support faster and more transparent legal research.

---

## Reference links

### Legal sources and collectors

- [Indian Kanoon](https://indiankanoon.org/)
- [IBBI orders](https://ibbi.gov.in/orders)
- [IBBI NCLAT orders](https://ibbi.gov.in/orders/nclat)
- [NCLT order and judgment search](https://nclt.gov.in/order-judgement-date-wise)

### Annotation tools

- [INCEpTION](https://inception-project.github.io/)
- [Doccano](https://github.com/doccano/doccano)

### Dataset and literature

- [ECHR argument-mining dataset and code](https://github.com/trusthlt/mining-legal-arguments)
- [Mining Legal Arguments in Court Decisions](https://doi.org/10.1007/s10506-023-09361-y)
- [Mining Legal Arguments in Court Decisions — arXiv](https://arxiv.org/abs/2208.06178)
- [ECHR: Legal Corpus for Argument Mining](https://aclanthology.org/2020.argmining-1.8/)
- [Using Argument Mining for Legal Text Summarization](https://doi.org/10.3233/FAIA200862)
- [A Decade of Legal Argumentation Mining](https://transpire.ucd.ie/pubs/Zhang2022a.pdf)
- [Compact Prompting in Instruction-tuned LLMs for Joint Argumentative Component Detection](https://arxiv.org/abs/2603.03095)
- [ITFACD code repository](https://github.com/sofianeElguendouz/ITFACD)

### Models

- [Equall/Saul-7B-Instruct-v1](https://huggingface.co/Equall/Saul-7B-Instruct-v1)
- [Equall/SaulLM-54B-Instruct](https://huggingface.co/Equall/SaulLM-54B-Instruct)
- [AdaptLLM/law-chat](https://huggingface.co/AdaptLLM/law-chat)
- [Meta-Llama-3-8B-Instruct](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct)
