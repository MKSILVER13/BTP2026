#!/usr/bin/env python3
"""
eval_gold.py - score a <stem>.am.json against a gold file of the corpus format, and say WHY spans fail.

    python3 eval_gold.py GOLD.json PRED.am.json TEXT.txt [--thr 0.5] [--diagnose] [--sweep]

GOLD.json : {"annotations": [{"start": 22222, "end": 22969, "label": "Application to the concrete case", ...}, ...]}
PRED.am.json : output of this skill (spans = [id,start,end,TYPE,ACTOR])
(GOLD may also be an am.json file with actors: then actor accuracy and span+label+actor F1 are reported.)
TEXT.txt  : the judgment. Gold offsets index the LF-normalised text (CRLF counted once); if PRED was made on the
            raw CRLF text (n_chars == raw length) it is converted automatically.

Scoring = same idea as the IoU evaluator notebook: one-to-one matching of spans with character IoU >= thr
(maximise the number of pairs, then total IoU); P = c/s, R = c/g, F1. 'label' scores also require the same label.
"""
import argparse
import bisect
import importlib.util
import json
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_spec = importlib.util.spec_from_file_location("am_tools", os.path.join(os.path.dirname(os.path.abspath(__file__)), "am_tools.py"))
am = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(am)

CODE2LABEL = {
    "NCP": "Procedural arguments—Non contestation by the parties",
    "TXT": "Method of interpretation—Textual interpretation",
    "HIS": "Method of interpretation—Historical interpretation",
    "SYS": "Method of interpretation—Systematic interpretation",
    "TEL": "Method of interpretation—Teleological interpretation",
    "CMP": "Method of interpretation—Comparative law",
    "LEG": "Test of the principle of proportionality—Legal basis",
    "PUR": "Test of the principle of proportionality—Legitimate purpose",
    "SUI": "Test of the principle of proportionality—Suitability",
    "NEC": "Test of the principle of proportionality—Necessity/Proportionality",
    "OVR": "Institutional arguments—Overruling",
    "DIS": "Institutional arguments—Distinguishing",
    "MOA": "Institutional arguments—Margin of Appreciation",
    "PRE": "Precedents of the ECHR",
    "DEC": "Decision of the ECHR",
    "APP": "Application to the concrete case",
}


def iou(a, b):
    i = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    u = (a[1] - a[0]) + (b[1] - b[0]) - i
    return i / u if u > 0 else 0.0


def match(sys_sp, gold_sp, thr):
    if not sys_sp or not gold_sp:
        return []
    M = [[iou(s, g) for g in gold_sp] for s in sys_sp]
    elig = [[M[i][j] >= thr and M[i][j] > 0 for j in range(len(gold_sp))] for i in range(len(sys_sp))]
    try:
        import numpy as np
        from scipy.optimize import linear_sum_assignment
        W = np.array([[(1 + M[i][j]) if elig[i][j] else 0.0 for j in range(len(gold_sp))] for i in range(len(sys_sp))])
        r, c = linear_sum_assignment(-W)
        return [(i, j, M[i][j]) for i, j in zip(r, c) if elig[i][j]]
    except Exception:  # greedy fallback
        cand = sorted(((M[i][j], i, j) for i in range(len(sys_sp)) for j in range(len(gold_sp)) if elig[i][j]), reverse=True)
        used_i, used_j, out = set(), set(), []
        for v, i, j in cand:
            if i not in used_i and j not in used_j:
                used_i.add(i); used_j.add(j); out.append((i, j, v))
        return out


