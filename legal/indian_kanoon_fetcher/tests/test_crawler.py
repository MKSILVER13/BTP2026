import tempfile
import unittest
from pathlib import Path

from ik_scraper.crawler import CategoryCrawler
from ik_scraper.storage import Storage


class FakeClient:
    pages = {
        "https://indiankanoon.org/browse/category/": '<a href="/browse/category/2026/">2026</a>',
        "https://indiankanoon.org/browse/category/2026/": '<a href="/doc/1/">One</a><a href="?page=2">Next</a>',
        "https://indiankanoon.org/browse/category/2026/?page=2": '<a href="/doc/2/">Two</a>',
        "https://indiankanoon.org/search/?formInput=doctypes%3Acategory+year%3A2026": '<a href="/doc/1/">One</a>',
        "https://indiankanoon.org/doc/1/": '<h1>One</h1><main>Text one.</main>',
        "https://indiankanoon.org/doc/2/": '<h1>Two</h1><main>Text two.</main>',
    }

    def get(self, url):
        return self.pages[url]


class CrawlerTests(unittest.TestCase):
    def test_category_downloads_paginated_documents_and_resumes(self):
        with tempfile.TemporaryDirectory() as temp:
            storage = Storage(temp)
            crawler = CategoryCrawler(FakeClient(), storage)
            first = crawler.download_category("https://indiankanoon.org/browse/category/", "judgments", ["Example"])
            self.assertEqual(first["successful"], ["1", "2"])
            directory = Path(temp) / "judgments" / "example"
            self.assertEqual((directory / "1.txt").read_text(encoding="utf-8").strip(), "Text one.")
            second = crawler.download_category("https://indiankanoon.org/browse/category/", "judgments", ["Example"])
            self.assertEqual(second["successful"], ["1", "2"])
            document_report = (Path(temp) / "document-report.csv").read_text(encoding="utf-8-sig")
            category_report = (Path(temp) / "category-report.csv").read_text(encoding="utf-8-sig")
            self.assertIn("One", document_report)
            self.assertIn("downloaded_count", category_report)
            self.assertTrue((directory / "1.classified.txt").exists())


if __name__ == "__main__":
    unittest.main()
