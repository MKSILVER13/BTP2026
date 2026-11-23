import unittest

from ibbi_gov_fetcher.parser import parse_orders, pagination_links, safe_name


class ParserTests(unittest.TestCase):
    html = '''<table><thead><tr><th>Sr.No.</th><th>Orders Date</th><th>Subject</th><th>Orders Remarks</th></tr></thead><tbody>
    <tr><td>1</td><td>05 Aug, 2026</td><td><a href="/uploads/order/example.pdf">Matter One (284 KB)</a></td><td>Stay Order</td></tr>
    <tr><td>2</td><td>29 Jul, 2026</td><td>Missing PDF</td><td>Others</td></tr></tbody></table><a href="?page=2">2</a>'''

    def test_table_and_pdf_link(self):
        rows = parse_orders(self.html, "NCLAT", "https://ibbi.gov.in/orders/nclat", "https://ibbi.gov.in/orders/nclat")
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0].pdf_url.endswith("example.pdf"))
        self.assertEqual(rows[0].order_remarks, "Stay Order")
        self.assertEqual(rows[1].pdf_url, "")

    def test_pagination_and_filename(self):
        self.assertEqual(pagination_links(self.html, "https://ibbi.gov.in/orders/nclat"), ["https://ibbi.gov.in/orders/nclat?page=2"])
        self.assertEqual(safe_name("A/B: test!"), "a-b-test")


if __name__ == "__main__":
    unittest.main()
