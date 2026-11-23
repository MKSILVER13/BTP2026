import unittest

from ik_scraper.parser import catalogue_search_url, document_links, pagination_links, parse_catalogue, parse_classification, parse_document, search_result_documents


class ParserTests(unittest.TestCase):
    def test_catalogue_items_and_counts(self):
        html = '''<main><a href="/browse/sc">Supreme Court (1,234 documents)</a>
        <a href="/browse/hc">High Courts</a><a href="/">Home</a></main>'''
        items = parse_catalogue(html)
        self.assertEqual([x.name for x in items], ["Supreme Court", "High Courts"])
        self.assertEqual(items[0].count, 1234)

    def test_numeric_year_is_not_removed_from_name(self):
        items = parse_catalogue('<a href="/browse/court/2026/">2026</a>')
        self.assertEqual(items[0].name, "2026")

    def test_year_catalogue_resolves_to_search_page(self):
        self.assertEqual(
            catalogue_search_url("https://indiankanoon.org/browse/bengalpresidency-act/1943/"),
            "https://indiankanoon.org/search/?formInput=doctypes%3Abengalpresidency-act+year%3A1943",
        )

    def test_search_result_documents_extract_titles_and_ids(self):
        rows = search_result_documents('<a href="/doc/130298262/">The Bengal Vagrancy Act, 1943</a><a href="/doc/130298262/">Full Document</a>', "https://indiankanoon.org/search/")
        self.assertEqual(rows[0]["document_id"], "130298262")
        self.assertEqual(rows[0]["title"], "The Bengal Vagrancy Act, 1943")

    def test_indian_kanoon_classification_attributes(self):
        html = '''<div class="judgments">
          <p data-structure="Facts">The background facts.</p>
          <p data-structure="Issue">Whether the order is valid?</p>
          <p data-structure="PetArg">The appellant's argument.</p>
          <p data-structure="RespArg">The respondent's argument.</p>
          <p data-structure="Precedent">An earlier case.</p>
          <p data-structure="Section">The legal analysis.</p>
          <p data-structure="CDiscource">The court's reasoning.</p>
          <p data-structure="Conclusion">The petition is dismissed.</p>
        </div>'''
        self.assertEqual([label for label, _ in parse_classification(html)], [
            "fact", "issue", "appellant_argument", "respondent_argument",
            "precedent_analysis", "law_analysis", "court_reasoning", "conclusion",
        ])

    def test_document_and_pagination_links(self):
        html = '''<a href="/doc/123/">Case</a><a href="/doc/123/">Duplicate</a>
        <a href="/doc/456/">Case 2</a><a href="?page=2">Next</a>'''
        self.assertEqual(document_links(html, "https://indiankanoon.org/browse/"), ["https://indiankanoon.org/doc/123/", "https://indiankanoon.org/doc/456/"])
        self.assertEqual(pagination_links(html, "https://indiankanoon.org/browse/"), ["https://indiankanoon.org/browse/?page=2"])

    def test_document_text_removes_navigation(self):
        html = '<nav>Menu</nav><h1>Example Case</h1><main><p>First paragraph.</p><p>Second paragraph.</p></main>'
        document = parse_document(html, "https://indiankanoon.org/doc/789/")
        self.assertEqual(document.document_id, "789")
        self.assertIn("First paragraph.", document.text)
        self.assertNotIn("Menu", document.text)


if __name__ == "__main__":
    unittest.main()
