#!/usr/bin/env python3
"""Evaluate all train texts against paired gold and result lam-am JSON files.

Expected layout (all options can be overridden):
    predictions/train/<stem>.txt
    predictions/gold/<stem>.json
    predictions/result/<stem>.am.json

For each document, writes six CSV reports into evaluation_results/<stem>/.
It also writes six micro-aggregated CSV reports into evaluation_results/_aggregate/.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent
DEFAULT_TRAIN_DIR = ROOT / "predictions" / "train"
DEFAULT_GOLD_DIR = ROOT / "predictions" / "gold"
DEFAULT_RESULT_DIR = ROOT / "predictions" / "result"
DEFAULT_OUTPUT_DIR = ROOT / "evaluation_results"
DEFAULT_THRESHOLDS = tuple(round(i / 10, 2) for i in range(1, 11))

TYPE_CODES = (
    "NCP", "TXT", "HIS", "SYS", "TEL", "CMP", "LEG", "PUR",
    "SUI", "NEC", "OVR", "DIS", "MOA", "PRE", "DEC", "APP",
)
ACTOR_CODES = ("ECHR", "APPL", "STATE", "THIRD", "COMM")

AM_TOOLS_PATH = ROOT / "legal-argument-mining" / "scripts" / "am_tools.py"
_spec = importlib.util.spec_from_file_location("lam_am_tools_batch_eval", AM_TOOLS_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Could not load text normalizer: {AM_TOOLS_PATH}")
am_tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(am_tools)


def read_annotations(path: Path, role: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or not isinstance(data.get("spans"), list):
        raise ValueError(f"{role} file must be a lam-am JSON object containing a spans list: {path}")
    spans = []
    for index, row in enumerate(data["spans"], start=1):
        if not isinstance(row, list) or len(row) != 5:
            raise ValueError(f"{role} span {index} must be [id,start,end,type,actor]")
        span_id, start, end, label, actor = row
        if not all(isinstance(x, int) and not isinstance(x, bool) for x in (span_id, start, end)):
            raise ValueError(f"{role} span {index} has a non-integer id/start/end")
        if label not in TYPE_CODES:
            raise ValueError(f"{role} span {index} has unknown type {label!r}")
        if actor not in ACTOR_CODES:
            raise ValueError(f"{role} span {index} has unknown actor {actor!r}")
        if start < 0 or end <= start:
            raise ValueError(f"{role} span {index} has invalid offsets [{start},{end})")
        spans.append({"id": span_id, "start": start, "end": end, "type": label, "actor": actor})
    return data, spans


def normalize_offsets(
    text_path: Path,
    text: str,
    text_info: dict[str, Any],
    annotations: dict[str, Any],
    spans: list[dict[str, Any]],
    role: str,
) -> list[str]:
    notes = []
    count = annotations.get("n_chars")
    has_bom = text_path.read_bytes().startswith(b"\xef\xbb\xbf")

    if count == text_info["raw_len"] and text_info["raw_len"] != len(text):
        mapper = am_tools.make_mapper(text_info["edits"])
        for span in spans:
            span["start"] = mapper(span["start"])
            span["end"] = mapper(span["end"])
        notes.append(f"converted {role} offsets from raw text")
    elif has_bom and count == len(text) + 1:
        for span in spans:
            span["start"] -= 1
            span["end"] -= 1
        notes.append(f"removed UTF-8 BOM offset from {role}")
    elif count is not None and count != len(text):
        notes.append(f"WARNING: {role} n_chars={count}, normalized text length={len(text)}")

    return notes


def span_iou(a: dict[str, Any], b: dict[str, Any]) -> float:
    intersection = max(0, min(a["end"], b["end"]) - max(a["start"], b["start"]))
    if intersection == 0:
        return 0.0
    union = (a["end"] - a["start"]) + (b["end"] - b["start"]) - intersection
    return intersection / union if union else 0.0


def match_spans(
    gold: list[dict[str, Any]],
    pred: list[dict[str, Any]],
    threshold: float,
    same_label: Callable[[dict[str, Any], dict[str, Any]], bool] | None = None,
) -> int:
    candidates = []
    for gi, g in enumerate(gold):
        for pi, p in enumerate(pred):
            overlap = span_iou(g, p)
            if overlap >= threshold and overlap > 0 and (same_label is None or same_label(g, p)):
                candidates.append((overlap, gi, pi))
    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
    used_g: set[int] = set()
    used_p: set[int] = set()
    for _, gi, pi in candidates:
        if gi not in used_g and pi not in used_p:
            used_g.add(gi)
            used_p.add(pi)
    return len(used_g)


def make_metrics(
    gold: list[dict[str, Any]],
    pred: list[dict[str, Any]],
    threshold: float,
    same_label: Callable[[dict[str, Any], dict[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    tp = match_spans(gold, pred, threshold, same_label)
    fp, fn = len(pred) - tp, len(gold) - tp
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def filter_spans(spans: list[dict[str, Any]], key: str, code: str) -> list[dict[str, Any]]:
    return [span for span in spans if span[key] == code]


def evaluate_document(
    gold: list[dict[str, Any]], pred: list[dict[str, Any]], thresholds: tuple[float, ...], document: str,
) -> dict[str, list[dict[str, Any]]]:
    tables: dict[str, list[dict[str, Any]]] = {
        "span": [], "span_type": [], "span_actor": [], "span_type_actor": [],
        "per_type": [], "per_actor": [],
    }
    for threshold in thresholds:
        common = {"document": document, "iou_threshold": threshold}
        table_specs = (
            ("span", None),
            ("span_type", lambda g, p: g["type"] == p["type"]),
            ("span_actor", lambda g, p: g["actor"] == p["actor"]),
            ("span_type_actor", lambda g, p: g["type"] == p["type"] and g["actor"] == p["actor"]),
        )
        for name, predicate in table_specs:
            tables[name].append({**common, **make_metrics(gold, pred, threshold, predicate)})

        for code in TYPE_CODES:
            g = filter_spans(gold, "type", code)
            p = filter_spans(pred, "type", code)
            tables["per_type"].append({**common, "type": code,
                                        **make_metrics(g, p, threshold, lambda a, b: a["type"] == b["type"])})
        for code in ACTOR_CODES:
            g = filter_spans(gold, "actor", code)
            p = filter_spans(pred, "actor", code)
            tables["per_actor"].append({**common, "actor": code,
                                         **make_metrics(g, p, threshold, lambda a, b: a["actor"] == b["actor"])})
    return tables


def aggregate_tables(tables_by_doc: list[dict[str, list[dict[str, Any]]]], thresholds: tuple[float, ...]
                     ) -> dict[str, list[dict[str, Any]]]:
    aggregate: dict[str, list[dict[str, Any]]] = {name: [] for name in tables_by_doc[0]}
    for name in aggregate:
        is_type = name == "per_type"
        is_actor = name == "per_actor"
        codes = TYPE_CODES if is_type else ACTOR_CODES if is_actor else (None,)
        for threshold in thresholds:
            for code in codes:
                selected = [
                    row for doc_tables in tables_by_doc for row in doc_tables[name]
                    if row["iou_threshold"] == threshold
                    and (code is None or row["type" if is_type else "actor"] == code)
                ]
                tp = sum(row["tp"] for row in selected)
                fp = sum(row["fp"] for row in selected)
                fn = sum(row["fn"] for row in selected)
                precision = tp / (tp + fp) if tp + fp else 0.0
                recall = tp / (tp + fn) if tp + fn else 0.0
                f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
                row = {"document": "_ALL_", "iou_threshold": threshold}
                if is_type:
                    row["type"] = code
                if is_actor:
                    row["actor"] = code
                row.update({"tp": tp, "fp": fp, "fn": fn,
                            "precision": precision, "recall": recall, "f1": f1})
                aggregate[name].append(row)
    return aggregate


def write_tables(output_dir: Path, tables: dict[str, list[dict[str, Any]]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in tables.items():
        detail = ["type"] if name == "per_type" else ["actor"] if name == "per_actor" else []
        fields = ["document", "iou_threshold", *detail, "tp", "fp", "fn", "precision", "recall", "f1"]
        with (output_dir / f"{name}.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-dir", type=Path, default=DEFAULT_TRAIN_DIR)
    parser.add_argument("--gold-dir", type=Path, default=DEFAULT_GOLD_DIR)
    parser.add_argument("--result-dir", type=Path, default=DEFAULT_RESULT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--iou-thresholds", type=float, nargs="+", default=list(DEFAULT_THRESHOLDS))
    args = parser.parse_args()
    thresholds = tuple(sorted(set(args.iou_thresholds)))
    if not thresholds or any(x <= 0 or x > 1 for x in thresholds):
        parser.error("IoU thresholds must be greater than 0 and at most 1")

    train_dir, gold_dir, result_dir = args.train_dir.resolve(), args.gold_dir.resolve(), args.result_dir.resolve()
    output_dir = args.output_dir.resolve()
    for directory in (train_dir, gold_dir, result_dir):
        if not directory.is_dir():
            parser.error(f"input directory does not exist: {directory}")

    texts = sorted(train_dir.glob("*.txt"))
    if not texts:
        parser.error(f"no .txt files found in {train_dir}")

    all_doc_tables = []
    failures = []
    for index, text_path in enumerate(texts, start=1):
        stem = text_path.stem
        gold_path = gold_dir / f"{stem}.json"
        pred_path = result_dir / f"{stem}.am.json"
        missing = [str(path) for path in (gold_path, pred_path) if not path.is_file()]
        if missing:
            failures.append(f"{stem}: missing " + ", ".join(missing))
            continue
        try:
            text, info = am_tools.load_text(str(text_path))
            gold_data, gold = read_annotations(gold_path, "Gold")
            pred_data, pred = read_annotations(pred_path, "Prediction")
            notes = normalize_offsets(text_path, text, info, gold_data, gold, "gold")
            notes.extend(normalize_offsets(text_path, text, info, pred_data, pred, "prediction"))
            for role, spans in (("gold", gold), ("prediction", pred)):
                for span in spans:
                    if span["end"] > len(text):
                        raise ValueError(f"{role} span {span['id']} ends beyond normalized text length {len(text)}")
            if notes:
                print(f"[{index}/{len(texts)}] {stem}: " + "; ".join(notes))
            tables = evaluate_document(gold, pred, thresholds, stem)
            all_doc_tables.append(tables)
            write_tables(output_dir / stem, tables)
            print(f"[{index}/{len(texts)}] {stem}: gold={len(gold)}, result={len(pred)}")
        except Exception as exc:
            failures.append(f"{stem}: {type(exc).__name__}: {exc}")

    if all_doc_tables:
        write_tables(output_dir / "_aggregate", aggregate_tables(all_doc_tables, thresholds))

    print(f"\nProcessed {len(all_doc_tables)} of {len(texts)} train documents; {len(failures)} failed.")
    print(f"Reports saved under: {output_dir}")
    for failure in failures:
        print(f"FAILED: {failure}")
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
