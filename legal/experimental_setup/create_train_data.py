#!/usr/bin/env python3
"""Export the Mining Legal Arguments ECHR gold data in lam-am JSON format.

By default, this reads ``mining-legal-arguments`` next to this script and
rebuilds ``processed_echr`` next to this script. Each document gets its XMI
text as a UTF-8 .txt file and a matching .json containing span offsets, the
canonical argument type, the actor, and an empty relations list. The source
XMI does not annotate argument relations.

Run from any working directory with::

    python legal/experimental_setup/create_train_data.py

Optional directories can be supplied with ``--data-dir`` and ``--output-dir``.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = SCRIPT_DIR / "mining-legal-arguments"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "processed_echr"


# The original XMI uses German names. Mapping is to the canonical codes used
# by legal-argument-mining/05_output_schema.md.
TYPE_CODES = {
    "Konsens der prozessualen Parteien": "NCP",
    "Wortlaut Auslegung": "TXT",
    "Historische Auslegung": "HIS",
    "Systematische Auslegung": "SYS",
    "Sinn & Zweck Auslegung": "TEL",
    "Rechtsvergleichung": "CMP",
    "Verhältnismäßigkeitsprüfung – Rechtsgrundlage": "LEG",
    "Verhältnismäßigkeitsprüfung – Legitimer Zweck": "PUR",
    "Verhältnismäßigkeitsprüfung – Geeignetheit": "SUI",
    "Verhältnismäßigkeitsprüfung – Angemessenheit": "NEC",
    "Overruling": "OVR",
    "Distinguishing": "DIS",
    "Einschätzungsspielraum": "MOA",
    "Vorherige Rechtsprechung des EGMR": "PRE",
    "Entscheidung des EGMR": "DEC",
    "Subsumtion": "APP",
}

ACTOR_CODES = {
    "Beschwerdeführer": "APPL",
    "EGMR": "ECHR",
    "Staat": "STATE",
    "Kommission/Kammer": "COMM",
    "Dritte": "THIRD",
}


def repair_mojibake(value: str) -> str:
    """Repair common UTF-8-as-Windows-1252 artifacts in XMI label values."""
    current = value
    for _ in range(2):
        try:
            repaired = current.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if repaired == current:
            break
        current = repaired
    return current


def normalize_label(value: str) -> str:
    value = repair_mojibake(value)
    value = value.replace("–", "-").replace("—", "-")
    return " ".join(value.split()).casefold()


def normalized_map(values: dict[str, str]) -> dict[str, str]:
    return {normalize_label(label): code for label, code in values.items()}


TYPE_LOOKUP = normalized_map(TYPE_CODES)
ACTOR_LOOKUP = normalized_map(ACTOR_CODES)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def assigned_ids(data_dir: Path) -> dict[str, list[str]]:
    """Read official split membership from the repository's token CSVs."""
    splits: dict[str, list[str]] = {}
    for source_split in ("train", "val", "test"):
        agent_dir = data_dir / "data" / source_split / "agent"
        type_dir = data_dir / "data" / source_split / "argType"
        if not agent_dir.is_dir() or not type_dir.is_dir():
            raise FileNotFoundError(
                f"Expected both agent and argType split folders under data/{source_split}"
            )
        agent_ids = {path.stem for path in agent_dir.glob("*.csv")}
        type_ids = {path.stem for path in type_dir.glob("*.csv")}
        if agent_ids != type_ids:
            only_agent = sorted(agent_ids - type_ids)
            only_type = sorted(type_ids - agent_ids)
            raise ValueError(
                f"Split mismatch for {source_split}: only agent={only_agent[:5]}, "
                f"only argType={only_type[:5]}"
            )
        output_split = "dev" if source_split == "val" else source_split
        splits[output_split] = sorted(agent_ids)
    return splits


