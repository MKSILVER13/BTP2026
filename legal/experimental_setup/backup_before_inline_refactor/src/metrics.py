from collections import defaultdict

def _match(pred,gold,labeled=True,overlap=False):
    used=set(); hits=0
    for p in pred:
        for i,g in enumerate(gold):
            if i in used or (labeled and p["label"]!=g["label"]): continue
            ok=(p["start"]==g["start"] and p["end"]==g["end"]) if not overlap else max(p["start"],g["start"])<min(p["end"],g["end"])
            if ok: used.add(i); hits+=1; break
    return hits

def score(records,predictions):
    totals=defaultdict(int); names=(("exact_joint",True,False),("overlap_joint",True,True),("span_exact",False,False),("span_overlap",False,True))
    for rec,pred in zip(records,predictions):
        for name,labeled,overlap in names:
            hit=_match(pred,rec["annotations"],labeled,overlap); totals[name+"_tp"]+=hit; totals[name+"_fp"]+=len(pred)-hit; totals[name+"_fn"]+=len(rec["annotations"])-hit
    result={}
    for name,_,_ in names:
        tp,fp,fn=totals[name+"_tp"],totals[name+"_fp"],totals[name+"_fn"]; p=tp/(tp+fp) if tp+fp else 0; r=tp/(tp+fn) if tp+fn else 0
        result[name]={"precision":p,"recall":r,"f1":2*p*r/(p+r) if p+r else 0}
    return result
