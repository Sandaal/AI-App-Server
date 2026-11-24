from aiapp.testing import AppTest


class Copy(AppTest):
    def test_the_route_runs_the_changed_copy(self):
        self.harness.wait_jobs()
        self.models.reply("You have 30 days to return an item [1]. Contoso Help", when="return")
        r = self.client.chat("How long do I have to return an item?")
        self.assertIn("30 days", r.text)
        self.assertEqual(r.citations[0]["source"], "returns.md")              # still cites like the blueprint
        self.assertIn("at most three sentences", self.models.last.system)     # but with this app's change
