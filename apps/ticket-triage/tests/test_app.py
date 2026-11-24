"""Run with: aiapp test   (models are scripted; everything else is real)."""

from aiapp.testing import AppTest


class Classification(AppTest):
    def test_labels_a_ticket(self):
        self.models.json({"label": "billing", "confidence": 0.93, "reason": "asks for a refund"})
        r = self.client.post("/classify", {"text": "I was charged twice, please refund me."})
        self.assertEqual(r.status, 200, r.text)
        self.assertEqual(r.json()["label"], "billing")
        self.assertIn("charged twice", self.models.last.prompt)
