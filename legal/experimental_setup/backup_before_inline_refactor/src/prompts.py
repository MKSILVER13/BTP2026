import json
from .labels import LABELS

SCHEMA={"arguments":[{"text":"exact copied span","label":"one canonical label"}]}

def make_prompt(text, demonstrations=None):
    labels="\n".join("- "+x for x in LABELS)
    examples=""
    if demonstrations:
        examples="\nExamples (copy spans exactly):\n"+"\n".join("INPUT:\n%s\nOUTPUT:\n%s"%(d["text"],json.dumps({"arguments":d["arguments"]},ensure_ascii=False)) for d in demonstrations)
    return f"""Extract every argumentative component from the legal text. Return JSON only, with no markdown. Copy each span exactly from the input and assign exactly one label. Do not infer relations or actors. Use [] when no argument is present.

Allowed labels:
{labels}

Required schema: {json.dumps(SCHEMA, ensure_ascii=False)}
{examples}
INPUT:
{text}
OUTPUT:"""
