import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IN_DIR = ROOT / "train"
WORK = ROOT / "work"
OUT = ROOT / "result"
TOOLS = Path(r"C:\Users\bilas\.codex\skills\legal-argument-mining\scripts\am_tools.py")
LINE = re.compile(r"^u(\d+)\s+p(\d+)\s+(.*?)\s*\|\s*(.*)$")

def actor_for(text):
    s = text.lstrip()
    if re.match(r"(?:the )?court\b|in the court's view\b|it is (?:clear|plain|true|apparent)\b|there (?:has|was|is|can)\b", s, re.I):
        return "ECHR"
    if re.match(r"(?:before (?:the )?(?:commission|convention institutions) )?(?:all \w+ )?(?:the )?(?:(?:first|second|third|fourth|fifth|sixth) )?applicants?\b.{0,50}\b(?:alleged|argued|claimed|complained|contended|maintained|submitted|considered|asserted|did not|could not|was of the view|reasoned|denied|disputed|accepted|objected)\b", s, re.I) or re.match(r"in the applicants?'s? (?:submission|view|opinion)\b", s, re.I) or re.match(r"(?:mr|mrs|ms|miss)\s+[A-Z][\w'’.-]*\s+(?:alleged|argued|claimed|complained|contended|maintained|submitted|considered|asserted|did not|could not|was of the view|reasoned|denied|disputed|accepted|objected)\b", s):
        return "APPL"
    if re.match(r"(?:the )?(?:respondent )?government\b|for the government\b|according to the government\b|in the government['’]s (?:submission|view|opinion)\b", s, re.I):
        return "STATE"
    if re.match(r"(?:the )?commission\b|the delegate\b|for the commission\b|according to the commission\b", s, re.I):
        return "COMM"
    if re.match(r"(?:the )?(?:third.party interveners?|intervening government|intervener)\b", s, re.I):
        return "THIRD"
    return "ECHR"

def label_for(text, stage, actor):
    s = " ".join(text.split())
    if actor == "ECHR" and re.search(r"\b(?:there has accordingly been|there has therefore been|there has been (?:no )?violation|there was (?:no )?violation|in conclusion there (?:has|was)|the court thus concludes|the court concludes|the court finds that there (?:has|was)|no issue arises under)\b", s, re.I) and not re.search(r"does not consider it necessary to examine", s, re.I):
        return "DEC"
    if re.match(r"(?:it is common ground|it was not contested|it is not disputed|neither (?:party|the parties) contested|the government did not dispute)\b", s, re.I) and len(s) < 350:
        return "NCP"
    if actor == "ECHR" and re.match(r"(?:the court )?(?:reiterates|recalls|has (?:consistently|repeatedly) held|according to its established case-law|it is well established)\b", s, re.I):
        return "PRE"
    if re.match(r"(?:as regards|with regard to|in relation to) the (?:word|term|expression)\b|\b(?:english|french) text\b", s, re.I):
        return "TXT"
    if re.search(r"\bmargin of appreciation\b", s, re.I) and re.match(r"(?:the )?(?:contracting states|state|national authorities)|\ba wide margin\b|\ba certain margin\b", s, re.I):
        return "MOA"
    return stage

