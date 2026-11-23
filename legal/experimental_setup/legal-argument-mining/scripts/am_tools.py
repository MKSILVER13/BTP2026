#!/usr/bin/env python3
"""
am_tools.py - helper for the legal-argument-mining skill (Python 3.8+, standard library only).

Why it exists: language models are unreliable at counting characters, so the model marks spans as
SENTENCE-UNIT RANGES (["u7-u9"]) and this tool turns them into exact character offsets.

Commands
  segment         split text file(s) into numbered sentence units (+ scope, flags, warnings)
  build           scratch rows (.jsonl, unit ranges) -> final <stem>.am.json with character offsets
  validate        check one final annotation file against its text
  batch-validate  validate every .txt in a directory against <out_dir>/<stem>.am.json
  rebase          convert an older output (CRLF / un-repaired offsets) to the canonical offsets

CANONICAL TEXT AND OFFSETS (every command uses the same text, so numbers always agree):
  * file bytes are decoded as UTF-8 (BOM removed; UTF-16 / cp1252 / latin-1 are tried if UTF-8 fails)
  * line endings are normalised to "\\n": CRLF counts as ONE character - exactly what Python's
    open(path, encoding="utf-8").read() gives, and what the corpus gold files use.   (--keep-crlf: off)
  * mojibake caused by UTF-8 text decoded as cp1252 (e.g. "â€™" for an apostrophe) is repaired. (--no-repair: off)
  * offsets are 0-based and END-EXCLUSIVE:  span text == text[start:end]

Run:  python3 am_tools.py <command> --help        (on Windows use `python` or `py` instead of python3)
"""
import argparse
import bisect
import json
import os
import re
import sys

# Windows consoles default to cp1252 and crash on characters such as the typographic apostrophe.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCHEMA = "lam-am/1.1"

TYPES = ["NCP", "TXT", "HIS", "SYS", "TEL", "CMP", "LEG", "PUR", "SUI", "NEC",
         "OVR", "DIS", "MOA", "PRE", "DEC", "APP"]
ACTORS = ["ECHR", "APPL", "STATE", "THIRD", "COMM"]
RELS = ["S", "A", "E"]
RARE_TYPES = ["HIS", "OVR", "SUI", "TXT", "SYS", "CMP", "TEL", "MOA", "DIS", "NCP"]

OPTS = {"keep_crlf": False, "repair": True}

# ============================================================================ text loading
_CONT = ("[\u0080-¿ŒœŠšŸŽžƒˆ˜"
         "–—‘-‚“-„†-•…‰‹›€™]")
MOJIBAKE = re.compile("(?:[Â-ß]%s|[à-ï]%s{2}|[ð-ô]%s{3})" % (_CONT, _CONT, _CONT))


def _moji_bytes(s):
    out = bytearray()
    for ch in s:
        try:
            out += ch.encode("cp1252")
        except UnicodeEncodeError:
            if 0x80 <= ord(ch) <= 0x9F:
                out.append(ord(ch))
            else:
                return None
    return bytes(out)


def _repair_one(s):
    b = _moji_bytes(s)
    if b is None:
        return None
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return None


def decode_bytes(b):
    """bytes -> (str, note or None)"""
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:]
    if b.startswith(b"\xff\xfe") or b.startswith(b"\xfe\xff"):
        return b.decode("utf-16"), "file was UTF-16"
    try:
        return b.decode("utf-8"), None
    except UnicodeDecodeError:
        pass
    try:
        return b.decode("cp1252"), "file is not valid UTF-8; decoded as cp1252"
    except UnicodeDecodeError:
        return b.decode("latin-1"), "file is not valid UTF-8; decoded as latin-1"


def normalize_text(raw, keep_crlf=False, repair=True):
    """raw str -> (clean str, edits). edits = sorted non-overlapping (raw_start, raw_end, replacement)."""
    edits = []
    if not keep_crlf:
        edits += [(m.start(), m.end(), "\n") for m in re.finditer(r"\r\n?", raw)]
    if repair:
        for m in MOJIBAKE.finditer(raw):
            fixed = _repair_one(m.group())
            if fixed is not None:
                edits.append((m.start(), m.end(), fixed))
    edits.sort()
    out, pos = [], 0
    for s, e, r in edits:
        out.append(raw[pos:s])
        out.append(r)
        pos = e
    out.append(raw[pos:])
    return "".join(out), edits


def make_mapper(edits):
    """returns f(raw_offset) -> clean_offset"""
    starts = [e[0] for e in edits]
    ends = [e[1] for e in edits]
    cum, d = [], 0
    for s, e, r in edits:
        d += len(r) - (e - s)
        cum.append(d)

    def f(o):
        j = bisect.bisect_right(starts, o) - 1
        if j >= 0 and starts[j] < o < ends[j]:
            return starts[j] + (cum[j - 1] if j > 0 else 0)
        i = bisect.bisect_right(ends, o) - 1
        return o + (cum[i] if i >= 0 else 0)
    return f


def load_text(path, keep_crlf=None, repair=None):
    keep_crlf = OPTS["keep_crlf"] if keep_crlf is None else keep_crlf
    repair = OPTS["repair"] if repair is None else repair
    with open(path, "rb") as f:
        raw, note = decode_bytes(f.read())
    clean, edits = normalize_text(raw, keep_crlf, repair)
    n_nl = sum(1 for e in edits if e[2] == "\n")
    info = {"raw_len": len(raw), "n_chars": len(clean), "crlf": n_nl, "repairs": len(edits) - n_nl,
            "decode_note": note, "edits": edits}
    return clean, info


def read_text(path):
    return load_text(path)[0]