def load_xmi(path: Path) -> tuple[str, list[list[Any]]]:
    """Return document text and sorted [id,start,end,type,actor] spans."""
    root = ET.parse(path).getroot()
    text: str | None = None
    raw_annotations: list[tuple[int, int, str, str]] = []

    for element in root.iter():
        name = local_name(element.tag)
        if name == "Sofa" and element.attrib.get("sofaString") is not None:
            text = element.attrib["sofaString"]
        elif name == "LegalArgumentation":
            try:
                start = int(element.attrib["begin"])
                end = int(element.attrib["end"])
                raw_type = element.attrib["ArgType"]
                raw_actor = element.attrib["Akteur"]
            except (KeyError, ValueError) as exc:
                raise ValueError(f"Malformed LegalArgumentation in {path}: {element.attrib}") from exc

            type_code = TYPE_LOOKUP.get(normalize_label(raw_type))
            actor_code = ACTOR_LOOKUP.get(normalize_label(raw_actor))
            if type_code is None:
                raise ValueError(f"Unknown XMI argument type {raw_type!r} in {path}")
            if actor_code is None:
                raise ValueError(f"Unknown XMI actor {raw_actor!r} in {path}")
            raw_annotations.append((start, end, type_code, actor_code))

    if text is None:
        raise ValueError(f"No Sofa sofaString document text found in {path}")
    if "\r" in text:
        raise ValueError(
            f"XMI text contains CR line endings in {path}; refusing to change its offsets silently"
        )

    raw_annotations.sort(key=lambda row: (row[0], row[1]))
    spans: list[list[Any]] = []
    previous_end = -1
    for span_id, (start, end, type_code, actor_code) in enumerate(raw_annotations, start=1):
        if not (0 <= start < end <= len(text)):
            raise ValueError(
                f"Invalid XMI offsets [{start},{end}) for {len(text)}-character text in {path}"
            )
        if start < previous_end:
            raise ValueError(f"Overlapping XMI argument spans in {path} at [{start},{end})")
        previous_end = end
        spans.append([span_id, start, end, type_code, actor_code])

    return text, spans


def write_pair(
    *, document_id: str, split: str, xmi_path: Path, output_dir: Path
) -> dict[str, str | int]:
    text, spans = load_xmi(xmi_path)
    text_path = output_dir / split / "texts" / f"{document_id}.txt"
    annotation_path = output_dir / split / "annotations" / f"{document_id}.json"
    text_path.parent.mkdir(parents=True, exist_ok=True)
    annotation_path.parent.mkdir(parents=True, exist_ok=True)

    # newline="" preserves XMI's LF text exactly, keeping XMI offsets valid.
    with text_path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(text)

    annotation = {
        "schema": "lam-am/1.1",
        "file": text_path.name,
        "n_chars": len(text),
        "offsets": "lf",
        "spans": spans,
        "relations": [],
    }
    annotation_path.write_text(
        json.dumps(annotation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="",
    )
    return {
        "id": document_id,
        "split": split,
        "input_file": str(text_path.resolve()),
        "annotation_file": str(annotation_path.resolve()),
        "spans": len(spans),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    output_dir = args.output_dir.resolve()
    gold_dir = data_dir / "gold_data"
    if not gold_dir.is_dir():
        parser.error(f"Gold XMI directory not found: {gold_dir}")

    split_ids = assigned_ids(data_dir)
    manifest: list[dict[str, str | int]] = []
    type_counts: dict[str, int] = {}
    actor_counts: dict[str, int] = {}

    for split, document_ids in split_ids.items():
        for document_id in document_ids:
            xmi_path = gold_dir / f"{document_id}.xmi"
            if not xmi_path.is_file():
                raise FileNotFoundError(f"Split document has no gold XMI: {xmi_path}")
            entry = write_pair(
                document_id=document_id,
                split=split,
                xmi_path=xmi_path,
                output_dir=output_dir,
            )
            manifest.append({key: value for key, value in entry.items() if key != "spans"})

            annotation_path = Path(str(entry["annotation_file"]))
            with annotation_path.open(encoding="utf-8") as stream:
                annotation = json.load(stream)
            for span in annotation["spans"]:
                type_counts[span[3]] = type_counts.get(span[3], 0) + 1
                actor_counts[span[4]] = actor_counts.get(span[4], 0) + 1

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest.sort(key=lambda row: (str(row["split"]), str(row["id"])))
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="",
    )

    print(f"Wrote {len(manifest)} documents to {output_dir}")
    for split in ("train", "dev", "test"):
        count = sum(row["split"] == split for row in manifest)
        print(f"  {split}: {count} documents")
    print(f"Argument types: {dict(sorted(type_counts.items()))}")
    print(f"Actors: {dict(sorted(actor_counts.items()))}")
    print("Relations: [] (the source XMI has no argument-relation annotations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
