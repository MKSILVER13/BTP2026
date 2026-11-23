import json
from pathlib import Path
from .dataset import load_echr, load_prepared
from .prompts import make_prompt
from .inference import LocalGenerator, VLLMGenerator, parse_json, align_prediction
from .metrics import score

def choose_demos(records, n=2):
    return [{"text": r["text"][:2500], "arguments": [{"text": a["text"], "label": a["label"]} for a in r["annotations"]]} for r in records[:n]]

def run(model_id, data_root, split="test", few_shot=False, quantization=None, limit=None, output_path=None, backend="transformers", prepared_root=None):
    loader=(lambda s: load_prepared(prepared_root,s)) if prepared_root else (lambda s: load_echr(data_root,split=s))
    records=loader(split); demos=choose_demos(loader("train")) if few_shot else None
    if limit: records=records[:limit]
    generator=(VLLMGenerator(model_id) if backend == "vllm" else LocalGenerator(model_id, quantization=quantization)); predictions=[]; audit=[]
    for record in records:
        prompt=make_prompt(record["text"], demos); raw,seconds=generator.generate(prompt); parsed,status=parse_json(raw); pred,errors=align_prediction(record["text"],parsed)
        predictions.append(pred); audit.append({"id":record["id"],"input_file":record.get("input_file",""),"annotation_file":record.get("annotation_file",""),"raw_output":raw,"parsed":parsed,"predictions":pred,"errors":[status]+errors,"seconds":seconds})
    result={"model_id":model_id,"split":split,"few_shot":few_shot,"backend":backend,"metrics":score(records,predictions),"audit":audit}
    if output_path: Path(output_path).parent.mkdir(parents=True,exist_ok=True); Path(output_path).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result