# ============================================================================ segmentation
ABBREV = {
    "v", "vs", "no", "nos", "art", "arts", "para", "paras", "p", "pp", "cf", "e.g", "i.e", "viz",
    "mr", "mrs", "ms", "dr", "sir", "prof", "st", "sec", "s", "ss", "ch", "cl", "reg", "regs", "vol",
    "ed", "eds", "et", "al", "inc", "co", "ltd", "approx", "ibid", "op", "cit", "supp", "rev", "ex",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
    "u.s", "u.k", "lit", "sub", "subpara", "fig", "tab",
}
NUM_START = re.compile(r"^(\d{1,3})\s?\.\s+(?=\S)")
HEAD_NUM = re.compile(r"^(?:[IVXLC]{1,6}|[A-Z]|\d{1,2})\.\s+\S|^\((?:[a-z]|[ivx]{1,4}|\d{1,2})\)\s+\S")
SENT_END = re.compile(r"[.!?][\"'”’)\]]*[ \t\r\n]+")
QUOTE_OPEN = "\"“"
INLINE_NUM = re.compile(r"(?:(?<=\s)|^)(\d{1,3})\.\s+(?=[A-Z“\"'(])")

LAW_PATTERNS = [
    (re.compile(r"^[ \t]*(?:AS TO )?THE LAW[ \t]*$", re.I | re.M), "law-heading"),
    (re.compile(r"^[ \t]*IN LAW[ \t]*$", re.I | re.M), "law-heading"),
    (re.compile(r"^[ \t]*(?:THE )?COURT[’']S (?:ASSESSMENT|EVALUATION|APPRAISAL)[ \t]*$", re.I | re.M),
     "assessment-heading"),
    (re.compile(r"^[ \t]*(?:[IVXLC]{1,5}\.[ \t]+)?(?:ALLEGED (?:VIOLATION|BREACH)|SCOPE OF THE CASE|ADMISSIBILITY|"
                r"PRELIMINARY OBJECTION)[^\n]{0,140}$", re.M), "issue-heading"),
]
INLINE_LAW = re.compile(r"(?<![A-Za-z])(?:AS TO )?THE LAW(?![A-Za-z])")
PREAMBLE = re.compile(r"CASE OF |composed of the following|Having deliberated|\bPROCEDURE\b|AS TO THE FACTS|"
                      r"\bTHE FACTS\b|THE CIRCUMSTANCES OF THE CASE|was referred to the Court|lodged with the (?:Court|Commission)|"
                      r"Application no\.")
CUE = re.compile(r"\bThe Court (?:notes|reiterates|considers|observes|recalls|finds)\b|"
                 r"\balleg(?:es|ed) (?:a )?(?:violation|breach) of Article|"
                 r"\bcomplain(?:s|ed) under Article|\balleged violation of Article", re.I)
TAIL_PATTERNS = [
    re.compile(r"^[ \t]*FOR (?:THESE|THE ABOVE) REASONS\b[^\n]*$", re.I | re.M),
    re.compile(r"^[ \t]*(?:(?:JOINT|PARTLY|PARTIALLY|SEPARATE|CONCURRING|DISSENTING|COMMON|AND)\s+)+OPINION\b[^\n]*$",
               re.I | re.M),
    re.compile(r"^[ \t]*Done in English(?: and in French)?\b", re.I | re.M),
]
INLINE_TAIL = re.compile(r"FOR THESE REASONS(?:, THE COURT)?|(?:JOINT )?(?:PARTLY )?(?:DISSENTING|CONCURRING|SEPARATE) OPINION OF")
LOW_HEADING = re.compile(r"\b(?:costs and expenses|default interest|costs)\b", re.I)
# just-satisfaction section (Art. 41 / old Art. 50): once it starts, everything after it is low priority
JUST_SAT_HEADING = re.compile(r"\bapplication of article\s*(?:41|50)\b|\bjust satisfaction\b|\barticle\s*(?:41|50)\s*$", re.I)
TOP_HEADING = re.compile(r"^(?:[IVXLC]{1,6}|[A-Z])\.\s")


def is_heading(st):
    if not st or len(st) > 160 or st[-1] in ".;:,!?\"”’'":
        return False
    if HEAD_NUM.match(st):
        return True
    letters = [c for c in st if c.isalpha()]
    if len(letters) >= 3 and sum(c.isupper() for c in letters) / len(letters) >= 0.7 and len(st.split()) <= 20:
        return True
    return len(st.split()) <= 6 and st[0].isupper()


def split_inline(text, s, e, first_num):
    """A long block that contains sequential inline paragraph numbers ('... 34. The applicant ...') -> sub-blocks."""
    seg = text[s:e]
    cands = []
    for m in INLINE_NUM.finditer(seg):
        pos = m.start(1)
        prev = seg[:pos].rstrip()[-1:] if pos > 0 else ""
        cands.append((pos, int(m.group(1)), prev in ".!?:;\"”’)]" or prev == ""))
    chain, cur = [], first_num
    for i, (pos, n, after_stop) in enumerate(cands):
        if pos == 0:
            cur = n
            continue
        if cur is None:
            # start of a chain: needs a sentence stop before it and the next number somewhere later
            if after_stop and any(c[1] == n + 1 for c in cands[i + 1:]):
                chain.append((pos, n))
                cur = n
        elif n == cur + 1:
            # inside an established chain the strict +1 sequence is the evidence (flattened headings may precede it)
            chain.append((pos, n))
            cur = n
    if not chain:
        return None
    cuts = [(0, first_num)] + chain
    out = []
    for k, (pos, n) in enumerate(cuts):
        end = cuts[k + 1][0] if k + 1 < len(cuts) else len(seg)
        piece = seg[pos:end]
        ps = s + pos + (len(piece) - len(piece.lstrip()))
        pe = s + end - (len(piece) - len(piece.rstrip()))
        if pe > ps:
            out.append({"s": ps, "e": pe, "heading": False, "num": n})
    return out


