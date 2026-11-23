# Experimental Results Analysis

The experiments use the manually annotated ECHR argument-mining dataset from the [mining-legal-arguments GitHub repository](https://github.com/trusthlt/mining-legal-arguments).

The task was to identify argumentative spans and assign one of the 16 legal argument labels.

## ECHR argument-label taxonomy

The English labels used for analysis correspond to the following original German labels in the XMI annotations:

| No. | English label | Original German label |
|---:|---|---|
| 1 | Procedural arguments — Non-contestation by the parties | Konsens der prozessualen Parteien |
| 2 | Method of interpretation — Textual interpretation | Wortlaut Auslegung |
| 3 | Method of interpretation — Historical interpretation | Historische Auslegung |
| 4 | Method of interpretation — Systematic interpretation | Systematische Auslegung |
| 5 | Method of interpretation — Teleological interpretation | Sinn & Zweck Auslegung |
| 6 | Method of interpretation — Comparative law | Rechtsvergleichung |
| 7 | Test of the principle of proportionality — Legal basis | Verhältnismäßigkeitsprüfung – Rechtsgrundlage |
| 8 | Test of the principle of proportionality — Legitimate purpose | Verhältnismäßigkeitsprüfung – Legitimer Zweck |
| 9 | Test of the principle of proportionality — Suitability | Verhältnismäßigkeitsprüfung – Geeignetheit |
| 10 | Test of the principle of proportionality — Necessity/Proportionality | Verhältnismäßigkeitsprüfung – Angemessenheit |
| 11 | Institutional arguments — Overruling | Overruling |
| 12 | Institutional arguments — Distinguishing | Distinguishing |
| 13 | Institutional arguments — Margin of Appreciation | Einschätzungsspielraum |
| 14 | Precedents of the ECHR | Vorherige Rechtsprechung des EGMR |
| 15 | Decision of the ECHR | Entscheidung des EGMR |
| 16 | Application to the concrete case | Subsumtion |

## Model and resource notes

The following are approximate observations from the runs:

| Model | Model size | Quantization | Approximate execution time |
|---|---:|---|---:|
| `Equall/Saul-7B-Instruct-v1` | 7B parameters | 4-bit | About 100 seconds per execution |
| `AdaptLLM/law-chat` | 7B-class model | 4-bit | About 60-80 seconds per execution |

Downloading and running both models required approximately 30 GB of CPU storage and up to approximately 15 GB of GPU memory. The exact usage can vary with the selected document, chunk count, cache state, and hardware.

## Experiment 1 — Saul-7B with the full document

### Setup

`Equall/Saul-7B-Instruct-v1` received the complete legal document in one prompt.

### Prompt snapshot

```text
You are a legal argument mining assistant.
Extract every argumentative component from the legal document.
Return JSON only, with no Markdown or explanation.
Copy each predicted span exactly from the input document.
Assign exactly one allowed label to each span.

Allowed labels:
<16 legal argument labels>

DOCUMENT:
<complete legal document>

JSON OUTPUT:
```

### Output snapshot

The response did not follow the requested argument-mining schema. Instead of returning argument spans and the 16 labels, it attempted to extract other legal-document information such as cited cases and court decisions:

```json
{
  "cited_cases": [
    {
      "case_number": "24746/94",
      "case_name": "Hugh Jordan v. the United Kingdom",
      "court": "European Court of Human Rights",
      "date": "4 May 2001"
    }
  ],
  "court_decision": "The Court accepts that the applicant suffered ..."
}
```

Other responses were ambiguous or unstructured and did not provide the requested argument spans and labels.

### Decision

The full-document prompt was unsuccessful. Saul-7B did not reliably understand the task over the complete legal document and produced an unrelated or improperly structured response.

## Experiment 2 — Saul-7B with chunked text

### Setup

The same Saul-7B model was tested after dividing the document into chunks of 1,000 words with an overlap of 100 words between adjacent chunks.

### Prompt snapshot

```text
You are a legal argument mining assistant.
Extract every argumentative component from the document chunk.
Return JSON only, with no Markdown or explanation.
Copy each predicted span exactly from the input chunk.
Assign exactly one allowed label to each span.

Allowed labels:
<16 legal argument labels>

DOCUMENT CHUNK:
<1,000-word chunk>

JSON OUTPUT:
```

### Output snapshot

The response was closer to the requested JSON format and it identified some relevant argument classifications. However, it repeatedly assigned the same label to many different spans:

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
    },
    {
      "text": "On 22 May 2006 the indictment was extended ...",
      "label": "Test of the principle of proportionality—Legal basis"
    }
  ]
}
```

The overlap between chunks also caused the same spans to be repeated. Some chunks returned placeholder content instead of real predictions:

```json
{
  "arguments": [
    {
      "text": "exact copied span",
      "label": "one allowed label"
    }
  ]
}
```

### Decision

Chunking improved the output structure and allowed the model to identify some relevant classifications. However, the model still produced repeated labels, incomplete classifications, repeated spans, and occasional placeholder outputs.

The 1,000-word chunk size with 100-word overlap will be retained for the next experiments. Duplicate predictions must be merged using their document-level character offsets.

## Experiment 3 — Law-chat with chunked text

### Setup

`AdaptLLM/law-chat` was tested using 1,000-word chunks with 100-word overlap.

### Prompt snapshot

```text
You are a legal argument mining assistant.
Extract every argumentative component from the document chunk.
Return JSON only, with no Markdown or explanation.
Copy each predicted span exactly from the input chunk.
Assign exactly one allowed label to each span.

Allowed labels:
<16 legal argument labels>

DOCUMENT CHUNK:
<1,000-word chunk>

JSON OUTPUT:
```

### Output snapshot

Law-chat followed the requested JSON structure, but it did not produce actual predictions. It returned the schema’s placeholder values:

```json
[
  {
    "text": "exact copied span",
    "label": "one allowed label"
  }
]
```

This is syntactically JSON, but it contains no real extracted span and no real classification.

### Decision

The problem was primarily the prompt design. Law-chat is an instruction-tuned model, but it was given a generic 16-class JSON extraction prompt. The prompt did not give the model a task format that matched its instruction-tuning behavior.

The next version should use an instruction-style prompt and ask the model to reproduce the input text while inserting tags:

```text
<premise>supporting or attacking evidence</premise>
<claim>central assertion</claim>
```

The complete generated response should be preserved first, and span extraction should be performed afterward.

## Overall conclusions

1. Saul-7B failed to handle the full legal document and produced ambiguous, unrelated, or unstructured output.
2. Chunking improved Saul-7B’s JSON structure, but repeated labels, repeated spans, incomplete predictions, and placeholder responses remained.
3. Law-chat produced the correct JSON structure but returned only placeholder values, so it did not identify actual spans or labels.
4. The 1,000-word chunk size with 100-word overlap will be used in the next experiments.
5. Prompt design must match the model’s instruction-tuning objective. For instruction-tuned argument-mining models, generative span tagging is more appropriate than forcing a generic JSON schema.
