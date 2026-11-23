from __future__ import annotations

import argparse
import json
from pathlib import Path

from .client import WebClient
from .crawler import IBBICrawler
from .storage import Storage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download public IBBI order PDFs")
    parser.add_argument("--section", help="Configured section slug, for example nclat")
    parser.add_argument("--all-sections", action="store_true")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--all-pages", action="store_true")
    parser.add_argument("--download", action="store_true", help="Download PDFs; otherwise perform a dry run")
    parser.add_argument("--output", default="ibbi_data")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / "sections.json"))
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-documents", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sections = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if args.section:
        sections = [section for section in sections if section["slug"] == args.section]
        if not sections:
            raise SystemExit(f"Unknown section: {args.section}")
    elif not args.all_sections:
        raise SystemExit("Choose --section SLUG or --all-sections")
    crawler = IBBICrawler(WebClient(args.delay, args.timeout, args.retries), Storage(args.output), args.download, args.max_documents)
    for section in sections:
        print(f"Scanning {section['name']}...")
        crawler.run_section(section, args.all_pages, args.page)
    crawler.storage.save_reports(crawler.rows, crawler.errors)
    print(f"Discovered {len(crawler.rows)} rows; errors: {len(crawler.errors)}")
    print(f"Reports: {Path(args.output) / 'reports'}")
    return 0 if not crawler.errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