def build_blocks(text):
    """Blocks = numbered judgment paragraphs (with their continuation lines), headings, other paragraphs."""
    lines, pos, n = [], 0, len(text)
    while pos <= n:
        e = text.find("\n", pos)
        if e == -1:
            e = n
        a, b = pos, e
        while a < b and text[a] in " \t\r ":
            a += 1
        while b > a and text[b - 1] in " \t\r ":
            b -= 1
        st = text[a:b]
        if not st:
            kind, num = "blank", None
        else:
            m = NUM_START.match(st)
            if is_heading(st):
                kind, num = "heading", None
            elif m:
                kind, num = "numbered", int(m.group(1))
            else:
                kind, num = "plain", None
        lines.append((a, b, kind, num))
        pos = e + 1
    numbered_mode = sum(1 for l in lines if l[2] == "numbered") >= 5
    blanks = 0
    seen_text = False
    for l in lines:
        if l[2] == "blank":
            blanks += seen_text
        else:
            seen_text = True
    has_blank = blanks >= 3
    blocks, cur = [], None
    for a, b, kind, num in lines:
        if kind == "blank":
            cur = None
        elif kind == "heading":
            blocks.append({"s": a, "e": b, "heading": True, "num": None})
            cur = None
        elif kind == "numbered":
            cur = {"s": a, "e": b, "heading": False, "num": num}
            blocks.append(cur)
        else:
            if cur is not None and (numbered_mode or has_blank):
                cur["e"] = b
            else:
                cur = {"s": a, "e": b, "heading": False, "num": None}
                blocks.append(cur)
    # flattened / merged paragraphs: recover them from the paragraph numbers inside very long blocks
    out = []
    for blk in blocks:
        if not blk["heading"] and blk["e"] - blk["s"] > 2500:
            parts = split_inline(text, blk["s"], blk["e"], blk["num"])
            if parts:
                out.extend(parts)
                continue
        out.append(blk)
    for i, blk in enumerate(out, 1):
        blk["id"] = i
    return out


def split_sentences(text, s, e):
    seg = text[s:e]
    cuts = [0]
    for m in SENT_END.finditer(seg):
        j = m.end()
        if j >= len(seg):
            continue
        nxt = seg[j]
        if not (nxt.isupper() or nxt.isdigit() or nxt in "\"'“‘([§"):
            continue
        if seg[m.start()] == ".":
            w = re.search(r"([A-Za-z][A-Za-z.]*)$", seg[:m.start()])
            word = w.group(1).lower().rstrip(".") if w else ""
            if word in ABBREV or (len(word) == 1 and word.isalpha()):
                continue
        cuts.append(j)
    cuts.append(len(seg))
    out = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        piece = seg[a:b]
        lead = len(piece) - len(piece.lstrip())
        trail = len(piece) - len(piece.rstrip())
        if piece.strip():
            out.append((s + a + lead, s + b - trail))
    return out


def line_pieces(text, s, e):
    """Split a block at hard line breaks (a line that ends a sentence/lead-in). Soft (wrapped) breaks stay."""
    cuts = [s]
    k = text.find("\n", s, e)
    while k != -1:
        j = k - 1
        while j >= s and text[j] in " \t\r":
            j -= 1
        q = k + 1
        while q < e and text[q] in " \t\r\n":
            q += 1
        if j >= s and q < e:
            c, nxt = text[j], text[q]
            if c in ".:;!?" or (c in "\"”’)]" and not nxt.islower()):
                cuts.append(k + 1)
        k = text.find("\n", k + 1, e)
    cuts.append(e)
    for a, b in zip(cuts[:-1], cuts[1:]):
        while a < b and text[a] in " \t\r\n":
            a += 1
        while b > a and text[b - 1] in " \t\r\n":
            b -= 1
        if b > a:
            yield a, b


def make_units(text, blocks):
    units, uid, low, sticky = [], 0, False, False
    for b in blocks:
        if b["heading"]:
            st = text[b["s"]:b["e"]]
            if JUST_SAT_HEADING.search(st):
                low = sticky = True
            elif LOW_HEADING.search(st):
                low = True
            elif sticky:
                pass
            elif TOP_HEADING.match(st):
                low = False
            uid += 1
            units.append({"id": uid, "p": b["id"], "s": b["s"], "e": b["e"], "h": 1, "q": 0, "l": 0})
            continue
        body_s = b["s"]
        if b["num"] is not None:
            m = NUM_START.match(text[b["s"]:b["e"]])
            if m:
                body_s = b["s"] + m.end()
        b["body_s"] = body_s
        for ps, pe in line_pieces(text, body_s, b["e"]):
            qend = ps
            if text[ps] in QUOTE_OPEN:
                close = "”" if text[ps] == "“" else "\""
                idx = text.find(close, ps + 1, pe)
                qend = pe if idx == -1 else idx + 1
            for us, ue in split_sentences(text, ps, pe):
                uid += 1
                ut = text[us:ue]
                letters = [c for c in ut if c.isalpha()]
                shouty = (len(letters) >= 8 and ut[-1] not in ".;:,!?\"”’"
                          and sum(c.isupper() for c in letters) / len(letters) >= 0.7)   # heading swallowed by flattened text
                units.append({"id": uid, "p": b["id"], "s": us, "e": ue, "h": int(shouty), "q": int(us < qend), "l": int(low)})
    return units


