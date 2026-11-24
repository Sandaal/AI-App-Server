import time

from aiapp.testing import AppTest


class Refunds(AppTest):
    def wait_state(self, job, *states, timeout=30):
        end = time.time() + timeout
        while time.time() < end:
            s = self.client.post("/status", {"job": job}).json()
            if s["state"] in states:
                return s
            time.sleep(0.3)
        self.fail(f"job {job} never reached {states}")

    def test_small_refund_is_paid_at_once(self):
        job = self.client.post("/refund", {"order_id": "A-1002"}).json()["job"]
        s = self.wait_state(job, "done")
        self.assertEqual(s["result"], {"refunded": True, "reference": "refund-alan"})

    def test_large_refund_waits_for_a_person(self):
        job = self.client.post("/refund", {"order_id": "A-1001"}).json()["job"]
        self.wait_state(job, "waiting")
        listed = self.harness.cli("approvals", "approval-workflow")
        approval_id = listed.split()[0]
        self.harness.cli("approve", "approval-workflow", approval_id)
        s = self.wait_state(job, "done")
        self.assertEqual(s["result"]["reference"], "refund-ada")
