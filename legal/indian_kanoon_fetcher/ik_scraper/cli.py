from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from .client import WebClient
from .crawler import CategoryCrawler
from .inventory import WebsiteInventory
from .models import CatalogueItem
from .parser import BASE_URL, parse_catalogue
from .storage import Storage


@dataclass
class MenuState:
    label: str
    url: str
    kind: str
    path: list[str]


class InteractiveApp:
    def __init__(self, client: WebClient, storage: Storage, max_documents: int | None = None):
        self.client = client
        self.storage = storage
        self.crawler = CategoryCrawler(client, storage)
        self.max_documents = max_documents
        self.history: list[MenuState] = []

    def run(self) -> int:
        state = MenuState("Home", BASE_URL, "home", [])
        while True:
            items = self._items(state)
            self._print_menu(state, items)
            try:
                command = input("Select an option: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if command in {"q", "quit", "exit"}:
                return 0
            if command in {"b", "back"}:
                if self.history:
                    state = self.history.pop()
                continue
            if command in {"h", "home"}:
                self.history.clear()
                state = MenuState("Home", BASE_URL, "home", [])
                continue
            if command == "help":
                print("Use a number to open it, #number to download it, b/back, h/home, or q/quit.")
                continue
            download = command.startswith("#")
            raw_number = command[1:] if download else command
            if not raw_number.isdigit() or not (1 <= int(raw_number) <= len(items)):
                print("Invalid option.")
                continue
            item = items[int(raw_number) - 1]
            if download:
                self._download(item, state)
            else:
                self.history.append(state)
                state = MenuState(item.name, item.url, self._kind_for(state, item), state.path + [item.name])

    def _items(self, state: MenuState) -> list[CatalogueItem]:
        if state.kind == "home":
            return [CatalogueItem(1, "Browse Laws", "https://indiankanoon.org/browselaws/"), CatalogueItem(2, "Browse Judgments", "https://indiankanoon.org/browse/")]
        try:
            return parse_catalogue(self.client.get(state.url), state.url)
        except Exception as exc:
            print(f"Could not load this page: {exc}")
            return []

    @staticmethod
    def _kind_for(state: MenuState, item: CatalogueItem) -> str:
        return "laws" if state.kind == "laws" or "browselaws" in item.url else "judgments"

    def _print_menu(self, state: MenuState, items: list[CatalogueItem]) -> None:
        print(f"\n{state.label}\n")
        for item in items:
            count = f" ({item.count:,} documents)" if item.count is not None else " (count unavailable)"
            print(f"{item.number}. {item.name}{count}")
        print("\nCommands: number=open, #number=download, b=back, h=home, q=quit")

    def _download(self, item: CatalogueItem, state: MenuState) -> None:
        count = f"{item.count:,}" if item.count is not None else "an unknown number of"
        answer = input(f"Download all {count} documents under '{item.name}'? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Download cancelled.")
            return
        print("Discovering documents and downloading; this may take a while...")
        manifest = self.crawler.download_category(item.url, self._kind_for(state, item), state.path + [item.name], self.max_documents, item.count)
        discovery_failures = len(manifest.get("discovery_failures", []))
        print(f"Downloaded {len(manifest['successful'])}; failed {len(manifest['failed'])}; inaccessible catalogue pages {discovery_failures}.")
        if not manifest["successful"] and not manifest["failed"] and not discovery_failures:
            print("No document links were found under this selection. It may be an empty or unsupported catalogue page.")
        print(f"Reports written to: {self.storage.root / 'document-report.csv'} and {self.storage.root / 'category-report.csv'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Interactive Indian Kanoon catalogue scraper")
    parser.add_argument("--output", default="data", help="Output directory (default: data)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-documents", type=int, default=None)
    parser.add_argument("--inventory", action="store_true", help="Crawl both catalogues and create a one-time website CSV inventory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    client = WebClient(args.delay, args.timeout, args.retries)
    if args.inventory:
        inventory = WebsiteInventory(client)
        print("Building website inventory; full document text will not be downloaded...")
        inventory.run()
        files = inventory.write_csv(args.output)
        print(f"Indexed {len(inventory.rows)} documents across {len(inventory.categories)} catalogue pages.")
        print("Reports written to:")
        for file in files:
            print(f"  {file}")
        return 0 if not inventory.errors else 2
    app = InteractiveApp(client, Storage(args.output), args.max_documents)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