def find_scope(text, blocks):
    n = len(text)
    start, source = 0, "none"
    for rx, name in LAW_PATTERNS[:3]:                      # strong signals: an explicit Law heading
        m = rx.search(text)
        if m:
            start, source = m.start() + (len(m.group()) - len(m.group().lstrip())), name
            break
    else:
        m = INLINE_LAW.search(text)
        if m and m.start() > 0.05 * n:
            start, source = m.start(), "law-heading-inline"
        elif not PREAMBLE.search(text[:6000]):
            # no judgment preamble at all: an excerpt that already starts inside the reasoning
            start, source = 0, "excerpt"
        else:
            m = LAW_PATTERNS[3][0].search(text)             # weak signals: never hide anything, only suggest
            if m:
                start, source = m.start(), "issue-heading"
            else:
                for b in blocks:
                    if b["s"] < 0.08 * n or b["heading"]:
                        continue
                    if CUE.search(text[b["s"]:b["e"]]):
                        start, source = b["s"], "cue"
                        break
    end = None
    for rx in TAIL_PATTERNS:
        for m in rx.finditer(text, start):
            end = m.start() if end is None else min(end, m.start())
            break
    if end is None and source in ("law-heading-inline", "cue"):
        m = INLINE_TAIL.search(text, start)
        if m:
            end = m.start()
    return {"start": start, "source": source, "end": end}


def segment_text(text):
    blocks = build_blocks(text)
    units = make_units(text, blocks)
    scope = find_scope(text, blocks)
    stripped = text.rstrip()
    truncated = bool(stripped) and stripped[-1] not in ".!?\"”’)];:"
    return {"n_chars": len(text), "blocks": blocks, "units": units, "scope": scope, "truncated": truncated}


HIDING_SOURCES = ("law-heading", "law-heading-inline", "assessment-heading")


def in_scope(seg, u, include_tail=False):
    sc = seg["scope"]
    if sc["source"] in HIDING_SOURCES and u["e"] <= sc["start"]:
        return False
    if sc["end"] is not None and not include_tail and u["s"] >= sc["end"]:
        return False
    return True


def render_units(text, seg, name, info, include_tail=False, show_all=False):
    sc, units = seg["scope"], seg["units"]
    first = next((u for u in units if u["s"] >= sc["start"]), None)
    first_of_block = {}
    for u in units:
        first_of_block.setdefault(u["p"], u["id"])
    L = ["# FILE %s  n_chars=%d  units=%d  paragraphs=%d" % (name, len(text), len(units), len(seg["blocks"]))]
    notes = []
    if info.get("crlf"):
        notes.append("CRLF->LF x%d" % info["crlf"])
    if info.get("repairs"):
        notes.append("repaired %d mojibake sequences (e.g. a-circumflex+euro+tm -> apostrophe)" % info["repairs"])
    if info.get("decode_note"):
        notes.append(info["decode_note"])
    if notes:
        L.append("# TEXT: offsets refer to the cleaned text (" + "; ".join(notes) + ")")
    if sc["source"] in HIDING_SOURCES:
        L.append("# SCOPE: legal reasoning starts at char %d (unit u%s) via %s. Earlier units are hidden (facts/procedure)."
                 % (sc["start"], first["id"] if first else "?", sc["source"]))
    elif sc["source"] == "issue-heading":
        L.append("# SCOPE WARNING: no 'THE LAW' heading. The first issue heading ('ALLEGED VIOLATION...' etc.) is at char %d "
                 "(marked >>> below). ALL units are shown; legal reasoning normally starts at or just before it "
                 "(07_edge_cases.md section 1)." % sc["start"])
    elif sc["source"] == "excerpt":
        L.append("# SCOPE: no judgment preamble (parties, procedure, facts) detected, so this looks like an EXCERPT that already "
                 "starts inside the reasoning. Everything is in scope: annotate from the first unit.")
    elif sc["source"] == "cue":
        L.append("# SCOPE WARNING: no 'THE LAW' heading found. The first argumentative-sounding paragraph is at char %d "
                 "(marked >>> below). ALL units are shown; decide yourself where legal reasoning starts "
                 "(see 07_edge_cases.md section 1)." % sc["start"])
    else:
        L.append("# SCOPE WARNING: no 'THE LAW' heading and no argumentative cue found. ALL units are shown; "
                 "decide yourself where legal reasoning starts (07_edge_cases.md section 1).")
    if sc["end"] is not None:
        tail_u = next((u for u in units if u["s"] >= sc["end"]), None)
        L.append("# TAIL: from char %d (unit u%s) = operative part / separate opinions %s. "
                 % (sc["end"], tail_u["id"] if tail_u else "?",
                    "(shown)" if include_tail else "(hidden: not annotated in the corpus; use --include-tail to show)"))
    if seg["truncated"]:
        L.append("# WARNING: the text appears TRUNCATED (it ends mid-sentence). The last unit is flagged T. Annotate what "
                 "is there; do not invent the missing end (07_edge_cases.md section 4).")
    L.append("# FLAGS: H=heading (never annotate)  Q=inside a quotation (often verbatim law/judgment: usually no span)  "
             "L=low-priority section (Art. 41/50 just satisfaction, costs, default interest: do not annotate by default)  T=truncated end")
    L.append("# FORMAT: u<unit> p<block> <paragraph-number> [start-end) flags | text")
    hidden_head = False
    for u in units:
        vis = show_all or in_scope(seg, u, include_tail)
        if not vis:
            if not hidden_head and u["e"] <= sc["start"]:
                L.append("-- units before char %d hidden (facts/procedure; use --show-all to see them) --" % sc["start"])
                hidden_head = True
            continue
        if sc["source"] in ("cue", "issue-heading") and first and u["id"] == first["id"]:
            L.append(">>> suggested start of legal reasoning (uncertain) <<<")
        blk = seg["blocks"][u["p"] - 1]
        para = ""
        if u["id"] == first_of_block[u["p"]] and blk["num"] is not None:
            para = "¶%d" % blk["num"]
        flags = ("H" if u["h"] else "") + ("Q" if u["q"] else "") + ("L" if u["l"] else "")
        if seg["truncated"] and u["id"] == units[-1]["id"]:
            flags += "T"
        t = re.sub(r"\s+", " ", text[u["s"]:u["e"]])
        L.append("u%d p%d %s [%d-%d) %s| %s" % (u["id"], u["p"], para, u["s"], u["e"], (flags + " ") if flags else "", t))
    if sc["end"] is not None and not include_tail:
        L.append("-- tail from char %d hidden --" % sc["end"])
    return "\n".join(L) + "\n"


