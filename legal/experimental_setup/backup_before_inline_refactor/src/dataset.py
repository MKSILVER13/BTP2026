"""Permissive adapters for common Mining Legal Arguments data layouts."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import json
from .labels import LABELS

XMI_LABELS = {
    "Konsens der prozessualen Parteien": LABELS[0],
    "Wortlaut Auslegung": LABELS[1],
    "Historische Auslegung": LABELS[2],
    "Systematische Auslegung": LABELS[3],
    "Sinn & Zweck Auslegung": LABELS[4],
    "Rechtsvergleichung": LABELS[5],
    "Verhältnismäßigkeitsprüfung – Rechtsgrundlage": LABELS[6],
    "Verhältnismäßigkeitsprüfung – Legitimer Zweck": LABELS[7],
    "Verhältnismäßigkeitsprüfung – Geeignetheit": LABELS[8],
    "Verhältnismäßigkeitsprüfung – Angemessenheit": LABELS[9],
    "Overruling": LABELS[10],
    "Distinguishing": LABELS[11],
    "Einschätzungsspielraum": LABELS[12],
    "Vorherige Rechtsprechung des EGMR": LABELS[13],
    "Entscheidung des EGMR": LABELS[14],
    "Subsumtion": LABELS[15],
}

def _read(path):
    try:
        if path.suffix.lower() == ".jsonl": return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return None

def _text(obj):
    if isinstance(obj, dict):
        for key in ("text", "document", "raw_text", "content"):
            if isinstance(obj.get(key), str): return obj[key]
        for value in obj.values():
            found = _text(value)
            if found: return found

def _items(obj):
    if isinstance(obj, dict):
        for key in ("annotations", "arguments", "spans", "entities"):
            if isinstance(obj.get(key), list): return obj[key]
        for value in obj.values():
            found = _items(value)
            if found: return found
    return []

def _record(obj, split, source):
    text = _text(obj)
    if not text: return None
    anns=[]
    for item in _items(obj):
        if not isinstance(item, dict): continue
        label=item.get("label", item.get("class", item.get("type")))
        start=item.get("start", item.get("begin")); end=item.get("end", item.get("stop")); span=item.get("text", item.get("span"))
        if start is None and isinstance(span, str): start=text.find(span); end=start+len(span)
        if start is not None and end is not None and int(start) >= 0:
            start,end=int(start),int(end); anns.append({"start":start,"end":end,"text":text[start:end],"label":label})
    return {"id":str(obj.get("id", source.stem)),"split":split,"text":text,"annotations":anns,"source":str(source)}

def _load_xmi(path, split):
    root=ET.parse(path).getroot(); text=""; annotations=[]
    for element in root.iter():
        if element.tag.endswith("Sofa") and element.attrib.get("sofaString"):
            text=element.attrib["sofaString"]; break
    if not text: return None
    for element in root.iter():
        if not element.tag.endswith("LegalArgumentation"): continue
        label=XMI_LABELS.get(" ".join(element.attrib.get("ArgType", "").split()))
        if not label: continue
        start=element.attrib.get("begin"); end=element.attrib.get("end")
        if start is None or end is None: continue
        start,end=int(start),int(end)
        annotations.append({"start":start,"end":end,"text":text[start:end],"label":label})
    return {"id":path.stem,"split":split,"text":text,"annotations":annotations,"source":str(path)} if annotations else None

def load_echr(root, split=None):
    root=Path(root); records=[]
    # The official repository stores gold annotations as XMI and split membership
    # as data/{train,val,test}/agent/<document-id>.csv.
    split_name={"dev":"val","validation":"val"}.get(split,split) if split else None
    if (root/"gold_data").exists():
        split_dirs=[split_name] if split_name else ["train","val","test"]
        ids=set()
        for name in split_dirs:
            for csv in (root/"data"/name).rglob("*.csv") if (root/"data"/name).exists() else []:
                ids.add((name,csv.stem))
        for name,doc_id in sorted(ids):
            path=root/"gold_data"/(doc_id+".xmi")
            if path.exists():
                record=_load_xmi(path, "dev" if name=="val" else name)
                if record: records.append(record)
        if records: return records
    for path in root.rglob("*"):
        if path.suffix.lower() not in {".json", ".jsonl"}: continue
        inferred=next((s for s in ("train","dev","validation","test") if s in (path.stem+str(path.parent)).lower()), "unknown")
        current=split or inferred
        if split and current != split: continue
        data=_read(path)
        values=data if isinstance(data,list) else (data.get("data",data.get("documents",[])) if isinstance(data,dict) else [])
        if isinstance(values,dict): values=list(values.values())
        for value in values:
            rec=_record(value,current,path)
            if rec and rec["annotations"]: records.append(rec)
    if not records: raise RuntimeError("No annotated records found. Set DATA_ROOT to the repository checkout and inspect its gold_data layout.")
    return records

def prepare_echr_files(data_root, output_root):
    """Export one raw text file and one annotation JSON file per document."""
    output_root=Path(output_root); manifest=[]
    for split in ("train", "dev", "test"):
        text_dir=output_root/split/"texts"; annotation_dir=output_root/split/"annotations"
        text_dir.mkdir(parents=True,exist_ok=True); annotation_dir.mkdir(parents=True,exist_ok=True)
        for record in load_echr(data_root, split=split):
            text_file=text_dir/(record["id"]+".txt"); annotation_file=annotation_dir/(record["id"]+".json")
            text_file.write_text(record["text"],encoding="utf-8")
            annotation_file.write_text(json.dumps({"id":record["id"],"split":split,"annotations":record["annotations"],"source":record["source"]},ensure_ascii=False,indent=2),encoding="utf-8")
            manifest.append({"id":record["id"],"split":split,"input_file":str(text_file),"annotation_file":str(annotation_file)})
    (output_root/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    return manifest

def load_prepared(root, split):
    """Load the exported text/annotation pairs created by prepare_echr_files."""
    root=Path(root); records=[]
    for annotation_file in sorted((root/split/"annotations").glob("*.json")):
        annotation=json.loads(annotation_file.read_text(encoding="utf-8")); text_file=root/split/"texts"/(annotation_file.stem+".txt")
        record={"id":annotation["id"],"split":split,"text":text_file.read_text(encoding="utf-8"),"annotations":annotation["annotations"],"source":annotation.get("source",""),"input_file":str(text_file),"annotation_file":str(annotation_file)}
        records.append(record)
    if not records: raise RuntimeError("No prepared files found. Run prepare_echr_files first.")
    return records
