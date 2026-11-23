from collections import Counter, defaultdict
from .metrics import score
import json
from pathlib import Path

def load_prediction_file(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    return [[x for x in item.get("predictions", [])] for item in data.get("audit", [])]

def majority_fusion(predictions_by_model):
    """Fuse overlapping spans; label is the majority label, with model order as tie-break."""
    all_preds=[p for preds in predictions_by_model.values() for p in preds]
    groups=[]
    for pred in all_preds:
        group=next((g for g in groups if max(pred["start"],g[0]["start"]) < min(pred["end"],g[0]["end"])),None)
        if group is None:
            groups.append([pred])
        else:
            group.append(pred)
    result=[]
    for group in groups:
        labels=Counter(x["label"] for x in group); best=labels.most_common(1)[0][0]
        chosen=next(x for x in group if x["label"]==best); result.append(dict(chosen, support=len(group)))
    return result

def weighted_fusion(predictions_by_model, weights):
    groups=[]
    for model,preds in predictions_by_model.items():
        for pred in preds:
            group=next((g for g in groups if max(pred["start"],g[0]["pred"]["start"]) < min(pred["end"],g[0]["pred"]["end"])),None)
            item={"model":model,"pred":pred}
            if group is None: groups.append([item])
            else: group.append(item)
    result=[]
    for group in groups:
        candidates=defaultdict(float)
        for item in group: candidates[item["pred"]["label"]]+=weights.get(item["model"],1.0)
        label=max(candidates,key=candidates.get); chosen=next(x["pred"] for x in group if x["pred"]["label"]==label)
        result.append(dict(chosen, support=len(group), confidence=candidates[label]/sum(candidates.values())))
    return result

def derive_weights(dev_records, dev_predictions):
    return {model: score(dev_records,preds)["exact_joint"]["f1"] for model,preds in dev_predictions.items()}