def cmd_segment(a):
    in_path, out_dir = a.input, a.work_dir
    os.makedirs(out_dir, exist_ok=True)
    files = ([os.path.join(in_path, f) for f in sorted(os.listdir(in_path)) if f.lower().endswith(".txt")]
             if os.path.isdir(in_path) else [in_path])
    if not files:
        sys.exit("no .txt files found in " + in_path)
    for fp in files:
        text, info = load_text(fp)
        seg = segment_text(text)
        if a.region_start is not None:
            seg["scope"] = {"start": a.region_start, "source": "law-heading", "end": seg["scope"]["end"]}
        stem = os.path.splitext(os.path.basename(fp))[0]
        with open(os.path.join(out_dir, stem + ".units.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write(render_units(text, seg, os.path.basename(fp), info, a.include_tail, a.show_all))
        sc = seg["scope"]
        bits = ["%d chars" % len(text), "%d units" % len(seg["units"]), "%d paragraphs" % len(seg["blocks"]),
                "scope=%s@%d" % (sc["source"], sc["start"])]
        if sc["end"] is not None:
            bits.append("tail@%d" % sc["end"])
        if info["crlf"]:
            bits.append("CRLF->LF x%d" % info["crlf"])
        if info["repairs"]:
            bits.append("REPAIRED %d mojibake" % info["repairs"])
        if seg["truncated"]:
            bits.append("TRUNCATED")
        if sc["source"] in ("cue", "none"):
            bits.append("SCOPE UNCERTAIN")
        if len(seg["blocks"]) < 3 and len(text) > 5000:
            bits.append("WARNING: only %d paragraph(s) found - text looks flattened" % len(seg["blocks"]))
        print("%s: %s -> %s.units.txt" % (os.path.basename(fp), ", ".join(bits), stem))


# ============================================================================ build
UNIT_RANGE = re.compile(r"u?(\d+)(?:\s*-\s*u?(\d+))?$", re.IGNORECASE)
START_KEYS = ("start_at", "start_after")
END_KEYS = ("end_before", "end_after")


def find_anchor(text, lo, hi, phrase, what, where):
    if not isinstance(phrase, str) or not phrase:
        raise ValueError("%s: %s must be a non-empty string" % (where, what))
    hits, i = [], text.find(phrase, lo, hi)
    while i != -1:
        hits.append(i)
        i = text.find(phrase, i + 1, hi)
    if not hits:
        raise ValueError("%s: %s %r not found inside the unit (copy it exactly from the unit text)" % (where, what, phrase))
    if len(hits) > 1:
        raise ValueError("%s: %s %r occurs %d times inside the unit; use a longer, unique phrase" % (where, what, phrase, len(hits)))
    return hits[0]


def resolve_unit_span(row, units, text, where, seg):
    """[id,"u7-u8",type,actor(,{anchors})] -> ([id,start,end,type,actor], [warnings])"""
    sid, rng, typ, act = row[0], row[1], row[2], row[3]
    anchors = row[4] if len(row) == 5 else {}
    warns = []
    if not isinstance(anchors, dict):
        raise ValueError("%s: 5th item of a unit-span row must be an object of anchors" % where)
    allowed = START_KEYS + END_KEYS + ("allow_heading",)
    bad = [k for k in anchors if k not in allowed]
    if bad:
        raise ValueError("%s: unknown key(s) %s; allowed: %s" % (where, bad, list(allowed)))
    if sum(k in anchors for k in START_KEYS) > 1 or sum(k in anchors for k in END_KEYS) > 1:
        raise ValueError("%s: use at most one start anchor and one end anchor" % where)
    m = UNIT_RANGE.match(str(rng).strip())
    if not m:
        raise ValueError("%s: bad unit range %r (use \"u7\" or \"u7-u9\")" % (where, rng))
    first = int(m.group(1))
    last = int(m.group(2)) if m.group(2) else first
    if first > last:
        raise ValueError("%s: unit range %r runs backwards" % (where, rng))
    for u in (first, last):
        if u not in units:
            raise ValueError("%s: unit u%d does not exist (file has u1-u%d)" % (where, u, max(units)))
    span_units = [units[u] for u in range(first, last + 1)]
    paras = {u["p"] for u in span_units}
    if len(paras) > 1:
        raise ValueError("%s: units u%d-u%d cross a paragraph boundary (blocks %s); use one span per paragraph"
                         % (where, first, last, sorted(paras)))
    if any(u["h"] for u in span_units) and not anchors.get("allow_heading"):
        raise ValueError("%s: u%d-u%d includes a heading unit (flag H); headings are never annotated "
                         "(if the tool misjudged a real sentence as a heading, add {\"allow_heading\":true})"
                         % (where, first, last))
    if any(u["l"] for u in span_units):
        warns.append(("low", where))
    if seg["scope"]["end"] is not None and span_units[0]["s"] >= seg["scope"]["end"]:
        warns.append(("tail", where))
    fu, lu = units[first], units[last]
    s, e = fu["s"], lu["e"]
    for key in START_KEYS:
        if key in anchors:
            pos = find_anchor(text, fu["s"], fu["e"], anchors[key], key, where)
            s = pos if key == "start_at" else pos + len(anchors[key])
    for key in END_KEYS:
        if key in anchors:
            pos = find_anchor(text, lu["s"], lu["e"], anchors[key], key, where)
            e = pos if key == "end_before" else pos + len(anchors[key])
    while s < e and text[s].isspace():
        s += 1
    while e > s and text[e - 1].isspace():
        e -= 1
    if s >= e:
        raise ValueError("%s: anchors leave an empty span" % where)
    return [sid, s, e, typ, act], warns


def dump_final(name, n, spans, rels, repairs=0):
    head = ["{", '  "schema": "%s",' % SCHEMA, '  "file": %s,' % json.dumps(name), '  "n_chars": %d,' % n,
            '  "offsets": "%s",' % ("raw" if OPTS["keep_crlf"] else "lf")]
    if repairs:
        head.append('  "repairs": %d,' % repairs)
    out = head + ['  "spans": [']
    out.append(",\n".join("    " + json.dumps(s, ensure_ascii=False) for s in spans))
    out.append("  ],")
    out.append('  "relations": [')
    out.append(",\n".join("    " + json.dumps(r) for r in rels))
    out.append("  ]")
    out.append("}")
    return "\n".join(out) + "\n"


def cmd_build(a):
    text, info = load_text(a.txt)
    seg = segment_text(text)
    units = {u["id"]: u for u in seg["units"]}
    spans, rels, problems, warns = [], [], [], []
    with open(a.jsonl, encoding="utf-8-sig") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            where = "%s:%d" % (os.path.basename(a.jsonl), ln)
            try:
                row = json.loads(line)
            except json.JSONDecodeError as ex:
                problems.append("%s: bad JSON (%s)" % (where, ex))
                continue
            if not isinstance(row, list):
                problems.append("%s: row must be a JSON array" % where)
                continue
            try:
                if len(row) == 3:
                    rels.append(row)
                elif len(row) in (4, 5) and isinstance(row[1], str):
                    sp, w = resolve_unit_span(row, units, text, where, seg)
                    spans.append(sp)
                    warns += w
                elif len(row) == 5 and isinstance(row[1], int):
                    spans.append(row)
                else:
                    problems.append("%s: unrecognised row shape %s" % (where, line[:60]))
            except ValueError as ex:
                problems.append(str(ex))
    if problems:
        print("NOT BUILT - %d problem(s):" % len(problems))
        for p in problems:
            print("  " + p)
        sys.exit(1)
    spans.sort(key=lambda r: r[1])
    out_dir = os.path.dirname(os.path.abspath(a.out))
    os.makedirs(out_dir, exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(dump_final(os.path.basename(a.txt), len(text), spans, rels, info["repairs"]))
    for kind, msg in (("low", "span row(s) in a low-priority section (flag L: costs / default interest) - not annotated by default"),
                      ("tail", "span row(s) in the tail (operative part / separate opinions) - not annotated in the corpus")):
        lines_ = [w.split(":")[-1] for k, w in warns if k == kind]
        if lines_:
            print("WARN  %d %s (jsonl lines %s%s)" % (len(lines_), msg, ", ".join(lines_[:8]), " ..." if len(lines_) > 8 else ""))
    print("built %s: %d spans, %d relations (unit ranges resolved to character offsets) - now run: validate"
          % (a.out, len(spans), len(rels)))


# ============================================================================ validate
def validate(txt_path, ann_path, show=False, quiet=False):
    errs, warns = [], []
    text, info = load_text(txt_path)
    n = len(text)
    try:
        with open(ann_path, encoding="utf-8-sig") as f:
            ann = json.load(f)
    except Exception as ex:
        return ["cannot parse JSON: %s" % ex], [], {}
    if ann.get("n_chars") != n:
        hint = ""
        if ann.get("n_chars") == info["raw_len"] and info["raw_len"] != n:
            hint = (" - this file was made on the RAW text (CRLF/mojibake counted). Convert it with:  "
                    "am_tools.py rebase <old.am.json> <text.txt> <new.am.json>")
        errs.append("n_chars is %s but the (cleaned) text has %d characters%s" % (ann.get("n_chars"), n, hint))
        return errs, [], {"spans": len(ann.get("spans", []))}     # offsets are meaningless on a different text
    spans, rels = ann.get("spans", []), ann.get("relations", [])
    seg = segment_text(text)
    blocks = seg["blocks"]
    bstarts = [b["s"] for b in blocks]
    sc = seg["scope"]
    ids, ok, tail_ids = set(), [], []
    for i, sp in enumerate(spans):
        if not (isinstance(sp, list) and len(sp) == 5):
            errs.append("span #%d: must be [id,start,end,type,actor]" % i)
            continue
        sid, s, e, t, ac = sp
        if not all(isinstance(x, int) for x in (sid, s, e)):
            errs.append("span %s: id/start/end must be integers" % sid)
            continue
        if sid in ids:
            errs.append("span id %d duplicated" % sid)
        ids.add(sid)
        if t not in TYPES:
            errs.append("span %d: unknown type '%s'" % (sid, t))
        if ac not in ACTORS:
            errs.append("span %d: unknown actor '%s'" % (sid, ac))
        if not (0 <= s < e <= n):
            errs.append("span %d: bad offsets [%d,%d) for a %d-char text" % (sid, s, e, n))
            continue
        frag = text[s:e]
        if frag != frag.strip():
            errs.append("span %d: starts/ends with whitespace -> %r...%r" % (sid, frag[:20], frag[-20:]))
        if s > 0 and text[s - 1].isalnum() and text[s].isalnum():
            errs.append("span %d: starts in the middle of a word (%r)" % (sid, text[max(0, s - 8):s + 8]))
        if e < n and text[e - 1].isalnum() and text[e].isalnum():
            errs.append("span %d: ends in the middle of a word (%r)" % (sid, text[max(0, e - 8):e + 8]))
        k = bisect.bisect_right(bstarts, s) - 1
        blk = blocks[k] if k >= 0 else None
        if blk is None or e > blk["e"]:
            errs.append("span %d: crosses a paragraph boundary (spans may not; paragraphs = numbered judgment "
                        "paragraphs incl. their continuation lines)" % sid)
        elif blk["heading"]:
            errs.append("span %d: lies on a heading" % sid)
        elif blk["num"] is not None and s < blk.get("body_s", blk["s"]):
            warns.append("span %d: includes the paragraph number" % sid)
        if sc["source"] in HIDING_SOURCES and e <= sc["start"]:
            warns.append("span %d: lies before the start of the Law section (facts/procedure are not annotated)" % sid)
        if sc["end"] is not None and s >= sc["end"]:
            tail_ids.append(sid)
        L = e - s
        if L > 2500:
            warns.append("span %d: very long (%d chars) - consider splitting" % (sid, L))
        if L < 25:
            warns.append("span %d: very short (%d chars) - check it is really an argument" % (sid, L))
        ok.append((s, e, sid, t))
    if tail_ids:
        warns.append("%d span(s) lie in the tail (operative part / separate opinions; ids %s%s) - not annotated in the corpus; "
                     "delete them" % (len(tail_ids), ", ".join(map(str, tail_ids[:8])), " ..." if len(tail_ids) > 8 else ""))
    ok.sort()
    for (s1, e1, i1, _), (s2, e2, i2, _) in zip(ok, ok[1:]):
        if s2 < e1:
            errs.append("spans %d and %d overlap ([%d,%d) vs [%d,%d))" % (i1, i2, s1, e1, s2, e2))
    seen, adj = set(), {}
    for r in rels:
        if not (isinstance(r, list) and len(r) == 3):
            errs.append("relation %s: must be [from,to,rel]" % (r,))
            continue
        f_, t_, k = r
        if f_ not in ids or t_ not in ids:
            errs.append("relation %s: refers to a span id that does not exist" % (r,))
        if f_ == t_:
            errs.append("relation %s: self-relation" % (r,))
        if k not in RELS:
            errs.append("relation %s: unknown relation '%s'" % (r, k))
        if (f_, t_) in seen:
            errs.append("relation %s: duplicate pair" % (r,))
        seen.add((f_, t_))
        if k == "S":
            adj.setdefault(f_, []).append(t_)
    state = {}

    def dfs(u):
        state[u] = 1
        for v in adj.get(u, []):
            if state.get(v) == 1:
                return True
            if state.get(v) is None and dfs(v):
                return True
        state[u] = 2
        return False
    if any(state.get(u) is None and dfs(u) for u in list(adj)):
        warns.append("cycle among 'S' (supports) relations")
    # ---- corpus-level plausibility checks (calibrated on the paper's statistics, see 08_calibration.md)
    stats = {}
    for sp in spans:
        if isinstance(sp, list) and len(sp) == 5:
            stats[sp[3]] = stats.get(sp[3], 0) + 1
    ns = sum(stats.values())
    in_units = [u for u in seg["units"] if in_scope(seg, u) and not u["h"] and not u["l"]]
    annotatable = sum(u["e"] - u["s"] for u in in_units)
    covered = sum(e - s for s, e, _, _ in ok if sc["end"] is None or s < sc["end"])
    cov = covered / annotatable if annotatable else 0.0
    stats_out = {"spans": ns, "relations": len(rels), "types": stats, "coverage": round(cov, 2),
                 "avg_len": round(sum(e - s for s, e, _, _ in ok) / len(ok)) if ok else 0,
                 "per_1000": round(1000.0 * ns / annotatable, 2) if annotatable else 0}
    if ns and annotatable:
        if cov > 0.85:
            warns.append("coverage %.0f%% of the Law section is inside spans (reference ~75%%): you are probably annotating "
                         "procedural/quoted text or submissions that restate documents" % (100 * cov))
        elif cov < 0.40 and ns >= 3:
            warns.append("coverage only %.0f%% of the Law section (reference ~75%%): check you did not skip whole paragraphs" % (100 * cov))
        if stats_out["per_1000"] > 2.5:
            warns.append("%.1f spans per 1000 chars (reference ~1.5): probably over-split - merge neighbouring spans of the same "
                         "type+actor and do not split one paragraph by sentence function" % stats_out["per_1000"])
        if stats_out["avg_len"] < 300:
            warns.append("average span length %d chars (reference ~570): probably over-split" % stats_out["avg_len"])
        if stats.get("APP", 0) / ns > 0.75:
            warns.append("APP is >75%% of spans (reference 57%%): check proportionality/precedent/decision spans")
        if stats.get("DEC", 0) == 0:
            warns.append("no DEC span at all - judgments normally contain at least one")
        elif stats["DEC"] >= 5 and stats["DEC"] / ns > 0.12:
            warns.append("DEC is %.0f%% of spans (corpus 8%%): DEC = the Court's own holding on an issue, not a party's "
                         "conclusion and not the operative part" % (100.0 * stats["DEC"] / ns))
    elif seg["units"] and ns == 0:
        warns.append("no spans at all")
    if not quiet:
        for t in RARE_TYPES:
            if stats.get(t):
                warns.append("rare label %s x%d (corpus %s): avoid unless it meets the strict trigger in 02_label_descriptions.md §2 (TEL/SYS/CMP/HIS/SUI: use APP)"
                             % (t, stats[t], {"HIS": "0%", "OVR": "0.01%", "SUI": "0.16%", "TXT": "0.07%", "SYS": "0.03%",
                                              "CMP": "0.09%", "TEL": "0.33%", "MOA": "0.44%", "DIS": "0.58%", "NCP": "1.7%"}[t]))
    if show and not errs:
        bymap = {sp[0]: sp for sp in spans}
        for s, e, sid, t in ok:
            sp = bymap[sid]
            tx = re.sub(r"\s+", " ", text[s:e])
            body = tx if len(tx) <= 130 else tx[:85] + " ... " + tx[-40:]
            print("  %3d [%d-%d) %-3s %-5s | %s" % (sid, s, e, sp[3], sp[4], body))
    return errs, warns, stats_out


def cmd_validate(a):
    errs, warns, st = validate(a.txt, a.ann, show=a.show)
    for w in warns:
        print("WARN ", w)
    for e in errs:
        print("ERROR", e)
    print(("FAIL" if errs else "OK") + ": %d spans, %d relations, coverage %s, avg span %s chars, %s spans/1000 chars, "
          "%d errors, %d warnings" % (st.get("spans", 0), st.get("relations", 0), st.get("coverage", "-"),
                                      st.get("avg_len", "-"), st.get("per_1000", "-"), len(errs), len(warns)))
    sys.exit(1 if errs else 0)


def cmd_batch(a):
    rows, bad = [], 0
    for f in sorted(os.listdir(a.txt_dir)):
        if not f.lower().endswith(".txt"):
            continue
        stem = os.path.splitext(f)[0]
        ann = os.path.join(a.out_dir, stem + ".am.json")
        if not os.path.exists(ann):
            rows.append((f, "MISSING", "-", "-", "-"))
            bad += 1
            continue
        errs, warns, st = validate(os.path.join(a.txt_dir, f), ann, quiet=True)
        rows.append((f, "FAIL" if errs else "ok", st.get("spans", "-"), st.get("coverage", "-"), len(warns)))
        bad += 1 if errs else 0
        for e in errs[:5]:
            print("  %s: %s" % (f, e))
    print("%-40s %-8s %6s %9s %6s" % ("file", "status", "spans", "coverage", "warns"))
    for r in rows:
        print("%-40s %-8s %6s %9s %6s" % r)
    print("%d files, %d not valid" % (len(rows), bad))
    sys.exit(1 if bad else 0)


# ============================================================================ rebase
def cmd_rebase(a):
    """Convert offsets made on the RAW text (CRLF counted, mojibake not repaired) to the canonical text."""
    with open(a.old, encoding="utf-8-sig") as f:
        ann = json.load(f)
    with open(a.txt, "rb") as f:
        raw, _ = decode_bytes(f.read())
    clean, edits = normalize_text(raw, OPTS["keep_crlf"], OPTS["repair"])
    if ann.get("n_chars") == len(clean) and not a.force:
        sys.exit("nothing to do: n_chars (%d) already equals the cleaned text length. (--force to rewrite anyway)" % len(clean))
    if ann.get("n_chars") != len(raw) and not a.force:
        sys.exit("n_chars %s matches neither the raw text (%d) nor the cleaned text (%d): wrong text file? (--force to try)"
                 % (ann.get("n_chars"), len(raw), len(clean)))
    f = make_mapper(edits)
    spans = []
    for sid, s, e, t, ac in ann["spans"]:
        spans.append([sid, f(s), f(e), t, ac])
    with open(a.out, "w", encoding="utf-8", newline="\n") as fo:
        fo.write(dump_final(ann.get("file", os.path.basename(a.txt)), len(clean), spans, ann.get("relations", []),
                            sum(1 for e in edits if e[2] != "\n")))
    print("rebased %d spans: %d -> %d chars (%d CRLF, %d mojibake repairs) -> %s"
          % (len(spans), len(raw), len(clean), sum(1 for e in edits if e[2] == "\n"),
             sum(1 for e in edits if e[2] != "\n"), a.out))


# ============================================================================ main
def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--keep-crlf", action="store_true", help="count CRLF as 2 characters (default: normalise to LF)")
    common.add_argument("--no-repair", action="store_true", help="do not repair mojibake such as a-circumflex+euro+tm")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("segment", parents=[common], help="write <stem>.units.txt for a file or a directory")
    p.add_argument("input")
    p.add_argument("work_dir")
    p.add_argument("--include-tail", action="store_true", help="also show the operative part and separate opinions")
    p.add_argument("--show-all", action="store_true", help="also show units before the Law section")
    p.add_argument("--region-start", type=int, default=None, help="override the start of the Law section (char offset)")
    p.set_defaults(fn=cmd_segment)
    p = sub.add_parser("build", parents=[common], help="jsonl scratch rows (unit ranges) -> final <stem>.am.json")
    p.add_argument("jsonl")
    p.add_argument("txt")
    p.add_argument("out")
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser("validate", parents=[common], help="validate one annotation file")
    p.add_argument("txt")
    p.add_argument("ann")
    p.add_argument("--show", action="store_true", help="print each span's text for review")
    p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("batch-validate", parents=[common], help="validate all .txt in a dir against <out_dir>/<stem>.am.json")
    p.add_argument("txt_dir")
    p.add_argument("out_dir")
    p.set_defaults(fn=cmd_batch)
    p = sub.add_parser("rebase", parents=[common], help="convert an older output (CRLF/mojibake offsets) to canonical offsets")
    p.add_argument("old")
    p.add_argument("txt")
    p.add_argument("out")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_rebase)
    a = ap.parse_args()
    OPTS["keep_crlf"] = a.keep_crlf
    OPTS["repair"] = not a.no_repair
    a.fn(a)


if __name__ == "__main__":
    main()