def prf(c, s, g):
    p = c / s if s else 0.0
    r = c / g if g else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gold")
    ap.add_argument("pred")
    ap.add_argument("txt")
    ap.add_argument("--thr", type=float, default=0.5)
    ap.add_argument("--diagnose", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    a = ap.parse_args()

    text, info = am.load_text(a.txt)
    gold = json.load(open(a.gold, encoding="utf-8-sig"))
    GA = None                                  # gold actors (only when the gold is in this skill's own am.json format)
    if isinstance(gold, dict) and "spans" in gold:
        GA = [sp[4] for sp in gold["spans"]]
        gold = [{"start": sp[1], "end": sp[2], "label": CODE2LABEL.get(sp[3], sp[3])} for sp in gold["spans"]]
    else:
        gold = gold["annotations"] if isinstance(gold, dict) else gold
    pred = json.load(open(a.pred, encoding="utf-8-sig"))
    G = [(g["start"], g["end"], g["label"]) for g in gold]
    S = [(s, e, CODE2LABEL.get(t, t), ac, sid) for sid, s, e, t, ac in pred["spans"]]
    if pred.get("n_chars") != len(text):
        if pred.get("n_chars") == info["raw_len"]:
            f = am.make_mapper(info["edits"])
            S = [(f(s), f(e), l, ac, sid) for s, e, l, ac, sid in S]
            print("note: prediction was made on the raw text; offsets converted (CRLF/mojibake) before scoring")
        else:
            print("WARNING: prediction n_chars=%s but text has %d characters - offsets may not line up" % (pred.get("n_chars"), len(text)))
    bad = [i for i, g in enumerate(gold) if g.get("text") is not None and text[g["start"]:g["end"]] != g["text"]]
    if bad:
        print("WARNING: gold text does not match this text file for %d span(s) - wrong file or different newline/encoding" % len(bad))

    def score(thr):
        pr = match([s[:2] for s in S], [g[:2] for g in G], thr)
        same = [p for p in pr if S[p[0]][2] == G[p[1]][2]]
        return pr, same

    pairs, same = score(a.thr)
    p, r, f = prf(len(pairs), len(S), len(G))
    p2, r2, f2 = prf(len(same), len(S), len(G))
    print("IoU >= %.2f   gold=%d  predicted=%d" % (a.thr, len(G), len(S)))
    print("  span only      matched=%-3d P=%.3f R=%.3f F1=%.3f" % (len(pairs), p, r, f))
    print("  span + label   matched=%-3d P=%.3f R=%.3f F1=%.3f" % (len(same), p2, r2, f2))
    if GA is not None:
        ok_a = [q for q in pairs if S[q[0]][3] == GA[q[1]]]
        ok_la = [q for q in same if S[q[0]][3] == GA[q[1]]]
        pa, ra, fa = prf(len(ok_la), len(S), len(G))
        print("  span+label+actor matched=%-3d P=%.3f R=%.3f F1=%.3f" % (len(ok_la), pa, ra, fa))
        print("  actor accuracy on span-matched pairs: %d/%d = %.3f ; on span+label-matched pairs: %d/%d" % (
            len(ok_a), len(pairs), len(ok_a) / max(1, len(pairs)), len(ok_la), len(same)))
        conf = {}
        for i, j, *_ in pairs:
            conf[(GA[j], S[i][3])] = conf.get((GA[j], S[i][3]), 0) + 1
        print("  actor confusion (gold -> predicted): " + ", ".join("%s->%s x%d" % (g, pr, n) for (g, pr), n in sorted(conf.items()) if g != pr) or "none")
    labels = sorted({g[2] for g in G} | {s[2] for s in S})
    print("\n%-34s %4s %4s %4s %6s %6s %6s" % ("label", "g", "s", "c", "P", "R", "F1"))
    for lab in labels:
        sp = [s for s in S if s[2] == lab]
        gp = [g for g in G if g[2] == lab]
        c = len(match([s[:2] for s in sp], [g[:2] for g in gp], a.thr))
        pp, rr, ff = prf(c, len(sp), len(gp))
        print("%-34s %4d %4d %4d %6.3f %6.3f %6.3f" % (lab.split("—")[-1][:34], len(gp), len(sp), c, pp, rr, ff))
    if a.sweep:
        print("\nthr    span F1  label F1")
        for t in (0.1, 0.3, 0.5, 0.7, 0.9, 1.0):
            pr, sm = score(t)
            print("%.1f   %7.3f  %7.3f" % (t, prf(len(pr), len(S), len(G))[2], prf(len(sm), len(S), len(G))[2]))
    if a.diagnose:
        blocks = am.segment_text(text)["blocks"]
        bstarts = [b["s"] for b in blocks]

        def para(o):
            k = bisect.bisect_right(bstarts, o) - 1
            return blocks[k]["num"] if k >= 0 and blocks[k]["num"] is not None else "-"
        mp = {i: (j, v) for i, j, v in pairs}
        print("\n-- predicted spans (para = judgment paragraph number)")
        for i, s in enumerate(S):
            if i in mp:
                j, v = mp[i]
                st = "match g%d iou=%.2f%s" % (j + 1, v, "" if s[2] == G[j][2] else "  LABEL: gold=" + G[j][2].split("—")[-1])
            else:
                b = max(range(len(G)), key=lambda j: iou(s[:2], G[j][:2])) if G else None
                bi = iou(s[:2], G[b][:2]) if b is not None else 0
                st = ("no match (best g%d iou=%.2f)" % (b + 1, bi)) if bi > 0 else "NOT IN GOLD (false positive, outside every gold span)"
            print("s%-3d para %-3s [%d-%d) %-24s %-5s %s" % (s[4], para(s[0]), s[0], s[1], s[2].split("—")[-1][:24], s[3], st))
        matched_g = {j for _, j, _ in pairs}
        print("\n-- gold spans nobody matched")
        for j, g in enumerate(G):
            if j not in matched_g:
                ov = [s[4] for s in S if iou(s[:2], g[:2]) > 0]
                print("g%-3d para %-3s [%d-%d) %-24s overlapping predictions: %s" % (j + 1, para(g[0]), g[0], g[1], g[2].split("—")[-1][:24], ov or "none"))
        if G:
            lo, hi = min(g[0] for g in G), max(g[1] for g in G)
            outside = [s for s in S if s[0] >= hi]
            print("\n%d of %d predicted spans start after the last gold span (char %d): out-of-scope tail" % (len(outside), len(S), hi))


if __name__ == "__main__":
    main()