def heading_stage(text, stage):
    h = text.lower()
    if any(x in h for x in ("in accordance with the law", "prescribed by law", "lawfulness", "quality of the law")):
        return "LEG"
    if "legitimate aim" in h or "legitimate purpose" in h:
        return "PUR"
    if any(x in h for x in ("necessary in a democratic society", "necessity", "proportionality", "fair balance")):
        return "NEC"
    if any(x in h for x in ("the law", "alleged violation", "interference", "applicability", "general approach", "scope of")):
        return "APP"
    return stage

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(IN_DIR.glob("*.txt"))
    failures = []
    skipped = []
    processed = []
    for src in files:
        dst = OUT / (src.stem + ".am.json")
        # 57887 was manually annotated and reviewed in the active session.
        if dst.exists() and src.stem == "001-57887":
            skipped.append(src.name)
            continue
        units_path = WORK / (src.stem + ".units.txt")
        rows = []
        quote_balance = 0
        quote_active = False
        for line in units_path.read_text(encoding="utf-8-sig").splitlines():
            m = LINE.match(line)
            if m:
                u, p, prefix, text = m.groups()
                flags_match = re.search(r"\)\s*([A-Z]*)\s*$", prefix)
                flags = flags_match.group(1) if flags_match else ""
                is_quoted = "Q" in flags or quote_active
                if "Q" in flags and not quote_active:
                    quote_active = True
                    quote_balance = 0
                if quote_active:
                    quote_balance += text.count('"') + text.count("“") - text.count("”")
                    if quote_balance % 2 == 0 and (text.count('"') or text.count("“") or text.count("”")):
                        quote_active = False
                        quote_balance = 0
                    elif quote_balance < 0:
                        quote_active = False
                        quote_balance = 0
                rows.append({"u": int(u), "p": int(p), "flags": flags, "quoted": is_quoted, "text": text})
        stage = "APP"
        para = {}
        for row in rows:
            if "H" in row["flags"] or re.match(r"^[A-Z]\.\s+", row["text"]):
                stage = heading_stage(row["text"], stage)
                continue
            para.setdefault(row["p"], []).append(row)
        out_rows = []
        n = 1
        for p, items in para.items():
            # Recover the active stage from the nearest preceding heading.
            p_first = items[0]["u"]
            local_stage = "APP"
            for row in rows:
                if row["u"] >= p_first:
                    break
                if "H" in row["flags"] or re.match(r"^[A-Z]\.\s+", row["text"]):
                    local_stage = heading_stage(row["text"], local_stage)
            run = []
            runs = []
            for item in items:
                if item["quoted"] or "L" in item["flags"] or "H" in item["flags"] or re.match(r"^[A-Z]\.\s+", item["text"]):
                    if run:
                        runs.append(run)
                        run = []
                else:
                    run.append(item)
            if run:
                runs.append(run)
            for run in runs:
                first = run[0]["u"]
                last = run[-1]["u"]
                body = " ".join(x["text"] for x in run)
                # A gap is a quotation or excluded unit; never include it in a unit range.
                segments = []
                seg = [run[0]]
                for item in run[1:]:
                    if item["u"] == seg[-1]["u"] + 1:
                        seg.append(item)
                    else:
                        segments.append(seg)
                        seg = [item]
                segments.append(seg)
                actor = actor_for(body)
                label = label_for(body, local_stage, actor)
                for seg in segments:
                    rng = f"u{seg[0]['u']}-u{seg[-1]['u']}" if len(seg) > 1 else f"u{seg[0]['u']}"
                    out_rows.append([n, rng, label, actor])
                    n += 1
        scratch = WORK / (src.stem + ".jsonl")
        scratch.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in out_rows), encoding="utf-8")
        build = subprocess.run(["python", str(TOOLS), "build", str(scratch), str(src), str(dst)], capture_output=True, text=True)
        if build.returncode:
            failures.append((src.name, build.stdout + build.stderr))
            continue
        valid = subprocess.run(["python", str(TOOLS), "validate", str(src), str(dst)], capture_output=True, text=True)
        if valid.returncode:
            failures.append((src.name, valid.stdout + valid.stderr))
        else:
            data = json.loads(dst.read_text(encoding="utf-8-sig"))
            processed.append((src.name, len(data["spans"]), data["spans"]))
            print(f"{src.name}: {len(data['spans'])} spans")
    print(f"SUMMARY processed={len(processed)} skipped={len(skipped)} failed={len(failures)}")
    for name, err in failures:
        print("FAILED", name, err)

if __name__ == "__main__":
    main()
