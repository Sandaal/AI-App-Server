import time

from aiapp.testing import AppTest


class Report(AppTest):
    def test_job_publishes_and_subscriber_stores(self):
        self.models.reply("182 orders today, 23,940.50 in revenue.")
        self.client.post("/run")
        self.harness.wait_jobs()
        end = time.time() + 20
        while time.time() < end and not self.client.post("/latest").json():
            time.sleep(0.3)
        report = self.client.post("/latest").json()
        self.assertEqual(report["figures"]["orders"], 182)
        self.assertIn("182 orders", report["summary"])

    def test_cron_is_scheduled(self):
        self.assertIn("nightly", self.harness.cli("cron", "scheduled-report"))
