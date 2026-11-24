"""Run with: aiapp test   (models are scripted; everything else is real)."""

from aiapp.testing import AppTest


class Extraction(AppTest):
    def test_extracts_the_invoice(self):
        # The blueprint asks for the fields under "data", with a quote per field under "evidence".
        self.models.json({"data": {"vendor": "Northwind Traders Ltd", "invoice_number": "INV-2027-0042", "total": 1730.5,
                                   "currency": "GBP"},
                          "evidence": {"total": {"page": 1, "quote": "TOTAL DUE GBP 1,730.50"}}})
        r = self.client.upload("/extract", "samples/invoice.txt", query={"wait": 30})
        self.assertEqual(r.status, 200, r.text)
        result = r.json()
        self.assertEqual(result["state"], "done", result)
        self.assertEqual(result["result"]["data"]["total"], 1730.5)
        # The document's text reached the model.
        self.assertIn("Northwind", self.models.last.prompt + self.models.last.system)
